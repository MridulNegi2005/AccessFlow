"""User control holds block model continuations, not just frontend playback."""
import asyncio

import pytest

from accessflow.stop_control import stop_control
from accessflow.turn_policy import HeuristicTurnPolicy
from accessflow.contracts import Audio, AudioEvent, PlanProposal, SpeechStatus, SpeechStatusEvent
from tests.engine.test_pending_frame import setup
from tests.engine.test_output_interrupt import task_context
from test_safety import end, transcript, wait_for


@pytest.mark.parametrize("phrase", ["Stop", "Wait!", "Stop right there", "Cancel...", "Hold on"])
async def test_vague_control_holds_without_reasoning(phrase):
    agent, incoming, outgoing, task = await setup("write")
    try:
        await incoming.put(transcript(phrase))
        await wait_for(outgoing, lambda e: e.kind == "clarify")
        assert agent.stop_hold
        assert not agent.reasoner.views
        assert not agent.ledger
        await incoming.put(transcript("yes", utterance="ambiguous-answer"))
        await wait_for(outgoing, lambda e: e.kind == "clarify")
        assert agent.stop_hold and not agent.reasoner.views
    finally:
        await end(incoming, task)


async def test_spoken_output_stop_preserves_pending_authorized_write():
    agent, incoming, outgoing, task = await setup("write")
    agent.executor.gate = asyncio.Event()
    try:
        await incoming.put(transcript("Book Wednesday"))
        await wait_for(outgoing, lambda e: e.kind == "tool_call")
        before = task_context(agent)
        event = transcript("Stop speaking", utterance="control")
        await incoming.put(event)
        await wait_for(outgoing, lambda e: e.payload.get("output_only"))
        assert task_context(agent) == before
        assert not agent.executor.cancelled
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


async def test_policy_recognized_long_output_stop_never_reaches_planner():
    agent, incoming, outgoing, task = await setup("write")
    agent.turn_policy = HeuristicTurnPolicy()
    try:
        await incoming.put(transcript("Stop speaking while I think"))
        await wait_for(outgoing, lambda e: e.payload.get("output_only"))
        assert not agent.reasoner.views
        assert not agent.ledger
        assert not any("Stop speaking" in item.text for item in agent.observations.values())
    finally:
        await end(incoming, task)


async def test_late_read_result_cannot_restart_planner_while_held():
    agent, incoming, outgoing, task = await setup("read")
    agent.executor.gate = asyncio.Event()
    try:
        await incoming.put(transcript("Look up Wednesday"))
        await wait_for(outgoing, lambda e: e.kind == "tool_call")
        await incoming.put(transcript("Wait", utterance="control"))
        await wait_for(outgoing, lambda e: e.kind == "clarify")
        views = len(agent.reasoner.views)
        agent.executor.gate.set()
        await wait_for(outgoing, lambda e: e.payload.get("basis") == "tool_evidence")
        assert agent.stop_hold
        assert len(agent.reasoner.views) == views
        await incoming.put(transcript("I meant stop speaking", utterance="resolution"))
        await wait_for(outgoing, lambda e: e.kind == "final")
        assert not agent.stop_hold
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


@pytest.mark.parametrize("text", ['What does "stop" mean?', "Cancel this booking",
                                  "Stop speaking and book Friday", "never stop", "wait for Friday"])
def test_control_boundary_does_not_consume_other_requests(text):
    assert stop_control(text) is None


@pytest.mark.parametrize("phrase,held", [("Stop speaking", False), ("Stop", True)])
async def test_audio_control_resolves_pending_speech_without_losing_current_readiness(phrase, held):
    agent, incoming, outgoing, task = await setup("read")
    agent.executor.gate = asyncio.Event()
    try:
        await incoming.put(transcript("Look up Wednesday"))
        await wait_for(outgoing, lambda e: e.kind == "tool_call")
        original_speech = agent.active_speech
        await incoming.put(SpeechStatusEvent(session_id="s", payload=SpeechStatus(
            utterance_id="spoken-control", revision=0, status="pending")))
        await wait_for(outgoing, lambda e: e.payload.get("stop_output"))
        assert not agent.speech_ready
        agent.perception.overrides["spoken-control"] = {"text": phrase, "revision": 1}
        await incoming.put(AudioEvent(session_id="s", payload=Audio(
            path="scripted.wav", utterance_id="spoken-control", revision=1)))
        await wait_for(outgoing, lambda e: e.kind == "clarify" if held else e.payload.get("output_only"))
        assert agent.stop_hold is held
        assert agent.speech_ready
        assert agent.active_speech == original_speech
        assert not any(o.text == phrase for o in agent.observations.values())
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


async def test_audio_output_stop_preserves_authority_without_replaying_uncertain_write():
    agent, incoming, outgoing, task = await setup("write")
    agent.executor.gate = asyncio.Event()
    agent.executor.ignore_cancel = True
    try:
        await incoming.put(transcript("Book Wednesday"))
        call = await wait_for(outgoing, lambda e: e.kind == "tool_call")
        async with asyncio.timeout(2):
            while not agent.executor.calls:
                await asyncio.sleep(0)
        await incoming.put(SpeechStatusEvent(session_id="s", payload=SpeechStatus(
            utterance_id="control", revision=0, status="pending")))
        await wait_for(outgoing, lambda e: e.payload.get("stop_output"))
        agent.perception.overrides["control"] = {"text": "Stop speaking", "revision": 1}
        await incoming.put(AudioEvent(session_id="s", payload=Audio(
            path="scripted.wav", utterance_id="control", revision=1)))
        await wait_for(outgoing, lambda e: e.payload.get("output_only"))
        assert agent.write_intent_retained and agent.speech_ready
        assert agent.ledger[call.payload["call_id"]].status == "cancelled"
        agent.executor.gate.set()
        await wait_for(outgoing, lambda e: e.payload.get("code") == "effect_committed_after_invalidation")
        assert len(agent.executor.calls) == 1
        assert len(agent.executor.effects) == 1
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


async def test_explicit_task_stop_works_without_semantic_policy():
    agent, incoming, outgoing, task = await setup("write")
    agent.executor.gate = asyncio.Event()
    try:
        await incoming.put(transcript("Book Wednesday"))
        await wait_for(outgoing, lambda e: e.kind == "tool_call")
        await incoming.put(transcript("Cancel this task", utterance="control"))
        await wait_for(outgoing, lambda e: e.payload.get("stop_output"))
        assert agent.state.status == "stopped"
        assert not agent.write_intent_retained
        agent.executor.gate.set()
        assert not agent.executor.effects
    finally:
        agent.executor.gate.set()
        await end(incoming, task)


async def test_explicit_action_resolution_reaches_target_clarification():
    agent, incoming, outgoing, task = await setup()
    planned = []

    async def clarify_target(view, manifests):
        planned.append(view)
        return PlanProposal(request_complete=True, clarification="Which booking should I cancel?")

    agent.reasoner.plan = clarify_target
    try:
        await incoming.put(transcript("Stop"))
        await wait_for(outgoing, lambda e: e.kind == "clarify")
        await incoming.put(transcript("Cancel this booking", utterance="resolution"))
        response = await wait_for(outgoing, lambda e: e.kind == "clarify")
        assert response.payload["text"] == "Which booking should I cancel?"
        assert len(planned) == 1 and not agent.stop_hold
        assert not agent.ledger
    finally:
        await end(incoming, task)
