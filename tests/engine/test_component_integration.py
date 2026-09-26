"""Real B adapters/policy and A controller; injected models are explicit test doubles."""
import asyncio
import struct
import zlib
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from accessflow.contracts import (
    Audio, AudioEvent, Frame, FrameEvent, ImageSlotBinding, Interrupt, InterruptEvent, Observation, PlanProposal,
    Start, StartEvent, TranscriptEvent,
)
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


@pytest.mark.parametrize("final", [True, False])
async def test_correction_acknowledgment_does_not_wait_for_model_or_authorize_effect(final):
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowReasoner:
        async def plan(self, view, manifests):
            entered.set()
            await release.wait()
            return proposal()

    async with components([]) as (agent, iq, oq, applied):
        agent.reasoner = SlowReasoner()
        await iq.put(transcript("Actually Wednesday", final=final))
        await asyncio.wait_for(entered.wait(), 1)
        assert agent.state.correction_pending
        assert not agent.executor.calls
        if final:
            ack = await wait_for(oq, lambda event: event.kind == "acknowledge")
            assert ack.state.correction_pending
            assert not ack.state.pending_call_ids
        else:
            assert oq.empty()
        release.set()
        await asyncio.wait_for(applied.get(), 1)
        if final:
            await wait_for(oq, lambda event: event.kind == "final")
        else:
            assert not agent.executor.calls


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


async def test_clarify_then_image_completes_the_write(tmp_path):
    """A spoken write request survives a clarifying turn until an image answers it.

    Speech asks for a write and also poses one open question. That completed
    utterance sets `write_intent_retained`, which a clarifying turn on the same
    request does not clear. The image that follows answers the question; it
    never grants write authority itself, but the request can now dispatch
    because authorization already came from the spoken turn.
    """
    perception = LocalPerception(vision_provider=lambda path: "Wednesday appointment")
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"),
             proposal()]
    async with components(plans, perception) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls
        await iq.put(png(tmp_path / "pixel.png"))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert len(agent.executor.effects) == 1


async def test_clarify_then_spoken_answer_completes_the_write():
    """The same retained-intent rule applies when the answer arrives as speech, not an image.

    write_intent_retained is re-derived fresh from the second utterance's own proposal
    (fresh_evidence=True), and that proposal itself carries write_requested=True, so the
    write dispatches once the second utterance completes the request.
    """
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which day works?"),
             proposal()]
    async with components(plans) as (agent, iq, oq, applied):
        await iq.put(transcript("Book an appointment", utterance="u1"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls
        await iq.put(transcript("Wednesday", utterance="u2"))
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        assert len(agent.executor.effects) == 1


async def test_ambiguous_image_asks_again_instead_of_writing(tmp_path):
    """An image that fails to resolve the open question keeps the request clarifying.

    Retained spoken intent is necessary but not sufficient: the write dispatch gate also
    requires the proposal to drop its clarification and clarification_outstanding to clear,
    neither of which happens when the image is unrelated or ambiguous.
    """
    perception = LocalPerception(vision_provider=lambda path: "An indistinct photograph")
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"),
             proposal().model_copy(update={"clarification": "I still cannot tell the date."})]
    async with components(plans, perception) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await wait_for(oq, lambda event: event.kind == "clarify")
        assert not agent.executor.calls
        await iq.put(png(tmp_path / "pixel.png"))
        await wait_for(oq, lambda event: event.kind == "clarify" and
                       event.payload["text"] == "I still cannot tell the date.")
        assert not agent.executor.calls and not agent.executor.effects


async def test_explicit_stop_clears_retained_intent_so_image_cannot_write(tmp_path):
    """An explicit task stop clears write_intent_retained; a later image cannot revive it.

    Unlike a clarifying turn (test_clarify_then_image_completes_the_write), an
    InterruptEvent(scope="task") explicitly clears both write_intent_retained and
    clarification_outstanding, and a subsequent image is not new spoken evidence and so
    cannot set write_intent_retained again.
    """
    perception = LocalPerception(vision_provider=lambda path: "Wednesday appointment")
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"),
             proposal()]
    async with components(plans, perception) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        await wait_for(oq, lambda event: event.kind == "acknowledge" and event.payload["text"] == "Stopped.")
        assert not agent.write_intent_retained
        await iq.put(png(tmp_path / "pixel.png"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls and not agent.executor.effects


async def test_late_older_frame_keeps_its_identity_without_reopening_finished_write(tmp_path):
    """Late Image 1 evidence remains available but cannot change a finished action."""
    stale_gate = asyncio.Event()

    class RacingPerception:
        async def observe(self, event):
            if isinstance(event, TranscriptEvent):
                payload = event.payload
                yield Observation(event_id=event.event_id, source_id=payload.utterance_id,
                                  revision=payload.revision, modality="text", text=payload.text,
                                  final=payload.final, backend="test/text")
                return
            if isinstance(event, FrameEvent):
                if event.payload.frame_id == "stale-frame":
                    await stale_gate.wait()
                    text = "Monday guess"
                else:
                    text = "Wednesday appointment"
                yield Observation(event_id=event.event_id, source_id=event.payload.frame_id,
                                  revision=0, modality="image", text=text, final=True, backend="test/vision")

    older = FrameEvent(session_id="s", payload=Frame(path="stale.png", frame_id="stale-frame"))
    newer = FrameEvent(session_id="s", payload=Frame(path="fresh.png", frame_id="fresh-frame"))
    final_plan = proposal()
    final_plan.image_bindings = {"day": ImageSlotBinding(
        image_reference="Image 2", event_id=newer.event_id,
        processing_revision=0, evidence_quote="Wednesday appointment")}
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"), final_plan]
    async with components(plans, RacingPerception()) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(older)
        await iq.put(newer)
        final = await wait_for(oq, lambda event: event.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        assert len(agent.executor.effects) == 1
        assert agent.active_frame == "fresh-frame"
        assert agent.image_registry.resolve("stale-frame").status == "pending"
        stale_gate.set()
        for _ in range(20):
            await asyncio.sleep(0)
        assert len(agent.executor.effects) == 1
        assert agent.image_registry.resolve("stale-frame").observation.text == "Monday guess"
        assert agent.image_registry.resolve("fresh-frame").observation.text == "Wednesday appointment"
        assert agent.state.slots["day"].value == "Wednesday"


async def test_missing_vision_provider_surfaces_explicit_error_not_silence(tmp_path):
    """A request that cannot be perceived reaches an explicit error, never a silent stall.

    A bare LocalPerception() (no vision_provider) raises inside the perception worker when a
    frame arrives. The worker reports that as an explicit backend_failure error rather than
    leaving the request to hang -- this is the "no-provider" case, distinct from (and not a
    stand-in for) the write-intent deadlock that test_clarify_then_image_completes_the_write
    now covers with a real, deterministic vision provider.
    """
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"),
             proposal()]
    async with components(plans, None) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        await iq.put(png(tmp_path / "pixel.png"))
        error = await wait_for(oq, lambda event: event.kind == "error" and
                               event.payload.get("code") == "backend_failure")
        assert error.payload["detail"] == "RuntimeError"
        assert not agent.executor.effects


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
