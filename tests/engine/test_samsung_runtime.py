"""Offline integration of the real controller with the official queue boundary."""

import asyncio

import pytest

from accessflow.adapters.samsung import HarnessAuthorization, ParticipantAgent
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
