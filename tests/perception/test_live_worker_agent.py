"""Opt-in real ASR worker/Agent seam; fixture and reasoner are not real users or tools."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from accessflow.adapters.process_perception import ProcessPerception
from accessflow.contracts import Audio, AudioEvent, EndEvent, PlanProposal, Start, StartEvent
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, MockOnlyAuthorization
from accessflow.turn_policy import HeuristicTurnPolicy


FIXTURE = Path(__file__).parents[1] / "fixtures" / "audio" / "held_out" / "heldout_repetition.wav"


class _RecordingMockReasoner:
    def __init__(self) -> None:
        self.views = []

    async def plan(self, view, manifests):
        self.views.append(view.model_copy(deep=True))
        return PlanProposal(response="Mock informational acknowledgment.", request_complete=True)


@pytest.mark.asyncio
async def test_installed_asr_worker_reaches_actual_agent_without_tool_effects():
    model_path = os.environ.get("ACCESSFLOW_TEST_WHISPER_MODEL_PATH")
    if not model_path:
        pytest.skip("Set ACCESSFLOW_TEST_WHISPER_MODEL_PATH for the opt-in local model run")
    model = Path(model_path)
    assert model.is_dir(), "ACCESSFLOW_TEST_WHISPER_MODEL_PATH must be an installed directory"

    perception = ProcessPerception(model_path=model, observation_timeout_s=30.0)
    reasoner = _RecordingMockReasoner()
    executor = FakeTools()
    agent = Agent(perception, HeuristicTurnPolicy(), reasoner, executor, MockOnlyAuthorization())
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(agent.run(incoming, outgoing))
    outputs = []
    try:
        await incoming.put(
            StartEvent(session_id="real-asr-generated-fixture", event_id="start", payload=Start())
        )
        await incoming.put(
            AudioEvent(
                session_id="real-asr-generated-fixture",
                event_id="audio-request",
                payload=Audio(path=str(FIXTURE), utterance_id="generated-repetition"),
            )
        )
        async with asyncio.timeout(30):
            while True:
                output = await outgoing.get()
                outputs.append(output)
                if output.kind in ("final", "error"):
                    break
    finally:
        await incoming.put(EndEvent(session_id="real-asr-generated-fixture", event_id="end"))
        try:
            await asyncio.wait_for(task, 5)
        finally:
            await perception.aclose()

    assert outputs[-1].kind == "final"
    assert any(output.kind == "acknowledge" for output in outputs)
    assert outputs[-1].payload["caused_by_event_id"] == "audio-request"
    assert next(output for output in outputs if output.kind == "acknowledge").payload[
        "caused_by_event_id"
    ] == "audio-request"
    assert len(reasoner.views) == 1
    observation = reasoner.views[0].observations[-1]
    assert observation.event_id == "audio-request"
    assert observation.source_id == "generated-repetition"
    assert observation.modality == "audio"
    assert observation.backend == "faster-whisper/cpu-int8"
    assert observation.text.lower().count("tuesday") == 2
    assert "wednesday" in observation.text.lower()
    assert not executor.calls
    assert not executor.effects
    assert not perception.child_alive
