import asyncio
import json
import os
import platform
import subprocess
import time
from pathlib import Path

from accessflow.contracts import EndEvent, PlanProposal, ResultEvent
from accessflow.adapters.internal import parse_event
from accessflow.engine import Agent
from accessflow.fakes import EventReasoner, FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization
from accessflow.evaluation.trace_metrics import evaluate_trace


def commit_revision():
    supplied = os.getenv("ACCESSFLOW_COMMIT")
    if supplied:
        return supplied
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, timeout=2)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


async def replay(path, output, reasoner=None, backend="offline-fake"):
    scenario = json.loads(Path(path).read_text(encoding="utf-8"))
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    class RecordedTools(FakeTools):
        async def execute(self, call):
            result = await super().execute(call)
            record("input", ResultEvent(session_id=scenario["events"][0]["session_id"], payload=result),
                   transport="executor_return")
            return result

    tools = RecordedTools()
    inputs = [parse_event(entry) for entry in scenario["events"]]
    perception_inputs = [entry for entry in inputs if entry.kind in {"transcript", "audio", "frame"}]
    fixture_plans = {} if reasoner is not None else {
        event.event_id: PlanProposal.model_validate(plan)
        for event, plan in zip(perception_inputs, scenario["proposals"], strict=True)}
    agent = Agent(FakePerception(), FinalFlagPolicy(), reasoner or EventReasoner(fixture_plans),
                  tools, MockOnlyAuthorization())
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    events = []
    started = time.perf_counter()
    terminal = asyncio.Event()
    completion_status = "completed"

    def record(kind, event, transport="queue"):
        events.append({"type": kind, "event": event.model_dump(mode="json"),
                       "observed_at": time.perf_counter() - started, "transport": transport})

    async def collect():
        while True:
            event = await outgoing.get()
            record("output", event)
            if event.kind == "final" or event.payload.get("code") == "backend_failure":
                terminal.set()
            if event.state.status == "ended":
                return

    collector = asyncio.create_task(collect())
    try:
        for entry in inputs:
            record("input", entry)
            await incoming.put(entry)
            # Explicit test pacing, not an inferred speech/end-of-turn measurement.
            await asyncio.sleep(scenario.get("event_spacing_s", 0.01))
        await asyncio.wait_for(terminal.wait(), min(scenario.get("completion_timeout_s", 30), 110))
    except TimeoutError:
        completion_status = "timeout"
    finally:
        ending = EndEvent(session_id=scenario["events"][0]["session_id"])
        record("input", ending)
        await incoming.put(ending)
        try:
            await runner
            await asyncio.wait_for(collector, 1)
        finally:
            collector.cancel()
            await asyncio.gather(collector, return_exceptions=True)
    if any(row["type"] == "output" and row["event"]["payload"].get("code") == "backend_failure" for row in events):
        completion_status = "backend_failure"
    metadata = {"type": "run_metadata", "scenario": scenario["id"], "backend": backend,
                "tools": "fake", "perception": "text-pass-through", "commit": commit_revision(),
                "python": platform.python_version(), "platform": platform.platform(),
                "runtime_s": time.perf_counter() - started, "expected_slots": scenario.get("expected_slots", {}),
                "measurement_clock": "perf_counter", "clock_resolution_s": time.get_clock_info("perf_counter").resolution,
                "completion_status": completion_status,
                "mock_executor_effect_count": len(tools.effects),
                "config": {"partial_debounce_s": agent.partial_debounce_s, "turn_policy": "final-flag-baseline",
                           "tools": "fake", "perception": "text-pass-through"}}
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(e) for e in [metadata, *events]) + "\n", encoding="utf-8")
    return {"trace": str(destination), "backend": backend, "events": len(events), "mock_effects": len(tools.effects),
            "completion_status": completion_status}


def metrics(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    # Old flat output traces retain count/slot evidence but have no receipt timestamps.
    normalized = [({"type": "output", "event": row} if "kind" in row and "type" not in row else row)
                  for row in rows]
    return evaluate_trace(normalized)
