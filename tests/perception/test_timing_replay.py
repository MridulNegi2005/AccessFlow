import pytest

from accessflow.perception import ActivityFrame
from accessflow.turn_policy.timing_replay import TranscriptRevision, replay_endpoint_candidates


def _recorded_timeline(
    active_windows: tuple[tuple[float, float], ...], recording_end_s: float
) -> tuple[ActivityFrame, ...]:
    """Compress the recorded 20 ms VAD windows into equivalent activity spans."""
    frames = [ActivityFrame(start, end, 0, True) for start, end in active_windows]
    last_end = active_windows[-1][1] if active_windows else 0.0
    if recording_end_s > last_end:
        frames.append(ActivityFrame(last_end, recording_end_s, 0, False))
    return tuple(frames)


def _heldout_pause_frames() -> tuple[ActivityFrame, ...]:
    return _recorded_timeline(((0.1, 1.88), (3.86, 5.32)), 5.94)


def _heldout_fluent_frames() -> tuple[ActivityFrame, ...]:
    return _recorded_timeline(((0.18, 2.78),), 3.44)


def _heldout_final(source_id: str, speech_end_s: float) -> TranscriptRevision:
    return TranscriptRevision(
        source_id=source_id,
        revision=1,
        final=True,
        available_at_s=speech_end_s,
        speech_end_s=speech_end_s,
    )


def test_short_acoustic_baseline_is_premature_and_long_baseline_misses_end():
    revisions = (_heldout_final("heldout-pause", 5.32),)

    short = replay_endpoint_candidates(
        _heldout_pause_frames(), revisions, source_id="heldout-pause", require_final=False
    )
    long = replay_endpoint_candidates(
        _heldout_pause_frames(),
        revisions,
        source_id="heldout-pause",
        min_pause_s=2.0,
        require_final=False,
    )

    assert len(short.candidates) == 2
    assert len(short.premature_candidates) == 1
    assert short.missed_final_count == 0
    assert short.added_wait_after_speech_end_s == pytest.approx(0.62)
    assert long.candidates == ()
    assert long.premature_candidates == ()
    assert long.missed_final_count == 1


def test_long_baseline_misses_fluent_endpoint_while_short_baseline_has_bounded_wait():
    revisions = (_heldout_final("heldout-fluent", 2.78),)

    short = replay_endpoint_candidates(
        _heldout_fluent_frames(), revisions, source_id="heldout-fluent", require_final=False
    )
    long = replay_endpoint_candidates(
        _heldout_fluent_frames(),
        revisions,
        source_id="heldout-fluent",
        min_pause_s=2.0,
        require_final=False,
    )

    assert len(short.candidates) == 1
    assert short.candidates[0].trailing is True
    assert short.missed_final_count == 0
    assert short.added_wait_after_speech_end_s == pytest.approx(0.66)
    assert long.candidates == ()
    assert long.missed_final_count == 1


def test_combined_replay_waits_for_final_revision_before_emitting_candidate():
    frames = (
        ActivityFrame(0.0, 1.0, 0, True),
        ActivityFrame(1.0, 1.8, 0, False),
        ActivityFrame(1.8, 2.4, 0, True),
        ActivityFrame(2.4, 3.0, 0, False),
    )
    revisions = (
        TranscriptRevision("utterance-1", 0, False, 0.9, 1.0),
        TranscriptRevision("utterance-1", 1, True, 2.0, 2.4),
    )

    report = replay_endpoint_candidates(
        frames, revisions, source_id="utterance-1", require_final=True
    )

    assert len(report.candidates) == 1
    assert report.candidates[0].trailing is True
    assert report.candidates[0].revision == 1
    assert report.candidates[0].fired_at_s == pytest.approx(3.0)
    assert report.premature_candidates == ()
    assert report.missed_final_count == 0
    assert report.added_wait_after_speech_end_s == pytest.approx(0.6)


def test_replay_uses_revision_available_at_each_pause():
    frames = _heldout_pause_frames()
    revisions = (
        TranscriptRevision("utterance-1", 1, True, 1.9, 1.88),
        TranscriptRevision("utterance-1", 2, False, 4.0, 5.32),
    )

    report = replay_endpoint_candidates(
        frames, revisions, source_id="utterance-1", require_final=True
    )

    assert len(report.candidates) == 1
    assert report.candidates[0].revision == 1
    assert report.candidates[0].pause_start_s == pytest.approx(1.88)
    assert report.candidates[0].pause_end_s == pytest.approx(3.86)
    assert report.missed_final_count == 0


def test_stale_or_mismatched_revisions_cannot_gate_a_candidate():
    frames = _heldout_pause_frames()
    stale = (
        TranscriptRevision("utterance-1", 0, True, 0.0, 1.88),
        TranscriptRevision("utterance-1", 1, False, 2.0, 5.32),
    )
    mismatched = (_heldout_final("other-utterance", 5.32),)

    stale_report = replay_endpoint_candidates(
        frames, stale, source_id="utterance-1", require_final=True
    )
    mismatched_report = replay_endpoint_candidates(
        frames, mismatched, source_id="utterance-1", require_final=True
    )

    assert stale_report.candidates == ()
    assert stale_report.missed_final_count == 0
    assert mismatched_report.candidates == ()
    assert mismatched_report.missed_final_count == 0


def test_all_silence_never_emits_an_endpoint_candidate():
    frames = (
        ActivityFrame(0.0, 0.4, 0, False),
        ActivityFrame(0.4, 1.0, 0, False),
    )

    report = replay_endpoint_candidates(
        frames,
        (_heldout_final("silence", 0.0),),
        source_id="silence",
        require_final=False,
    )

    assert report.candidates == ()
    assert report.premature_candidates == ()


def test_replay_rejects_duplicate_revision_identity():
    revision = _heldout_final("duplicate", 1.0)

    with pytest.raises(ValueError, match="revisions must be unique"):
        replay_endpoint_candidates(
            _heldout_fluent_frames(),
            (revision, revision),
            source_id="duplicate",
        )


def test_partial_revision_cannot_count_as_matched_final_in_acoustic_baseline():
    frames = (
        ActivityFrame(0.0, 1.0, 0, True),
        ActivityFrame(1.0, 1.8, 0, False),
        ActivityFrame(1.8, 2.4, 0, True),
        ActivityFrame(2.4, 3.0, 0, False),
    )
    revisions = (
        TranscriptRevision("utterance-1", 0, False, 1.0, 1.0),
        TranscriptRevision("utterance-1", 1, True, 3.2, 2.4),
    )

    report = replay_endpoint_candidates(
        frames, revisions, source_id="utterance-1", require_final=False
    )

    assert len(report.candidates) == 2  # Acoustic candidates remain visible.
    assert all(candidate.revision == 0 for candidate in report.candidates)
    assert all(candidate.wait_after_speech_end_s is None for candidate in report.candidates)
    assert report.missed_final_count == 1
    assert report.added_wait_after_speech_end_s is None
