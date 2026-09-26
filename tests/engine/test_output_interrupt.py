"""Explicit playback controls preserve task authority and in-flight execution."""

import asyncio
from copy import deepcopy

import pytest

from accessflow.contracts import Interrupt, InterruptEvent
from tests.engine.test_pending_frame import setup, frame
from test_safety import end, transcript, wait_for


def control():
    return InterruptEvent(session_id="s", payload=Interrupt(scope="output"))


def task_context(agent):
    return deepcopy((agent.state, agent.request_id, agent.generation,
                     agent.perception_epoch, agent.write_intent_retained,
                     agent.speech_ready, agent.latest_complete,
                     agent._user_fixed_slots, agent._intent_user_fixed,
                     agent._slot_value_origin, agent.ledger, agent.observations))


@pytest.mark.parametrize("kind", ["read", "write"])
async def test_output_stop_preserves_pending_call_and_authority(kind):
    agent, incoming, outgoing, task = await setup(kind)
    agent.executor.gate = asyncio.Event()
    try:
        await incoming.put(transcript("Book Wednesday"))
        call = await wait_for(outgoing, lambda e: e.kind == "tool_call")
        before = task_context(agent)
        event = control()
        await incoming.put(event)
        ack = await wait_for(outgoing, lambda e: e.payload.get("caused_by_event_id") == event.event_id)
        assert ack.kind == "acknowledge"
        assert ack.payload["stop_output"] and ack.payload["output_only"]
        assert not ack.payload.get("text")  # Do not speak a new response to a playback stop.
        assert task_context(agent) == before
        assert not agent.executor.cancelled
        agent.executor.gate.set()
        async with asyncio.timeout(2):
            while agent.ledger[call.payload["call_id"]].status == "pending":
                await asyncio.sleep(0)
        assert agent.ledger[call.payload["call_id"]].status == "success"
        if kind == "write":
            assert len(agent.executor.effects) == 1
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


async def test_output_stop_preserves_pending_frame_worker():
    agent, incoming, outgoing, task = await setup()
    try:
        await incoming.put(frame())
        await asyncio.wait_for(agent.perception.started.get(), 2)
        worker = agent.perception_workers[("image", "f1")]
        before = task_context(agent)
        event = control()
        await incoming.put(event)
        await wait_for(outgoing, lambda e: e.payload.get("caused_by_event_id") == event.event_id)
        assert task_context(agent) == before
        assert not worker.done()
        agent.perception.release["f1"].set()
        await wait_for(outgoing, lambda e: e.kind == "final")
    finally:
        await end(incoming, task)


def test_legacy_interrupt_default_is_still_speech():
    assert Interrupt().scope == "speech"
