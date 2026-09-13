import asyncio

import pytest

from accessflow.contracts import Interrupt, InterruptEvent, ResultEvent, ToolResult
from accessflow.fakes import FakeTools
from test_safety import end, proposal, start, transcript, wait_for


@pytest.mark.parametrize("status", ["failed", "cancelled", "unknown"])
async def test_explicit_committed_effect_survives_inconsistent_transport_status(status):
    class ConflictingExecutor(FakeTools):
        async def execute(self, call):
            result = await super().execute(call)
            return result.model_copy(update={"status": status})

    executor = ConflictingExecutor()
    agent, incoming, outgoing, runner = await start([proposal()], tools=executor)
    try:
        await incoming.put(transcript())
        warning = await wait_for(outgoing, lambda e: e.payload.get("code") == "inconsistent_tool_result")
        assert warning.payload["reported_status"] == status
        final = await wait_for(outgoing, lambda e: e.kind == "final")
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert agent.ledger[final.payload["call_id"]].status == "success"
        assert len(executor.effects) == 1
    finally:
        await end(incoming, runner)


async def test_late_commit_after_confirmed_cancel_is_reported_and_kept_in_ledger():
    release = asyncio.Event()
    entered = asyncio.Event()

    class FaultyCancellationExecutor(FakeTools):
        async def execute(self, call):
            entered.set()
            return await super().execute(call)

        async def cancel(self, call_id):
            # Fault injection: a broken adapter claims cancellation but will commit anyway.
            return "cancelled_before_commit"

    executor = FaultyCancellationExecutor(gate=release, ignore_cancel=True)
    agent, incoming, outgoing, runner = await start([proposal()], tools=executor)
    try:
        await incoming.put(transcript())
        await asyncio.wait_for(entered.wait(), 1)
        call_event = await wait_for(outgoing, lambda e: e.kind == "tool_call")
        call_id = call_event.payload["call_id"]
        await incoming.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        await wait_for(outgoing, lambda e: e.payload.get("stop_output"))
        async with asyncio.timeout(1):
            while agent.ledger[call_id].status != "failed":
                await asyncio.sleep(0)
        release.set()
        warning = await wait_for(outgoing, lambda e: e.payload.get("code") == "effect_committed_after_invalidation")
        assert warning.payload["previous_status"] == "failed"
        assert warning.payload["operation_id"] == call_event.payload["operation_id"]
        assert agent.ledger[call_id].status == "success"
        assert any(result.call_id == call_id and result.committed for result in agent.results)
        assert len(executor.effects) == 1
        assert agent.state.status == "stopped"
        while not outgoing.empty():
            assert outgoing.get_nowait().kind != "final"
    finally:
        release.set()
        await end(incoming, runner)


async def test_late_commit_after_failure_emits_conflict_once_without_new_final():
    release, entered = asyncio.Event(), asyncio.Event()

    class DelayedExecutor(FakeTools):
        async def execute(self, call):
            entered.set()
            return await super().execute(call)

    executor = DelayedExecutor(gate=release)
    agent, incoming, outgoing, runner = await start([proposal()], tools=executor)
    try:
        await incoming.put(transcript())
        await asyncio.wait_for(entered.wait(), 1)
        call_event = await wait_for(outgoing, lambda e: e.kind == "tool_call")
        call_id = call_event.payload["call_id"]
        await incoming.put(ResultEvent(session_id="s", payload=ToolResult(call_id=call_id, status="failed")))
        await wait_for(outgoing, lambda e: e.payload.get("code") == "tool_failed")
        release.set()
        warning = await wait_for(outgoing, lambda e: e.payload.get("code") == "conflicting_write_outcome")
        assert warning.payload["caused_by_event_id"] == call_event.payload["caused_by_event_id"]
        assert agent.ledger[call_id].status == "success"
        await incoming.put(ResultEvent(session_id="s", payload=ToolResult(
            call_id=call_id, status="success", committed=True)))
        await incoming.put(ResultEvent(session_id="s", payload=ToolResult(call_id=call_id, status="failed")))
        # A following interrupt acts as a queue-processing barrier for both deliveries.
        await incoming.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        seen = []
        async with asyncio.timeout(1):
            while True:
                event = await outgoing.get()
                seen.append(event)
                if event.payload.get("stop_output"):
                    break
        assert all(event.kind != "final" for event in seen)
        assert not any(event.payload.get("code") == "conflicting_write_outcome" for event in seen)
        assert agent.ledger[call_id].status == "success"
        assert len(executor.effects) == 1
    finally:
        release.set()
        await end(incoming, runner)
