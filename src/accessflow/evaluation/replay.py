import asyncio
import json
import hashlib
import os
import platform
import subprocess
import time
from pathlib import Path

from accessflow.contracts import EndEvent, ResultEvent, ToolResult
from accessflow.engine import Agent
from accessflow.fakes import EventReasoner, FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization
from accessflow.evaluation.trace_metrics import evaluate_trace
from accessflow.evaluation.scenarios import StepReasoner, load_scenario
from accessflow.evaluation.oracle import evaluate_task
from accessflow.evaluation.mock_environment import MockEnvironment

SHUTDOWN_TIMEOUT_S = 2


def commit_revision():
    supplied = os.getenv("ACCESSFLOW_COMMIT")
    if supplied:
        return supplied
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, timeout=2)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def source_evidence(path):
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for source in sorted(root.rglob("*.py")):
        digest.update(source.relative_to(root).as_posix().encode() + b"\0" + source.read_bytes() + b"\0")
    try:
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=2)
        dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        dirty = None
    return {"source_sha256": digest.hexdigest(), "scenario_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "worktree_dirty": dirty}


async def replay(path, output, reasoner=None, backend="offline-fake", *, perception=None, turn_policy=None,
                 component_config=None):
    definition = load_scenario(path)
    scenario = definition.model_dump(mode="json")
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    inputs = definition.events
    executor = MockEnvironment(inputs[0].payload.tools, definition.environment) if definition.environment is not None else FakeTools()

    class RecordedTools:
        async def execute(self, call):
            result = await executor.execute(call)
            record("input", ResultEvent(session_id=scenario["events"][0]["session_id"], payload=result),
                   transport="executor_return")
            return result

        async def cancel(self, call_id):
            status = await executor.cancel(call_id)
            if status == "cancelled_before_commit":
                # Record the same normalized evidence that Agent receives through
                # its worker inbox; this is observation, not a second delivery.
                record("input", ResultEvent(session_id=inputs[0].session_id,
                       payload=ToolResult(call_id=call_id, status="cancelled")),
                       transport="executor_cancel")
            return status

        @property
        def effects(self):
            return executor.effects

    tools = RecordedTools()
    perception_inputs = [entry for entry in inputs if entry.kind in {"transcript", "audio", "frame"}]
    if reasoner is None:
        if definition.reasoning_steps:
            reasoner = StepReasoner(definition.reasoning_steps)
        elif definition.proposals is not None:
            reasoner = EventReasoner({event.event_id: plan for event, plan in zip(
                perception_inputs, definition.proposals, strict=True)})
        else:
            raise ValueError("Offline fake mode requires explicit proposals or reasoning_steps")
    perception_profile = "text-pass-through" if perception is None else (
        f"{type(perception).__module__}.{type(perception).__name__}")
    policy_profile = "final-flag-baseline" if turn_policy is None else (
        f"{type(turn_policy).__module__}.{type(turn_policy).__name__}")
    selected_perception = perception if perception is not None else FakePerception()
    observed_backends = set()

    class RecordedPerception:
        async def observe(self, event):
            async for observation in selected_perception.observe(event):
                observed_backends.add(observation.backend)
                yield observation

    agent = Agent(RecordedPerception(), turn_policy if turn_policy is not None else FinalFlagPolicy(), reasoner,
                  tools, MockOnlyAuthorization())
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    events = []
    started = time.perf_counter()
    terminal = asyncio.Event()
    completion_status = "completed"
    failure_type = None
    perception_cleanup = "not_required"
    criterion = definition.terminal_output
    terminal_cause = criterion.caused_by_event_id or inputs[-1].event_id

    def record(kind, event, transport="queue"):
        events.append({"type": kind, "event": event.model_dump(mode="json"),
                       "observed_at": time.perf_counter() - started, "transport": transport})

    async def collect():
        while True:
            event = await outgoing.get()
            try:
                record("output", event)
                if (event.kind == criterion.kind and event.payload.get("caused_by_event_id") == terminal_cause
                        and (criterion.code is None or event.payload.get("code") == criterion.code)):
                    terminal.set()
                if event.payload.get("code") == "backend_failure":
                    terminal.set()
                if event.state.status == "ended":
                    return
            finally:
                outgoing.task_done()

    async def feed_and_wait():
        for index, entry in enumerate(inputs):
            record("input", entry)
            await incoming.put(entry)
            # Explicit test pacing, not an inferred speech/end-of-turn measurement.
            if index < len(inputs) - 1:
                await asyncio.sleep(definition.event_spacing_s)
        await asyncio.wait_for(terminal.wait(), definition.completion_timeout_s)

    collector = asyncio.create_task(collect())
    feeder = asyncio.create_task(feed_and_wait())
    try:
        done, _ = await asyncio.wait({runner, collector, feeder}, return_when=asyncio.FIRST_COMPLETED)
        # An agent/collector exit must not strand the replay until the scenario deadline.
        for task in (runner, collector):
            if task in done:
                task.result()
        if feeder in done:
            feeder.result()
        elif not terminal.is_set():
            completion_status = "agent_stopped"
    except TimeoutError:
        completion_status = "timeout"
    except Exception as exc:
        completion_status = "agent_error"
        failure_type = type(exc).__name__
    finally:
        feeder.cancel()
        await asyncio.gather(feeder, return_exceptions=True)
        ending = EndEvent(session_id=scenario["events"][0]["session_id"])
        record("input", ending)
        await incoming.put(ending)
        try:
            await asyncio.wait_for(asyncio.shield(runner), SHUTDOWN_TIMEOUT_S)
        except TimeoutError:
            completion_status = "shutdown_timeout"
            runner.cancel()
        except Exception as exc:
            completion_status = "agent_error"
            failure_type = type(exc).__name__
        finally:
            await asyncio.gather(runner, return_exceptions=True)
        close_perception = getattr(selected_perception, "aclose", None)
        if close_perception is not None:
            try:
                await asyncio.wait_for(close_perception(), SHUTDOWN_TIMEOUT_S)
                perception_cleanup = "closed"
            except Exception as exc:
                perception_cleanup = "failed"
                completion_status = "perception_cleanup_error"
                failure_type = type(exc).__name__
        try:
            # Drain output already emitted even when the runner failed before an ended event.
            await asyncio.wait_for(outgoing.join(), 1)
        except TimeoutError:
            completion_status = "collector_error"
        finally:
            collector.cancel()
            collected = await asyncio.gather(collector, return_exceptions=True)
            if isinstance(collected[0], Exception):
                completion_status = "collector_error"
                failure_type = type(collected[0]).__name__
    if completion_status == "completed" and any(
            row["type"] == "output" and row["event"]["payload"].get("code") == "backend_failure" for row in events):
        completion_status = "backend_failure"
    tool_profile = "manifest-mock" if definition.environment is not None else "fake"
    metadata = {"type": "run_metadata", "scenario": scenario["id"], "backend": backend,
                "provenance": definition.provenance,
                "tools": tool_profile, "perception": perception_profile, "commit": commit_revision(),
                "perception_backends_observed": sorted(observed_backends),
                "python": platform.python_version(), "platform": platform.platform(),
                "runtime_s": time.perf_counter() - started, "expected_slots": scenario.get("expected_slots", {}),
                "measurement_clock": "perf_counter", "clock_resolution_s": time.get_clock_info("perf_counter").resolution,
                "completion_status": completion_status,
                "perception_cleanup": perception_cleanup,
                "failure_type": failure_type,
                "mock_executor_effect_count": len(tools.effects),
                "config": {"partial_debounce_s": agent.partial_debounce_s, "turn_policy": policy_profile,
                           "tools": tool_profile, "perception": perception_profile,
                           "component_config": component_config or {}}}
    metadata.update(source_evidence(path))
    outcome = evaluate_task(definition.expectation, events, tools.effects, inputs[0].payload.tools, completion_status)
    metadata["task_oracle"] = outcome
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(e) for e in [metadata, *events]) + "\n", encoding="utf-8")
    return {"trace": str(destination), "backend": backend, "events": len(events), "mock_effects": len(tools.effects),
            "completion_status": completion_status, "task_oracle": outcome}


def metrics(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    # Old flat output traces retain count/slot evidence but have no receipt timestamps.
    normalized = [({"type": "output", "event": row} if "kind" in row and "type" not in row else row)
                  for row in rows]
    return evaluate_trace(normalized)
