"""FDB room routing tests use the real controller without network or a microphone."""

import asyncio
import json

import pytest

from accessflow.contracts import EndEvent, OutputEvent, PlanProposal, Snapshot, TranscriptEvent
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FinalFlagPolicy, ScriptedReasoner
from accessflow.perception.fdb_v3.bridge import RoomBridge, spoken_results, tts_safe_text


async def test_room_routes_two_distinct_final_turns_and_closes_cleanly():
    reasoner = ScriptedReasoner([
        PlanProposal(response="First answer.", request_complete=True),
        PlanProposal(response="Second answer.", request_complete=True),
    ])
    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), reasoner))
    await bridge.start()
    try:
        await bridge.begin_speech()
        assert await bridge.complete_turn("first question", timeout=5) == "First answer."
        await bridge.begin_speech()
        assert await bridge.complete_turn("second question", timeout=5) == "Second answer."
        assert len(reasoner.views) == 2
        assert reasoner.views[0].observations[-1].text == "first question"
        assert reasoner.views[1].observations[-1].text == "second question"
    finally:
        await bridge.close()


async def test_new_speech_cancels_waiting_reply():
    class SlowReasoner:
        async def plan(self, view, manifests):
            await asyncio.sleep(0.3)
            return PlanProposal(response=view.observations[-1].text, request_complete=True)

    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), SlowReasoner()))
    await bridge.start()
    try:
        first = asyncio.create_task(bridge.complete_turn("outdated", timeout=5))
        await asyncio.sleep(0.02)
        await bridge.begin_speech()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await bridge.complete_turn("corrected", timeout=5) == "corrected"
    finally:
        await bridge.close()


def test_long_spoken_reply_splits_into_provider_sized_sentences():
    text = "A detailed result with verified fields and a long explanation. " * 8
    spoken = tts_safe_text(text)
    assert all(len(sentence) <= 200 for sentence in spoken.split(". "))
    assert spoken.startswith("A detailed result")


def test_parallel_result_speech_uses_each_confirmed_tool_output():
    spoken = spoken_results([
        ("get_exchange_rate", {"status": "success", "converted_amount": 900.0, "rate": 0.9}),
        ("modify_autopay", {"status": "success", "autopay_enabled": True, "source": "savings"}),
        ("get_card_benefits", {"status": "success", "card_type": "premium",
                               "benefits": ["Cashback", "No fee"]}),
    ])
    assert "Conversion: 900.0 at rate 0.9" in spoken
    assert "Autopay now uses savings" in spoken
    assert "Cashback, No fee" in spoken
    assert "status" not in spoken


async def test_schema_rejection_is_not_spoken_before_controller_recovery():
    class RecoveringReasoner:
        def __init__(self):
            self.attempts = 0

        async def plan(self, view, manifests):
            self.attempts += 1
            if self.attempts == 1:
                raise json.JSONDecodeError("invalid first proposal", "{", 0)
            return PlanProposal(response="Recovered answer.", request_complete=True)

    reasoner = RecoveringReasoner()
    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), reasoner))
    await bridge.start()
    try:
        assert await bridge.complete_turn("question", timeout=5) == "Recovered answer."
        assert reasoner.attempts == 2
    finally:
        await bridge.close()


# ---------------------------------------------------------------------------
# B1 regression: control-terminal acknowledge events must resolve complete_turn
# ---------------------------------------------------------------------------

async def test_output_only_stop_resolves_silently_without_timeout():
    """B1: 'Stop speaking' must complete immediately with an empty reply, not hang."""
    bridge = RoomBridge(
        "control-probe",
        Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner()),
    )
    await bridge.start()
    try:
        await bridge.begin_speech()
        result = await bridge.complete_turn("Stop speaking", timeout=2)
        # Output-only stop must be silent: no generic "Done." invented.
        assert result == ""
    finally:
        await bridge.close()


async def test_task_cancel_resolves_with_stopped_text_without_timeout():
    """B1: 'Cancel this task' must complete immediately, not hang for 90 seconds."""
    bridge = RoomBridge(
        "control-probe",
        Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner()),
    )
    await bridge.start()
    try:
        await bridge.begin_speech()
        result = await bridge.complete_turn("Cancel this task", timeout=2)
        # Controller emits the completed task-stop acknowledgment.
        assert result == "Stopped."
    finally:
        await bridge.close()


async def test_vague_stop_resolves_via_clarify_without_timeout():
    """B1: Vague stop correctly asks whether to stop output or cancel -- no timeout."""
    bridge = RoomBridge(
        "control-probe",
        Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner()),
    )
    await bridge.start()
    try:
        await bridge.begin_speech()
        result = await bridge.complete_turn("Stop right there", timeout=2)
        # Controller emits a clarify asking output vs cancel.
        assert "stop" in result.lower() or "cancel" in result.lower()
    finally:
        await bridge.close()


async def test_ordinary_acknowledgment_does_not_complete_turn_prematurely():
    """A correlated progress acknowledgment must not resolve the pending future."""
    class ProgressThenFinalController:
        def __init__(self):
            self.progress_sent = asyncio.Event()
            self.allow_final = asyncio.Event()

        async def run(self, inputs, outputs):
            await inputs.get()  # StartEvent
            while True:
                event = await inputs.get()
                if isinstance(event, EndEvent):
                    return
                if isinstance(event, TranscriptEvent):
                    await outputs.put(OutputEvent(
                        session_id=event.session_id, kind="acknowledge",
                        payload={"text": "I'm listening.",
                                 "stop_output": True,
                                 "caused_by_event_id": event.event_id},
                        state=Snapshot(),
                    ))
                    self.progress_sent.set()
                    await self.allow_final.wait()
                    await outputs.put(OutputEvent(
                        session_id=event.session_id, kind="final",
                        payload={"text": "Real answer.",
                                 "caused_by_event_id": event.event_id},
                        state=Snapshot(),
                    ))

    controller = ProgressThenFinalController()
    bridge = RoomBridge("ack-probe", controller)
    await bridge.start()
    try:
        waiting = asyncio.create_task(bridge.complete_turn("give me the answer", timeout=2))
        await controller.progress_sent.wait()
        assert not waiting.done()
        controller.allow_final.set()
        result = await waiting
        assert result == "Real answer."
    finally:
        await bridge.close()


async def test_stale_reply_from_old_utterance_does_not_resolve_new_turn():
    """An old event arriving after new speech cannot resolve the new future."""
    class StaleThenCurrentController:
        def __init__(self):
            self.first_transcript = None
            self.first_seen = asyncio.Event()

        async def run(self, inputs, outputs):
            await inputs.get()  # StartEvent
            while True:
                event = await inputs.get()
                if isinstance(event, EndEvent):
                    return
                if isinstance(event, TranscriptEvent):
                    if self.first_transcript is None:
                        self.first_transcript = event
                        self.first_seen.set()
                        continue
                    await outputs.put(OutputEvent(
                        session_id=event.session_id, kind="final",
                        payload={"text": "Old answer.",
                                 "caused_by_event_id": self.first_transcript.event_id},
                        state=Snapshot(),
                    ))
                    await outputs.put(OutputEvent(
                        session_id=event.session_id, kind="final",
                        payload={"text": "New answer.",
                                 "caused_by_event_id": event.event_id},
                        state=Snapshot(),
                    ))

    controller = StaleThenCurrentController()
    bridge = RoomBridge("stale-probe", controller)
    await bridge.start()
    try:
        first = asyncio.create_task(bridge.complete_turn("old question", timeout=2))
        await controller.first_seen.wait()
        await bridge.begin_speech()
        with pytest.raises(asyncio.CancelledError):
            await first
        result = await bridge.complete_turn("new question", timeout=2)
        assert result == "New answer."
    finally:
        await bridge.close()


async def test_room_close_while_awaiting_completion_is_clean():
    """B1: Closing the room while complete_turn is waiting raises CancelledError cleanly."""
    class NeverReasoner:
        def __init__(self):
            self.started = asyncio.Event()

        async def plan(self, view, manifests):
            self.started.set()
            await asyncio.Event().wait()

    reasoner = NeverReasoner()
    bridge = RoomBridge(
        "close-probe",
        Agent(FakePerception(), FinalFlagPolicy(), reasoner),
    )
    await bridge.start()
    waiting = asyncio.create_task(bridge.complete_turn("wait forever", timeout=30))
    await reasoner.started.wait()
    await bridge.close()
    with pytest.raises(asyncio.CancelledError):
        await waiting


async def test_blank_transcript_closes_pending_speech_with_failed_status():
    bridge = RoomBridge("blank-probe", Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner()))
    bridge._runner = asyncio.current_task()
    bridge._utterance_id = "pending-utterance"
    try:
        assert await bridge.complete_turn("  ") == ""
        event = bridge.inputs.get_nowait()
        assert event.payload.status == "failed"
        assert event.payload.utterance_id == "pending-utterance"
    finally:
        bridge._runner = None


async def test_reply_timeout_cancels_future_and_interrupts_speech_request():
    class WaitingController:
        async def run(self, inputs, outputs):
            await inputs.get()  # StartEvent
            while True:
                event = await inputs.get()
                if isinstance(event, EndEvent):
                    return

    bridge = RoomBridge("timeout-probe", WaitingController())
    await bridge.start()
    try:
        with pytest.raises(TimeoutError):
            await bridge.complete_turn("slow request", timeout=0.01)
        event = bridge.inputs.get_nowait()
        assert event.payload.scope == "speech"
    finally:
        await bridge.close()
