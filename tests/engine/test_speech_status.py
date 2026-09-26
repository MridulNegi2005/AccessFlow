"""Transport activity cannot become an observation, permission, or frame discard."""

import asyncio

import pytest

from accessflow.contracts import Audio, AudioEvent, SpeechStatus, SpeechStatusEvent, PlanProposal
from accessflow.engine import WorkerMessage
from tests.engine.test_pending_frame import setup, frame
from test_safety import end, wait_for, transcript


def status(utterance="pending-audio", revision=0, failed=False):
    return SpeechStatusEvent(session_id="s", payload=SpeechStatus(
        utterance_id=utterance, revision=revision, status="failed" if failed else "pending"))


async def accepted(queue, event):
    return await wait_for(queue, lambda item: item.payload.get("caused_by_event_id") == event.event_id
                          and item.kind in {"acknowledge", "clarify"})


@pytest.mark.parametrize("kind", ["final", "write", "clarify"])
async def test_pending_transport_keeps_frame_without_final_write_or_clarification(kind):
    agent, iq, oq, task = await setup(kind)
    image = frame()
    activity = status()
    if kind == "clarify":
        async def clarify(view, manifests):
            return PlanProposal(request_complete=True, clarification="Which device?")
        agent.reasoner.plan = clarify
    try:
        await iq.put(image)
        await asyncio.wait_for(agent.perception.started.get(), 2)
        frame_task = agent.perception_workers[("image", "f1")]
        await iq.put(activity)
        acknowledgment = await accepted(oq, activity)
        assert acknowledgment.kind == "acknowledge" and acknowledgment.payload["stop_output"]
        assert not frame_task.cancelled()
        assert not agent.speech_ready and not agent.write_intent_retained
        assert not any(item.event_id == activity.event_id for item in agent._view().observations)
        assert ("speech", activity.payload.utterance_id) not in agent.perception_workers
        agent.perception.release["f1"].set()
        await asyncio.wait_for(agent.applied.get(), 2)
        outputs = list(oq._queue)
        assert not any(item.kind in {"tool_call", "final", "clarify"} for item in outputs)
        assert agent._view().observations[0].text == "image f1"
        assert not agent.latest_complete
        if kind != "clarify":
            # The old ASR interface remains unchanged: an ordinary WAV event with
            # a higher revision can now deliver actual final speech evidence.
            agent.perception.overrides[activity.payload.utterance_id] = {"revision": 1}
            await iq.put(AudioEvent(session_id="s", payload=Audio(path="fixture.wav",
                utterance_id=activity.payload.utterance_id, revision=1)))
            result = await wait_for(oq, lambda item: item.kind == ("tool_call" if kind == "write" else "final"))
            if kind == "final":
                assert "image f1" in result.payload["text"]
    finally:
        await end(iq, task)


async def test_pending_activity_holds_new_writes_and_late_speech_cannot_reopen_turn():
    agent, iq, oq, task = await setup("write")
    agent.executor.gate = asyncio.Event()
    try:
        await iq.put(AudioEvent(session_id="s", payload=Audio(path="fixture.wav", utterance_id="old")))
        call = await wait_for(oq, lambda item: item.kind == "tool_call")
        old = agent.observations[("speech", "old")].model_copy(deep=True)
        activity = status()
        await iq.put(activity)
        await accepted(oq, activity)
        assert call.payload["call_id"] not in agent.executor.cancelled
        assert not agent.speech_ready and agent.write_intent_retained
        assert agent.state.correction_pending
        # Deliberately inject an old observation with the current worker generation.
        # Source identity, rather than cooperative task cancellation, must reject it.
        stale = WorkerMessage("observation", agent.generation, old, agent.perception_epoch)
        await agent.inbox.put(stale)
        async with asyncio.timeout(2):
            while await agent.processed.get() is not stale:
                pass
        assert not agent.speech_ready and not agent.latest_complete
        assert agent.active_speech == activity.payload.utterance_id
    finally:
        await end(iq, task)
        agent.executor.gate.set()


async def test_failed_audio_preserves_image_and_requires_fresh_input_to_finish():
    agent, iq, oq, task = await setup("final")
    activity = status()
    failed = status(revision=1, failed=True)
    try:
        await iq.put(activity)
        await accepted(oq, activity)
        await iq.put(frame())
        await asyncio.wait_for(agent.perception.started.get(), 2)
        await iq.put(failed)
        clarification = await accepted(oq, failed)
        assert clarification.kind == "clarify"
        agent.perception.release["f1"].set()
        await asyncio.wait_for(agent.applied.get(), 2)
        assert not any(item.kind == "final" for item in list(oq._queue))
        assert not agent.latest_complete
        await iq.put(transcript("Please describe this device", utterance="recovery"))
        final = await wait_for(oq, lambda item: item.kind == "final")
        assert "image f1" in final.payload["text"]
    finally:
        await end(iq, task)


async def test_old_pending_revision_cannot_reopen_completed_audio():
    agent, iq, oq, task = await setup("final")
    activity = status()
    try:
        await iq.put(activity)
        await accepted(oq, activity)
        agent.perception.overrides[activity.payload.utterance_id] = {"revision": 1}
        await iq.put(AudioEvent(session_id="s", payload=Audio(path="fixture.wav",
            utterance_id=activity.payload.utterance_id, revision=1)))
        await wait_for(oq, lambda item: item.kind == "final")
        speech_ready = agent.speech_ready
        duplicate = status()
        await iq.put(duplicate)
        # A following accepted status supplies a deterministic dispatcher fence.
        fresh = status("different-turn")
        await iq.put(fresh)
        seen = []
        while True:
            event = await asyncio.wait_for(oq.get(), 2)
            seen.append(event)
            if event.payload.get("caused_by_event_id") == fresh.event_id:
                break
        assert speech_ready
        assert not any(item.payload.get("caused_by_event_id") == duplicate.event_id for item in seen)
    finally:
        await end(iq, task)
