"""Timing-only summaries for local speech activity experiments."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .audio import ActivityFrame


@dataclass(frozen=True)
class ActivityWindow:
    """A contiguous region containing active audio frames."""

    start_s: float
    end_s: float


@dataclass(frozen=True)
class PauseCandidate:
    """An acoustic gap that may inform endpointing, never a completion decision."""

    start_s: float
    end_s: float
    duration_s: float
    trailing: bool


@dataclass(frozen=True)
class ActivitySummary:
    """Activity facts; pause_detected is not a turn-completion decision."""

    windows: tuple[ActivityWindow, ...]
    active_duration_s: float
    leading_silence_s: float
    trailing_silence_s: float
    pause_detected: bool


def _active_windows(frames: tuple[ActivityFrame, ...]) -> tuple[ActivityWindow, ...]:
    windows: list[ActivityWindow] = []
    for frame in frames:
        if not frame.active:
            continue
        if windows and frame.start_s <= windows[-1].end_s:
            previous = windows[-1]
            windows[-1] = ActivityWindow(previous.start_s, max(previous.end_s, frame.end_s))
        else:
            windows.append(ActivityWindow(frame.start_s, frame.end_s))
    return tuple(windows)


def summarize_activity(
    frames: tuple[ActivityFrame, ...],
    *,
    pause_after_s: float = 0.4,
) -> ActivitySummary:
    """Summarize fixed-window activity without deciding that a turn is complete."""
    if not frames:
        raise ValueError("at least one activity frame is required")
    if (
        isinstance(pause_after_s, bool)
        or not isinstance(pause_after_s, (int, float))
        or not math.isfinite(pause_after_s)
        or pause_after_s < 0
    ):
        raise ValueError("pause_after_s cannot be negative")

    windows = _active_windows(frames)
    recording_start = frames[0].start_s
    recording_end = frames[-1].end_s
    if not windows:
        duration = recording_end - recording_start
        return ActivitySummary(
            windows=(),
            active_duration_s=0.0,
            leading_silence_s=duration,
            trailing_silence_s=duration,
            pause_detected=False,
        )

    first = windows[0]
    last = windows[-1]
    active_duration_s = sum(window.end_s - window.start_s for window in windows)
    trailing_silence_s = max(0.0, recording_end - last.end_s)
    return ActivitySummary(
        windows=windows,
        active_duration_s=active_duration_s,
        leading_silence_s=max(0.0, first.start_s - recording_start),
        trailing_silence_s=trailing_silence_s,
        pause_detected=trailing_silence_s >= pause_after_s,
    )


def pause_candidates(
    frames: tuple[ActivityFrame, ...],
    *,
    min_pause_s: float = 0.4,
) -> tuple[PauseCandidate, ...]:
    """Return long acoustic gaps, labeled internal or trailing.

    Consumers must combine these candidates with transcript revisions and policy
    before deciding whether an utterance ended.
    """
    if not frames:
        raise ValueError("at least one activity frame is required")
    if (
        isinstance(min_pause_s, bool)
        or not isinstance(min_pause_s, (int, float))
        or not math.isfinite(min_pause_s)
        or min_pause_s < 0
    ):
        raise ValueError("min_pause_s cannot be negative")

    summary = summarize_activity(frames, pause_after_s=min_pause_s)
    if not summary.windows:
        return ()

    candidates: list[PauseCandidate] = []
    for left, right in zip(summary.windows, summary.windows[1:]):
        duration = max(0.0, right.start_s - left.end_s)
        if duration >= min_pause_s:
            candidates.append(PauseCandidate(left.end_s, right.start_s, duration, trailing=False))
    if summary.trailing_silence_s >= min_pause_s:
        last = summary.windows[-1]
        candidates.append(
            PauseCandidate(last.end_s, last.end_s + summary.trailing_silence_s, summary.trailing_silence_s, trailing=True)
        )
    return tuple(candidates)
