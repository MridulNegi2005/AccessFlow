"""Offline integration of the real controller with the official queue boundary."""

import asyncio

import pytest

from accessflow.adapters.samsung import (
    HarnessAuthorization, ParticipantAgent, PRE_MANIFEST_BYTE_LIMIT, PRE_MANIFEST_EVENT_LIMIT,
)
from accessflow.contracts import PlanProposal, ProposedCall
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FinalFlagPolicy, ScriptedReasoner


def event(kind, payload, at=0):
    return {"timestamp_ms": at, "event_type": kind, "payload": payload}


async def action(queue, kind):
    async with asyncio.timeout(2):
        while True:
            item = await queue.get()
            if item["action"] == kind:
                return item


async def prepared(tmp_path, plans):
    async def factory():
        return Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner(plans),
                     authorization=HarnessAuthorization(), partial_debounce_s=0)

    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    participant = ParticipantAgent(incoming, outgoing, agent_factory=factory, media_root=tmp_path)
    await participant.setup()
    return participant, incoming, outgoing


@pytest.mark.asyncio
async def test_real_controller_finishes_tool_during_official_tail(tmp_path):
    participant, incoming, outgoing = await prepared(tmp_path, [PlanProposal(
        intent="reserve", slot_updates={"day": "Wednesday"}, request_complete=True,
        write_requested=True, calls=[ProposedCall(tool="reserve_slot", arguments={"day": "Wednesday"},
                                                dependencies=["day"])])])
    task = asyncio.create_task(participant.run())
    try:
        await incoming.put(event("tool_manifest", {"schema_version": "1.0", "tools": {
            "reserve_slot": {"kind": "state_modifying", "description": "Reserve a slot",
                             "args": {"day": {"type": "string", "required": True}},
                             "delay_range_ms": [100, 200]}}}))
        await incoming.put(event("user_speech_chunk", {"text": "Reserve Wednesday", "end_of_turn": True}, 10))
        call = await action(outgoing, "tool_call")
        assert call["payload"]["args"] == {"day": "Wednesday"}
        await incoming.put(event("scenario_end", {}, 11))
        await incoming.put(event("tool_result", {
            "call_id": call["payload"]["call_id"], "api_name": "reserve_slot", "status": "success",
            "result": {"status": "success", "reservation_id": "R-1"}}, 50))
        final = await action(outgoing, "final_response")
        assert final["state_snapshot"]["slots"]["day"] == "Wednesday"
        assert final["payload"]["text"].strip()
        assert not task.done(), "scenario_end must leave the result channel alive"
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert not participant.tasks
    assert not participant.agent.running


@pytest.mark.asyncio
async def test_input_failure_stops_all_pumps_instead_of_silently_hanging(tmp_path):
    participant, incoming, _ = await prepared(tmp_path, [])
    task = asyncio.create_task(participant.run())
    await incoming.put(event("not_an_official_event", {}))
    with pytest.raises(ValueError):
        await asyncio.wait_for(task, 2)
    assert not participant.tasks
    assert not participant.agent.running


async def test_early_speech_waits_for_manifest_then_replays_in_order(tmp_path):
    participant, source, outgoing = await prepared(tmp_path, [])
    internal = asyncio.Queue()
    waiting_again = asyncio.Event()
    original_get = source.get
    gets = 0

    async def observed_get():
        nonlocal gets
        gets += 1
        if gets == 3:
            waiting_again.set()  # Both earlier chunks have been processed by the input pump.
        return await original_get()

    source.get = observed_get
    pump = asyncio.create_task(participant._pump_input(internal))
    try:
        first = event("user_speech_chunk", {"text": "Reserve ", "end_of_turn": False}, 10)
        await source.put(first)
        await source.put(event("user_speech_chunk", {"text": "Wednesday", "end_of_turn": True}, 20))
        await asyncio.wait_for(waiting_again.wait(), 2)
        first["payload"]["text"] = "mutated after admission"
        assert internal.empty() and outgoing.empty()
        assert not participant.protocol.tools
        await source.put(event("tool_manifest", {"schema_version": "1.0", "tools": {"reserve_slot": {
            "kind": "state_modifying", "args": {"day": {"type": "string", "required": True}}}}}, 30))
        async with asyncio.timeout(2):
            start, partial, final = [await internal.get() for _ in range(3)]
        assert start.kind == "session_start"
        assert partial.payload.text == "Reserve "
        assert final.payload.text == "Reserve Wednesday"
        assert (partial.timestamp, final.timestamp) == (0.01, 0.02)
        assert partial.sequence < final.sequence
    finally:
        if pump.done() and not pump.cancelled():
            pump.result()
        pump.cancel()
        await asyncio.gather(pump, return_exceptions=True)


@pytest.mark.parametrize("overflow", ["count", "bytes"])
async def test_startup_buffer_overflow_stops_runtime_without_actions(tmp_path, overflow):
    participant, incoming, outgoing = await prepared(tmp_path, [])
    task = asyncio.create_task(participant.run())
    message = event("user_speech_chunk", {"text": "hello", "end_of_turn": False})
    count = PRE_MANIFEST_EVENT_LIMIT + 1
    if overflow == "bytes":
        count = 1
        message["payload"]["text"] = "x" * PRE_MANIFEST_BYTE_LIMIT
    for _ in range(count):
        await incoming.put(message)
    with pytest.raises(ValueError, match="startup buffer"):
        await asyncio.wait_for(task, 2)
    assert outgoing.empty()
    assert not participant.tasks and not participant.agent.running


async def test_early_tool_result_is_not_admitted_as_buffered_evidence(tmp_path):
    participant, incoming, outgoing = await prepared(tmp_path, [])
    task = asyncio.create_task(participant.run())
    await incoming.put(event("tool_result", {"status": "success", "result": {"approved": True}}))
    with pytest.raises(ValueError, match="tool_manifest"):
        await asyncio.wait_for(task, 2)
    assert outgoing.empty() and not participant.tasks


async def test_cancel_before_manifest_cleans_up_without_model_work(tmp_path):
    participant, incoming, outgoing = await prepared(tmp_path, [])
    task = asyncio.create_task(participant.run())
    await incoming.put(event("user_speech_chunk", {"text": "hello", "end_of_turn": False}))
    # Give run() the event loop so its managed pumps exist before cancellation.
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert outgoing.empty() and not participant.tasks
    assert not participant.agent.running


@pytest.mark.asyncio
async def test_requires_setup_and_one_instance_per_session(tmp_path):
    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path)
    with pytest.raises(RuntimeError, match="setup"):
        await participant.run()
    participant, _, _ = await prepared(tmp_path, [])
    task = asyncio.create_task(participant.run())
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="fresh"):
        await participant.run()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    with pytest.raises(RuntimeError, match="fresh"):
        await participant.run()


@pytest.mark.asyncio
async def test_failed_setup_does_not_retry_a_model_on_the_scenario_clock(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_SAMSUNG_BACKEND", raising=False)
    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path)
    with pytest.raises(ValueError, match="BACKEND"):
        await participant.setup()
    with pytest.raises(RuntimeError, match="setup"):
        await participant.run()


@pytest.mark.asyncio
async def test_missing_media_cancels_pending_write_and_keeps_session_alive(tmp_path):
    participant, incoming, outgoing = await prepared(tmp_path, [PlanProposal(
        intent="reserve", slot_updates={"day": "Wednesday"}, request_complete=True,
        write_requested=True, calls=[ProposedCall(tool="reserve_slot", arguments={"day": "Wednesday"},
                                                dependencies=["day"])])])
    task = asyncio.create_task(participant.run())
    try:
        await incoming.put(event("tool_manifest", {"schema_version": "1.0", "tools": {
            "reserve_slot": {"kind": "state_modifying", "description": "Reserve a slot",
                             "args": {"day": {"type": "string", "required": True}}}}}))
        await incoming.put(event("user_speech_chunk", {"text": "Reserve Wednesday", "end_of_turn": True}, 10))
        call = await action(outgoing, "tool_call")
        await incoming.put(event("video_frame", {"image_ref": "frames/missing.png", "frame_id": "new"}, 20))
        received = []
        async with asyncio.timeout(2):
            while not {"cancel_tool", "clarification_request"}.issubset({a["action"] for a in received}):
                received.append(await outgoing.get())
        cancellation = next(a for a in received if a["action"] == "cancel_tool")
        assert cancellation["payload"]["call_id"] == call["payload"]["call_id"]
        assert not task.done()
        assert participant.agent.state.correction_pending
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
