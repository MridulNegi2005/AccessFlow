"""Conformance examples for the jointly owned D1 stop decision boundary."""

import asyncio

import pytest

from accessflow.contracts import EndEvent, PlanProposal, Start, StartEvent, Transcript, TranscriptEvent
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, MockOnlyAuthorization
from accessflow.turn_policy import HeuristicTurnPolicy


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="D1 hold/clarify needs Mridul's additive TurnDecision and controller handling",
)
async def test_vague_stop_holds_and_clarifies_without_a_final():
    class Reasoner:
        async def plan(self, view, manifests):
            return PlanProposal(response="Planner would finish this task", request_complete=True)

    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    agent = Agent(
        FakePerception(), HeuristicTurnPolicy(), Reasoner(),
        FakeTools(), MockOnlyAuthorization(), partial_debounce_s=0,
    )
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id="vague-stop", payload=Start()))
        await incoming.put(
            TranscriptEvent(
                session_id="vague-stop",
                event_id="stop-speech",
                payload=Transcript(utterance_id="stop-turn", revision=0, text="Stop", final=True),
            )
        )
        seen = []
        while not any(event.kind in {"final", "clarify"} for event in seen):
            seen.append(await asyncio.wait_for(outgoing.get(), timeout=2))
        assert any(event.payload.get("stop_output") is True for event in seen)
        assert seen[-1].kind == "clarify"
        assert not any(event.kind == "tool_call" for event in seen)
        assert agent.state.status != "stopped"
    finally:
        await incoming.put(EndEvent(session_id="vague-stop"))
        await asyncio.wait_for(runner, timeout=2)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="D1 output-only stop needs Mridul's additive TurnDecision and controller handling",
)
async def test_stop_speaking_emits_output_stop_without_stopping_task():
    class Reasoner:
        async def plan(self, view, manifests):
            return PlanProposal(response="This should not be spoken", request_complete=True)

    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    agent = Agent(
        FakePerception(), HeuristicTurnPolicy(), Reasoner(),
        FakeTools(), MockOnlyAuthorization(), partial_debounce_s=0,
    )
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id="output-stop", payload=Start()))
        await incoming.put(
            TranscriptEvent(
                session_id="output-stop",
                event_id="stop-output-speech",
                payload=Transcript(utterance_id="stop-output-turn", revision=0, text="Stop speaking", final=True),
            )
        )
        output = await asyncio.wait_for(outgoing.get(), timeout=2)
        assert output.kind == "acknowledge"
        assert output.payload.get("stop_output") is True
        assert output.payload.get("caused_by_event_id") == "stop-output-speech"
        assert agent.state.status != "stopped"
    finally:
        await incoming.put(EndEvent(session_id="output-stop"))
        await asyncio.wait_for(runner, timeout=2)
