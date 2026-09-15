import pytest

from accessflow.contracts import Observation, SessionView, Snapshot
from accessflow.perception import ActivitySummary, ActivityWindow
from accessflow.turn_policy import HeuristicTurnPolicy


def observation(
    text: str,
    *,
    final: bool,
    revision: int = 0,
    modality: str = "text",
) -> Observation:
    return Observation(
        event_id=f"event-{revision}",
        source_id="utterance-1",
        revision=revision,
        modality=modality,
        text=text,
        final=final,
        backend="test",
    )


def view(*items: Observation) -> SessionView:
    return SessionView(
        session_id="session-1",
        state=Snapshot(),
        observations=list(items),
        results=[],
    )


@pytest.mark.parametrize("text", ["Book it", "two two tickets", "My screen keeps flickering"])
def test_fluent_and_repeated_final_speech_completes(text: str):
    item = observation(text, final=True)

    decision = HeuristicTurnPolicy().update(item, view())

    assert decision.kind == "complete"


def test_partial_speech_continues_even_after_a_long_recorded_gap():
    item = observation("My screen keeps flickering", final=False)
    item = item.model_copy(update={"speech_start": 0.0, "speech_end": 8.0})

    decision = HeuristicTurnPolicy().update(item, view())

    assert decision.kind == "continue"


def test_turn_policy_accepts_activity_timing_without_using_pause_as_completion():
    item = observation("Book Wednesday", final=False)
    timing = ActivitySummary(
        windows=(ActivityWindow(0.0, 0.8),),
        active_duration_s=0.8,
        leading_silence_s=0.0,
        trailing_silence_s=0.6,
        pause_detected=True,
    )

    decision = HeuristicTurnPolicy().update(item, view(), timing=timing)

    assert decision.kind == "continue"


def test_activity_pause_does_not_override_final_transcript_completion():
    item = observation("Book Wednesday", final=True)
    timing = ActivitySummary(
        windows=(ActivityWindow(0.0, 0.8),),
        active_duration_s=0.8,
        leading_silence_s=0.0,
        trailing_silence_s=0.6,
        pause_detected=True,
    )

    decision = HeuristicTurnPolicy().update(item, view(), timing=timing)

    assert decision.kind == "complete"


def test_explicit_self_correction_is_held_for_resolution():
    item = observation("Tuesday, actually Wednesday", final=True)

    decision = HeuristicTurnPolicy().update(item, view())

    assert decision.kind == "possible_correction"
    assert decision.uncertainty < 0.2


def test_repeated_word_without_correction_marker_is_not_rewritten():
    item = observation("two two tickets", final=True)

    decision = HeuristicTurnPolicy().update(item, view())

    assert decision.kind == "complete"


def test_backchannel_is_not_planned_as_a_new_request():
    item = observation("mm-hmm", final=True)

    decision = HeuristicTurnPolicy().update(item, view())

    assert decision.kind == "backchannel"


def test_image_captions_cannot_drive_speech_turn_policy():
    policy = HeuristicTurnPolicy()

    for caption in ("Wait, actually use this screen", "okay"):
        item = observation(caption, final=True, modality="image")

        decision = policy.update(item, view())

        assert decision.kind == "continue"
        assert decision.uncertainty == 1.0


def test_stale_revision_cannot_complete_a_turn():
    old = observation("Book Tuesday", final=True, revision=1)
    current = observation("Book Wednesday", final=False, revision=2)

    decision = HeuristicTurnPolicy().update(old, view(current))

    assert decision.kind == "continue"
    assert decision.uncertainty == 1.0
