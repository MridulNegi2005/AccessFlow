import pytest

from accessflow.contracts import Observation, SessionView, Snapshot
from accessflow.turn_policy import HeuristicTurnPolicy


def observation(text: str, *, final: bool, revision: int = 0) -> Observation:
    return Observation(
        event_id=f"event-{revision}",
        source_id="utterance-1",
        revision=revision,
        modality="text",
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


def test_stale_revision_cannot_complete_a_turn():
    old = observation("Book Tuesday", final=True, revision=1)
    current = observation("Book Wednesday", final=False, revision=2)

    decision = HeuristicTurnPolicy().update(old, view(current))

    assert decision.kind == "continue"
    assert decision.uncertainty == 1.0