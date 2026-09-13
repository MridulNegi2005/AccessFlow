"""Real B adapters/policy and A controller; injected models are explicit test doubles."""
import asyncio
import struct
import zlib
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from accessflow.contracts import Audio, AudioEvent, Frame, FrameEvent, PlanProposal, Start, StartEvent
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, MockOnlyAuthorization, ScriptedReasoner
from accessflow.perception import LocalPerception
from accessflow.turn_policy import HeuristicTurnPolicy
from test_safety import end, manifest, proposal, transcript, wait_for


@asynccontextmanager
async def components(plans, perception=None):
    applied = asyncio.Queue()

    class ObservedAgent(Agent):
        async def _apply(self, plan, source=None):
            await super()._apply(plan, source)
            await applied.put(plan)

    executor = FakeTools()
    agent = ObservedAgent(perception or LocalPerception(), HeuristicTurnPolicy(), ScriptedReasoner(plans),
                          executor, MockOnlyAuthorization(), partial_debounce_s=0)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id="s", payload=Start(tools=[manifest()])))
    try:
        yield agent, incoming, outgoing, applied
    finally:
        await end(incoming, runner)


def png(path):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\xff")) + chunk(b"IEND", b""))
    return FrameEvent(session_id="s", payload=Frame(path=str(path), frame_id="device-frame"))


async def test_completed_correction_can_be_resolved_without_changing_b_policy():
    async with components([PlanProposal(slot_updates={"day": "Tuesday"}), proposal()]) as (agent, iq, oq, applied):
        await iq.put(transcript("Book Tues", final=False))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.effects
        await iq.put(transcript("Actually Wednesday", revision=1))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        assert final.state.slots["day"].confirmed
        assert len(agent.executor.effects) == 1


async def test_unresolved_final_correction_can_ask_without_authorizing_write():
    async with components([PlanProposal(clarification="Which day do you want?")]) as (agent, iq, oq, _):
        await iq.put(transcript("Actually, maybe another day"))
        question = await wait_for(oq, lambda event: event.kind == "clarify")
        assert question.state.correction_pending
        assert not agent.executor.effects


@pytest.mark.parametrize("text", ["Book Wednesday", "Actually Wednesday"])
async def test_contradictory_clarification_and_write_proposal_cannot_execute(text):
    plan = proposal().model_copy(update={"clarification": "Which day do you want?"})
    async with components([plan]) as (agent, iq, oq, applied):
        await iq.put(transcript(text))
        await asyncio.wait_for(applied.get(), 1)
        await wait_for(oq, lambda event: event.kind == "clarify")
        assert not agent.executor.calls and not agent.state.pending_call_ids
        if "Actually" in text:
            assert agent.state.correction_pending


async def test_raw_wav_route_resolves_correction_with_explicit_injected_asr():
    tone = Path(__file__).resolve().parents[1] / "fixtures/audio/synthetic_tone.wav"
    perception = LocalPerception(transcriber=lambda path: "Actually Wednesday")
    async with components([proposal()], perception) as (agent, iq, oq, _):
        await iq.put(AudioEvent(session_id="s", event_id="audio-correction", payload=Audio(
            path=str(tone), utterance_id="u-audio", revision=2, speech_start=1, speech_end=1.5)))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        observation = next(iter(agent.observations.values()))
        assert observation.modality == "audio" and observation.backend == "local/injected-asr"
        assert observation.revision == 2 and observation.event_id == "audio-correction"


async def test_image_only_input_can_produce_informational_response(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Blue test pixel")
    async with components([PlanProposal(response="I see a blue pixel.")], perception) as (_, iq, oq, __):
        await iq.put(png(tmp_path / "pixel.png"))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.payload["basis"] == "informational"


async def test_image_only_input_cannot_supply_write_authorization(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Book Wednesday")
    async with components([proposal()], perception) as (agent, iq, _, applied):
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.effects and not agent.executor.calls


async def test_partial_speech_still_blocks_write_when_final_image_arrives(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Blue test device")
    async with components([PlanProposal(), proposal()], perception) as (agent, iq, _, applied):
        await iq.put(transcript("Book, actually", final=False))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert agent.state.correction_pending
        assert not agent.executor.effects and not agent.executor.calls


async def test_image_plan_cannot_resolve_an_unfinished_final_speech_correction(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Wednesday appointment")
    async with components([PlanProposal(), proposal()], perception) as (agent, iq, _, applied):
        await iq.put(transcript("Actually Tuesday"))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert agent.state.correction_pending
        assert not agent.executor.calls


async def test_image_cannot_inherit_write_request_from_informational_speech(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Wednesday appointment")
    async with components([PlanProposal(response="Hello."), proposal()], perception) as (agent, iq, _, applied):
        await iq.put(transcript("Hello there"))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls


async def test_image_can_complete_an_existing_spoken_write_request(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Wednesday appointment")
    plans = [PlanProposal(intent="service", write_requested=True), proposal()]
    async with components(plans, perception) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls
        await iq.put(png(tmp_path / "pixel.png"))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        assert len(agent.executor.effects) == 1


async def test_image_does_not_reuse_permission_after_a_committed_request(tmp_path):
    perception = LocalPerception(vision_provider=lambda path: "Friday appointment")
    async with components([proposal(), proposal("Friday")], perception) as (agent, iq, oq, applied):
        await iq.put(transcript("Book Wednesday"))
        await asyncio.wait_for(applied.get(), 1)
        await wait_for(oq, lambda event: event.kind == "final")
        assert len(agent.executor.effects) == 1
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert len(agent.executor.calls) == 1
