"""Offline endpoint-candidate replay for calibrated speech timing experiments.

This module reports acoustic endpoint candidates only.  It deliberately does not
construct a :class:`TurnDecision`, change controller readiness, authorize a
tool, or mutate a session.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from ..perception.audio import ActivityFrame
from ..perception.timing import PauseCandidate, pause_candidates


def _validate_time(value: float, field_name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field_name} must be a finite non-negative number")


@dataclass(frozen=True)
class TranscriptRevision:
    """A timestamped transcript state used by the offline replay."""

    source_id: str
    revision: int
    final: bool
    available_at_s: float
    speech_end_s: float

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ValueError("revision must be a non-negative integer")
        if not isinstance(self.final, bool):
            raise ValueError("final must be a boolean")
        _validate_time(self.available_at_s, "available_at_s")
        _validate_time(self.speech_end_s, "speech_end_s")


@dataclass(frozen=True)
class EndpointMeasurement:
    """One accepted acoustic candidate and its wait after labeled speech end."""

    source_id: str
    revision: int | None
    pause_start_s: float
    pause_end_s: float
    pause_duration_s: float
    trailing: bool
    fired_at_s: float
    speech_end_s: float | None
    wait_after_speech_end_s: float | None


@dataclass(frozen=True)
class TimingReplayReport:
    """Measurement output from one threshold and transcript-gating policy."""

    source_id: str
    min_pause_s: float
    require_final: bool
    candidates: tuple[EndpointMeasurement, ...]
    premature_candidates: tuple[PauseCandidate, ...]
    missed_final_count: int
    added_wait_after_speech_end_s: float | None


def _latest_revision_available(
    revisions: tuple[TranscriptRevision, ...], source_id: str, available_by_s: float
) -> TranscriptRevision | None:
    matching = [
        revision
        for revision in revisions
        if revision.source_id == source_id and revision.available_at_s <= available_by_s
    ]
    if not matching:
        return None
    return max(matching, key=lambda revision: revision.revision)


def _latest_revision(
    revisions: tuple[TranscriptRevision, ...], source_id: str
) -> TranscriptRevision | None:
    matching = [revision for revision in revisions if revision.source_id == source_id]
    if not matching:
        return None
    return max(matching, key=lambda revision: revision.revision)


def replay_endpoint_candidates(
    frames: tuple[ActivityFrame, ...],
    revisions: Iterable[TranscriptRevision],
    *,
    source_id: str,
    min_pause_s: float = 0.4,
    require_final: bool = True,
) -> TimingReplayReport:
    """Replay acoustic pauses against transcript revisions without completing a turn.

    A candidate is eligible for a gated replay only when the latest revision for
    ``source_id`` available by the end of that pause is final and reports a speech
    end at or before the pause.  Older revisions and revisions for another source
    cannot authorize a candidate.  An ungated replay is the acoustic baseline and
    accepts every pause returned by :func:`pause_candidates`.
    """
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be a non-empty string")
    if not isinstance(require_final, bool):
        raise ValueError("require_final must be a boolean")

    revision_values = tuple(revisions)
    if any(not isinstance(revision, TranscriptRevision) for revision in revision_values):
        raise ValueError("revisions must contain TranscriptRevision values")
    seen: set[tuple[str, int]] = set()
    for revision in revision_values:
        key = (revision.source_id, revision.revision)
        if key in seen:
            raise ValueError("transcript revisions must be unique")
        seen.add(key)

    pauses = pause_candidates(frames, min_pause_s=min_pause_s)
    latest_overall = _latest_revision(revision_values, source_id)
    accepted: list[EndpointMeasurement] = []
    premature: list[PauseCandidate] = []
    matched_final = False

    for pause in pauses:
        latest = _latest_revision_available(revision_values, source_id, pause.end_s)
        gated = (
            latest is not None
            and latest.final
            and latest.available_at_s <= pause.end_s
            and latest.speech_end_s <= pause.start_s
        )
        if require_final and not gated:
            continue

        speech_end = latest.speech_end_s if latest is not None else None
        wait = None
        if speech_end is not None and pause.start_s >= speech_end:
            matched_final = True
            wait = max(0.0, pause.end_s - speech_end)
        if not pause.trailing:
            premature.append(pause)
        accepted.append(
            EndpointMeasurement(
                source_id=source_id,
                revision=latest.revision if latest is not None else None,
                pause_start_s=pause.start_s,
                pause_end_s=pause.end_s,
                pause_duration_s=pause.duration_s,
                trailing=pause.trailing,
                fired_at_s=pause.end_s,
                speech_end_s=speech_end,
                wait_after_speech_end_s=wait,
            )
        )

    return TimingReplayReport(
        source_id=source_id,
        min_pause_s=min_pause_s,
        require_final=require_final,
        candidates=tuple(accepted),
        premature_candidates=tuple(premature),
        missed_final_count=int(
            latest_overall is not None and latest_overall.final and not matched_final
        ),
        added_wait_after_speech_end_s=(
            next(
                measurement.wait_after_speech_end_s
                for measurement in accepted
                if measurement.wait_after_speech_end_s is not None
            )
            if matched_final
            else None
        ),
    )
