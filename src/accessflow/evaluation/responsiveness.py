"""Offline controller responsiveness measurements.

This module measures queue/controller orchestration only.  Every sample creates a
new :class:`~accessflow.engine.Agent`, reasoner, executor, and pair of queues.
The workers are deliberately gated so that an acknowledgement or cancellation
cannot be hidden by a blocked reasoner/tool worker.  These are synthetic timing
probes; they are not speech, throughput, model, or accessibility-benefit tests.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import platform
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from accessflow.contracts import (
    EndEvent,
    Interrupt,
    InterruptEvent,
    PlanProposal,
    ProposedCall,
    Start,
    StartEvent,
    ToolManifest,
    ToolResult,
    Transcript,
    TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.evaluation.replay import commit_revision, source_evidence
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner


ACK_TARGET_S = 0.300
CANCEL_TARGET_S = 0.050
DEFAULT_SAMPLES = 100
_PROBE_TIMEOUT_S = 0.75
_SCENARIOS = (
    "final_ack_reasoner_blocked",
    "interrupt_ack_reasoner_blocked",
    "tool_cancel_blocked",
    "fluent_final_request",
)


class _Gate:
    """An event gate with observable entered and pending states."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.waiters = 0

    async def wait(self) -> None:
        self.entered.set()
        self.waiters += 1
        try:
            await self.release.wait()
        finally:
            self.waiters -= 1

    def open(self) -> None:
        self.release.set()

    @property
    def pending(self) -> bool:
        return self.waiters > 0 and not self.release.is_set()


class _TimedInputQueue(asyncio.Queue):
    """Record when an input has been accepted by the queue."""

    def __init__(self) -> None:
        super().__init__()
        self.accepted: dict[str, float] = {}

    async def put(self, item: Any) -> None:
        await super().put(item)
        event_id = getattr(item, "event_id", None)
        if isinstance(event_id, str):
            self.accepted[event_id] = time.perf_counter()


class _TimedOutputQueue(asyncio.Queue):
    """Timestamp output queue acceptance, immediately after ``Queue.put``."""

    def __init__(self) -> None:
        super().__init__()
        self.accepted: list[tuple[Any, float]] = []
        self.accepted_states: list[dict[str, str]] = []
        self.changed = asyncio.Event()
        self.state_reader: Callable[[], dict[str, str]] | None = None

    def set_state_reader(self, reader: Callable[[], dict[str, str]]) -> None:
        self.state_reader = reader

    async def put(self, item: Any) -> None:
        await super().put(item)
        self.accepted.append((item, time.perf_counter()))
        self.accepted_states.append(self.state_reader() if self.state_reader else {})
        self.changed.set()

    def state_for(self, item: Any) -> dict[str, str]:
        for index, (candidate, _) in enumerate(self.accepted):
            if candidate is item:
                return self.accepted_states[index]
        return {}

    async def wait_for(self, predicate: Callable[[Any], bool], timeout: float = _PROBE_TIMEOUT_S) -> tuple[Any, float]:
        """Wait for a recorded output without consuming the queue."""

        deadline = time.perf_counter() + timeout
        seen = 0
        while True:
            for item, accepted_at in self.accepted[seen:]:
                if predicate(item):
                    return item, accepted_at
            seen = len(self.accepted)
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("expected output was not accepted")
            self.changed.clear()
            try:
                await asyncio.wait_for(self.changed.wait(), remaining)
            except TimeoutError as exc:
                raise TimeoutError("expected output was not accepted") from exc

    async def drain(self) -> None:
        while True:
            try:
                self.get_nowait()
            except asyncio.QueueEmpty:
                break
            else:
                self.task_done()
        await asyncio.wait_for(self.join(), _PROBE_TIMEOUT_S)


class _GatedReasoner:
    def __init__(self, gate: _Gate) -> None:
        self.gate = gate
        self.calls = 0

    async def plan(self, view, manifests):
        self.calls += 1
        await self.gate.wait()
        return PlanProposal()


class _GatedExecutor(FakeTools):
    def __init__(self, execute_gate: _Gate, cancel_gate: _Gate) -> None:
        super().__init__()
        self.execute_gate = execute_gate
        self.cancel_gate = cancel_gate
        self.call_id: str | None = None

    async def execute(self, call):
        self.call_id = call.call_id
        self.calls.append(call)
        await self.execute_gate.wait()
        return ToolResult(call_id=call.call_id, status="cancelled")

    async def cancel(self, call_id):
        await self.cancel_gate.wait()
        self.cancelled.add(call_id)
        return "cancelled_before_commit"


class _MeasuredAgent(Agent):
    """Instrumentation confined to evaluation; production Agent is untouched."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cancel_entries: list[float] = []

    async def _cancel(self, call, reason):
        self.cancel_entries.append(time.perf_counter())
        await super()._cancel(call, reason)


def _manifest() -> ToolManifest:
    return ToolManifest(
        name="synthetic_booking",
        description="Synthetic benchmark write",
        effect="write",
        parameters={
            "type": "object",
            "properties": {"day": {"type": "string"}, "request_id": {"type": "string"}},
            "required": ["day", "request_id"],
            "additionalProperties": False,
        },
        idempotency_parameter="request_id",
        timeout_s=1,
    )


def _write_proposal() -> PlanProposal:
    return PlanProposal(
        intent="synthetic booking",
        slot_updates={"day": "Wednesday"},
        request_complete=True,
        write_requested=True,
        calls=[ProposedCall(tool="synthetic_booking", arguments={"day": "Wednesday"}, dependencies=["day"])],
    )


def _event(session_id: str, event_id: str, sequence: int, *, final: bool, text: str) -> TranscriptEvent:
    return TranscriptEvent(
        session_id=session_id,
        event_id=event_id,
        sequence=sequence,
        payload=Transcript(utterance_id=event_id, revision=0, text=text, final=final),
    )


async def _stop_agent(agent: Agent, incoming: _TimedInputQueue, outgoing: _TimedOutputQueue,
                      runner: asyncio.Task[Any], session_id: str, gates: list[_Gate]) -> None:
    cleanup_errors: list[str] = []
    if not runner.done():
        await incoming.put(EndEvent(session_id=session_id, event_id=f"end-{uuid4()}", sequence=99))
    try:
        await asyncio.wait_for(asyncio.shield(runner), _PROBE_TIMEOUT_S)
    except TimeoutError:
        cleanup_errors.append("shutdown_timeout")
        for gate in gates:
            gate.open()
        runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)
    finally:
        for gate in gates:
            gate.open()
        try:
            await outgoing.drain()
        except TimeoutError:
            cleanup_errors.append("output_drain_timeout")
    await asyncio.sleep(0)
    if not incoming.empty():
        cleanup_errors.append("input_queue_not_empty")
    if getattr(agent, "inbox", None) is not None and not agent.inbox.empty():
        cleanup_errors.append("agent_inbox_not_empty")
    if getattr(agent, "workers", None):
        cleanup_errors.append("worker_tasks_remaining")
    if cleanup_errors:
        raise RuntimeError(";".join(cleanup_errors))


def _gate_state(gate: _Gate) -> str:
    if gate.pending:
        return "entered_pending"
    if gate.entered.is_set():
        return "entered_released"
    return "not_entered"


def _set_cleanup_failure(record: dict[str, Any], exc: Exception) -> None:
    record.update(status="failed", failure_type=type(exc).__name__, cleanup_failure=True)


def _duration(start: float | None, finish: float | None) -> float | None:
    if start is None or finish is None:
        return None
    value = finish - start
    return round(value, 9) if math.isfinite(value) and value >= 0 else None


def _base_record(index: int, scenario: str, session_id: str) -> dict[str, Any]:
    return {
        "type": "responsiveness_sample",
        "measurement_clock": "perf_counter",
        "clock_origin": "process-local monotonic perf_counter origin",
        "sample": index,
        "scenario": scenario,
        "session_id": session_id,
        "status": "failed",
        "failure_type": None,
    }


async def _run_final_ack(index: int) -> dict[str, Any]:
    scenario = _SCENARIOS[0]
    session_id = f"responsiveness-{index}-{scenario}"
    record = _base_record(index, scenario, session_id)
    gate = _Gate()
    incoming, outgoing = _TimedInputQueue(), _TimedOutputQueue()
    outgoing.set_state_reader(lambda: {"reasoner": _gate_state(gate)})
    agent = _MeasuredAgent(FakePerception(), FinalFlagPolicy(), _GatedReasoner(gate),
                           scenario_timeout=2, inference_timeout=1, partial_debounce_s=0)
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, event_id=f"start-{uuid4()}",
                                      payload=Start(tools=[]), sequence=0))
        prep = _event(session_id, f"prep-{uuid4()}", 1, final=False, text="Book")
        await incoming.put(prep)
        await asyncio.wait_for(gate.entered.wait(), _PROBE_TIMEOUT_S)
        probe = _event(session_id, f"probe-{uuid4()}", 2, final=True, text="Book Wednesday")
        await incoming.put(probe)
        input_at = incoming.accepted[probe.event_id]
        output, output_at = await outgoing.wait_for(
            lambda event: event.kind == "acknowledge" and event.payload.get("caused_by_event_id") == probe.event_id
        )
        output_state = outgoing.state_for(output)
        if output_state.get("reasoner") != "entered_pending":
            raise RuntimeError("reasoner gate was not pending at acknowledgement")
        record.update(input_event_id=probe.event_id, input_accepted_at=input_at,
                     output_event_id=output.event_id, output_accepted_at=output_at,
                     input_enqueue_to_ack_s=_duration(input_at, output_at),
                     output_kind=output.kind, gates=output_state, status="passed")
    except Exception as exc:
        record.update(failure_type=type(exc).__name__, gates={"reasoner": _gate_state(gate)})
    finally:
        try:
            await _stop_agent(agent, incoming, outgoing, runner, session_id, [gate])
        except Exception as exc:
            _set_cleanup_failure(record, exc)
    return record


async def _run_interrupt_ack(index: int) -> dict[str, Any]:
    scenario = _SCENARIOS[1]
    session_id = f"responsiveness-{index}-{scenario}"
    record = _base_record(index, scenario, session_id)
    gate = _Gate()
    incoming, outgoing = _TimedInputQueue(), _TimedOutputQueue()
    outgoing.set_state_reader(lambda: {"reasoner": _gate_state(gate)})
    agent = _MeasuredAgent(FakePerception(), FinalFlagPolicy(), _GatedReasoner(gate),
                           scenario_timeout=2, inference_timeout=1, partial_debounce_s=0)
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, event_id=f"start-{uuid4()}",
                                      payload=Start(tools=[]), sequence=0))
        prep = _event(session_id, f"prep-{uuid4()}", 1, final=False, text="Book")
        await incoming.put(prep)
        await asyncio.wait_for(gate.entered.wait(), _PROBE_TIMEOUT_S)
        probe = InterruptEvent(session_id=session_id, event_id=f"probe-{uuid4()}", sequence=2,
                               payload=Interrupt(scope="task"))
        await incoming.put(probe)
        input_at = incoming.accepted[probe.event_id]
        output, output_at = await outgoing.wait_for(
            lambda event: event.kind == "acknowledge" and event.payload.get("stop_output") is True
            and event.payload.get("caused_by_event_id") == probe.event_id
        )
        output_state = outgoing.state_for(output)
        if output_state.get("reasoner") != "entered_pending":
            raise RuntimeError("reasoner gate was not pending at interruption acknowledgement")
        record.update(input_event_id=probe.event_id, input_accepted_at=input_at,
                     output_event_id=output.event_id, output_accepted_at=output_at,
                     input_enqueue_to_ack_s=_duration(input_at, output_at),
                     output_kind=output.kind, gates=output_state, status="passed")
    except Exception as exc:
        record.update(failure_type=type(exc).__name__, gates={"reasoner": _gate_state(gate)})
    finally:
        try:
            await _stop_agent(agent, incoming, outgoing, runner, session_id, [gate])
        except Exception as exc:
            _set_cleanup_failure(record, exc)
    return record


async def _run_tool_cancel(index: int) -> dict[str, Any]:
    scenario = _SCENARIOS[2]
    session_id = f"responsiveness-{index}-{scenario}"
    record = _base_record(index, scenario, session_id)
    execute_gate, cancel_gate = _Gate(), _Gate()
    incoming, outgoing = _TimedInputQueue(), _TimedOutputQueue()
    reasoner = ScriptedReasoner([_write_proposal()])
    executor = _GatedExecutor(execute_gate, cancel_gate)
    outgoing.set_state_reader(lambda: {"tool": _gate_state(execute_gate),
                                       "cancellation_transport": _gate_state(cancel_gate)})
    agent = _MeasuredAgent(FakePerception(), FinalFlagPolicy(), reasoner, executor,
                           MockOnlyAuthorization(), scenario_timeout=2, inference_timeout=1,
                           partial_debounce_s=0)
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, event_id=f"start-{uuid4()}",
                                      payload=Start(tools=[_manifest()]), sequence=0))
        probe = _event(session_id, f"probe-{uuid4()}", 1, final=True, text="Book Wednesday")
        await incoming.put(probe)
        tool_call, tool_call_at = await outgoing.wait_for(
            lambda event: event.kind == "tool_call" and event.payload.get("caused_by_event_id") == probe.event_id
        )
        await asyncio.wait_for(execute_gate.entered.wait(), _PROBE_TIMEOUT_S)
        interrupt = InterruptEvent(session_id=session_id, event_id=f"interrupt-{uuid4()}", sequence=2,
                                   payload=Interrupt(scope="task"))
        await incoming.put(interrupt)
        input_at = incoming.accepted[interrupt.event_id]
        cancel_output, cancel_at = await outgoing.wait_for(
            lambda event: event.kind == "cancel_call" and event.payload.get("caused_by_event_id") == interrupt.event_id
        )
        stop_output, stop_at = await outgoing.wait_for(
            lambda event: event.kind == "acknowledge" and event.payload.get("stop_output") is True
            and event.payload.get("caused_by_event_id") == interrupt.event_id
        )
        # The cancellation transport must have entered and remain blocked while both
        # controller outputs are already accepted.  Release happens only in finally.
        await asyncio.wait_for(cancel_gate.entered.wait(), _PROBE_TIMEOUT_S)
        cancel_entry = agent.cancel_entries[0] if agent.cancel_entries else None
        cancel_entry_to_emission = _duration(cancel_entry, cancel_at)
        cancel_state = outgoing.state_for(cancel_output)
        stop_state = outgoing.state_for(stop_output)
        if cancel_state.get("tool") != "entered_pending" or stop_state.get("tool") != "entered_pending":
            raise RuntimeError("tool gate was not pending at controller output")
        if cancel_state.get("cancellation_transport") != "not_entered":
            raise RuntimeError("cancellation transport entered before cancellation emission")
        if stop_state.get("cancellation_transport") != "not_entered":
            raise RuntimeError("cancellation transport completed before stop acknowledgement")
        if _gate_state(cancel_gate) != "entered_pending":
            raise RuntimeError("cancellation transport was not pending after controller outputs")
        record.update(
            input_event_id=interrupt.event_id,
            input_accepted_at=input_at,
            tool_call_event_id=tool_call.event_id,
            tool_call_accepted_at=tool_call_at,
            tool_call_id=tool_call.payload.get("call_id"),
            cancel_entry_at=cancel_entry,
            cancel_event_id=cancel_output.event_id,
            cancel_accepted_at=cancel_at,
            stop_ack_event_id=stop_output.event_id,
            stop_ack_accepted_at=stop_at,
            input_enqueue_to_cancel_s=_duration(input_at, cancel_at),
            input_enqueue_to_ack_s=_duration(input_at, stop_at),
            cancel_entry_to_emission_s=cancel_entry_to_emission,
            cancel_output_kind=cancel_output.kind,
            ack_output_kind=stop_output.kind,
            gates={"tool_at_cancel_emission": cancel_state.get("tool"),
                   "cancellation_transport_at_cancel_emission": cancel_state.get("cancellation_transport"),
                   "tool_at_stop_ack": stop_state.get("tool"),
                   "cancellation_transport_at_stop_ack": stop_state.get("cancellation_transport"),
                   "cancellation_transport_after_outputs": _gate_state(cancel_gate)},
            status="passed",
        )
    except Exception as exc:
        record.update(failure_type=type(exc).__name__, gates={
            "tool": _gate_state(execute_gate), "cancellation_transport": _gate_state(cancel_gate),
        })
    finally:
        try:
            await _stop_agent(agent, incoming, outgoing, runner, session_id, [execute_gate, cancel_gate])
        except Exception as exc:
            _set_cleanup_failure(record, exc)
    return record


async def _run_fluent_final(index: int) -> dict[str, Any]:
    scenario = _SCENARIOS[3]
    session_id = f"responsiveness-{index}-{scenario}"
    record = _base_record(index, scenario, session_id)
    incoming, outgoing = _TimedInputQueue(), _TimedOutputQueue()
    reasoner = ScriptedReasoner([PlanProposal(response="The synthetic request is complete.")])
    agent = _MeasuredAgent(FakePerception(), FinalFlagPolicy(), reasoner,
                           scenario_timeout=2, inference_timeout=1, partial_debounce_s=0)
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, event_id=f"start-{uuid4()}",
                                      payload=Start(tools=[]), sequence=0))
        probe = _event(session_id, f"probe-{uuid4()}", 1, final=True, text="Please summarize this request")
        await incoming.put(probe)
        input_at = incoming.accepted[probe.event_id]
        ack, ack_at = await outgoing.wait_for(
            lambda event: event.kind == "acknowledge" and event.payload.get("caused_by_event_id") == probe.event_id
        )
        final, final_at = await outgoing.wait_for(
            lambda event: event.kind == "final" and event.payload.get("caused_by_event_id") == probe.event_id
        )
        record.update(input_event_id=probe.event_id, input_accepted_at=input_at,
                     acknowledge_event_id=ack.event_id, acknowledge_accepted_at=ack_at,
                     final_event_id=final.event_id, final_accepted_at=final_at,
                     input_enqueue_to_ack_s=_duration(input_at, ack_at),
                     input_enqueue_to_final_s=_duration(input_at, final_at),
                     output_kind=final.kind, gates={}, status="passed")
    except Exception as exc:
        record.update(failure_type=type(exc).__name__, gates={})
    finally:
        try:
            await _stop_agent(agent, incoming, outgoing, runner, session_id, [])
        except Exception as exc:
            _set_cleanup_failure(record, exc)
    return record


async def _run_one(index: int, scenario: str) -> dict[str, Any]:
    if scenario == _SCENARIOS[0]:
        return await _run_final_ack(index)
    if scenario == _SCENARIOS[1]:
        return await _run_interrupt_ack(index)
    if scenario == _SCENARIOS[2]:
        return await _run_tool_cancel(index)
    if scenario == _SCENARIOS[3]:
        return await _run_fluent_final(index)
    raise ValueError(f"unknown responsiveness scenario: {scenario}")


def _quantiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"sample_count": 0, "p50_s": None, "p95_s": None, "p99_s": None}
    ordered = sorted(values)

    def percentile(p: float) -> float:
        position = (len(ordered) - 1) * p
        lower, upper = math.floor(position), math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    return {"sample_count": len(ordered), "p50_s": round(percentile(0.50), 9),
            "p95_s": round(percentile(0.95), 9), "p99_s": round(percentile(0.99), 9)}


def _metric(records: list[dict[str, Any]], field: str, expected_count: int, target: float) -> dict[str, Any]:
    values = [record[field] for record in records
              if record.get("status") == "passed"
              and isinstance(record.get(field), (int, float))
              and not isinstance(record.get(field), bool)
              and math.isfinite(record[field]) and record[field] >= 0]
    failed = sum(1 for record in records
                 if record.get("status") != "passed"
                 or not isinstance(record.get(field), (int, float))
                 or isinstance(record.get(field), bool)
                 or not math.isfinite(record[field])
                 or record[field] < 0)
    failed += max(0, expected_count - len(records))
    result = _quantiles(values)
    pass_count = sum(value < target for value in values)
    result.update({"expected_count": expected_count, "failed_or_missing_count": failed,
                   "target_s": target, "pass_count": pass_count,
                   "pass_rate_over_expected": pass_count / expected_count if expected_count else None,
                   "target_passed": failed == 0 and result["p95_s"] is not None and result["p95_s"] < target})
    return result


async def run_responsiveness(output_dir: str | os.PathLike[str], samples: int = DEFAULT_SAMPLES) -> dict[str, Any]:
    """Run isolated offline responsiveness probes and persist JSONL plus a report.

    ``samples`` is the number of independent executions of each of the four
    synthetic scenarios.  A failed execution remains in the report denominator.
    """

    if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    for index in range(1, samples + 1):
        for scenario in _SCENARIOS:
            try:
                records.append(await asyncio.wait_for(_run_one(index, scenario), _PROBE_TIMEOUT_S * 3))
            except Exception as exc:
                failed = _base_record(index, scenario, f"responsiveness-{index}-{scenario}")
                failed.update(failure_type=type(exc).__name__)
                records.append(failed)

    metadata = {
        "type": "run_metadata",
        "schema_version": "responsiveness.v1",
        "backend": "offline-fake",
        "provenance": "synthetic controller benchmark; scripted perception, final-flag policy, and gated workers",
        "sample_count_per_scenario": samples,
        "scenario_count": len(_SCENARIOS),
        "measurement_clock": "perf_counter",
        "clock_origin": "process-local monotonic perf_counter origin; compare timestamps within this run",
        "clock_resolution_s": time.get_clock_info("perf_counter").resolution,
        "commit": commit_revision(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "runtime_s": round(time.perf_counter() - started, 9),
        "config": {"ack_target_s": ACK_TARGET_S, "cancel_target_s": CANCEL_TARGET_S,
                   "scenarios": list(_SCENARIOS), "samples": samples,
                   "probe_timeout_s": _PROBE_TIMEOUT_S, "scenario_timeout_s": 2,
                   "inference_timeout_s": 1, "partial_debounce_s": 0,
                   "quantile_method": "linear_interpolation_inclusive"},
    }
    evidence = source_evidence(Path(__file__))
    metadata.update({key: value for key, value in evidence.items() if key != "scenario_sha256"})
    metadata["benchmark_sha256"] = evidence["scenario_sha256"]
    jsonl = output / "responsiveness.jsonl"
    jsonl.write_text("\n".join(json.dumps(row, sort_keys=True) for row in [metadata, *records]) + "\n",
                     encoding="utf-8")

    by_scenario = {scenario: [record for record in records if record["scenario"] == scenario]
                   for scenario in _SCENARIOS}
    counts = {"passed": sum(record["status"] == "passed" for record in records),
              "failed": sum(record["status"] != "passed" for record in records),
              "total": len(records)}
    ack_records = records
    cancel_records = by_scenario[_SCENARIOS[2]]

    def valid_values(rows: list[dict[str, Any]], field: str) -> list[float]:
        return [row[field] for row in rows if row.get("status") == "passed"
                and isinstance(row.get(field), (int, float)) and not isinstance(row.get(field), bool)
                and math.isfinite(row[field]) and row[field] >= 0]

    def scenario_latency(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
        return _quantiles(valid_values(rows, field))

    latency_by_scenario = {
        name: {
            "acknowledgment_from_input_enqueue_s": scenario_latency(rows, "input_enqueue_to_ack_s"),
            "substantive_response_from_input_enqueue_s": scenario_latency(rows, "input_enqueue_to_final_s"),
            "cancellation_from_input_enqueue_s": scenario_latency(rows, "input_enqueue_to_cancel_s"),
            "cancellation_entry_to_emission_s": scenario_latency(rows, "cancel_entry_to_emission_s"),
        }
        for name, rows in by_scenario.items()
    }
    report = {
        "report_version": "responsiveness-report.v1",
        "backend": "offline-fake",
        "samples_per_scenario": samples,
        "scenario_count": len(_SCENARIOS),
        "counts": counts,
        "counts_by_scenario": {name: {"total": len(rows), "passed": sum(r["status"] == "passed" for r in rows),
                                       "failed": sum(r["status"] != "passed" for r in rows)}
                                for name, rows in by_scenario.items()},
        "latency": {
            "acknowledgment_from_input_enqueue_s": _quantiles(
                valid_values(ack_records, "input_enqueue_to_ack_s")),
            "cancellation_from_input_enqueue_s": _quantiles(
                valid_values(cancel_records, "input_enqueue_to_cancel_s")),
            "cancellation_entry_to_emission_s": _quantiles(
                valid_values(cancel_records, "cancel_entry_to_emission_s")),
        },
        "latency_by_scenario": latency_by_scenario,
        "targets": {
            "acknowledgment_internal_300ms": _metric(ack_records, "input_enqueue_to_ack_s",
                                                       samples * len(_SCENARIOS), ACK_TARGET_S),
            "cancellation_internal_50ms": _metric(cancel_records, "cancel_entry_to_emission_s",
                                                    samples, CANCEL_TARGET_S),
        },
        "metadata": metadata,
        "raw_jsonl": str(jsonl),
        "limitation": "Synthetic offline orchestration evidence only; no clinical, accessibility-benefit, throughput, ASR, or live-model claim.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


__all__ = ["run_responsiveness"]
