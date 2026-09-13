"""Timing-only summaries for local speech activity experiments."""

from __future__ import annotations

from dataclasses import dataclass

from .audio import ActivityFrame


@dataclass(frozen=True)
class ActivityWindow:
    """A contiguous region containing active audio frames."""

    start_s: float
    end_s: float


@dataclass(frozen=True)
class ActivitySummary:
    """Activity facts; pause_detected is not a turn-completion decision."""

    windows: tuple[ActivityWindow, ...]
    active_duration_s: float
    leading_silence_s: float
    trailing_silence_s: float
    pause_detected: bool


def summarize_activity(
    frames: tuple[ActivityFrame, ...],
    *,
    pause_after_s: float = 0.4,
) -> ActivitySummary:
    """Summarize fixed-window activity without deciding that a turn is complete."""
    if not frames:
        raise ValueError("at least one activity frame is required")
    if pause_after_s < 0:
        raise ValueError("pause_after_s cannot be negative")

    windows: list[ActivityWindow] = []
    for frame in frames:
        if not frame.active:
            continue
        if windows and frame.start_s <= windows[-1].end_s:
            previous = windows[-1]
            windows[-1] = ActivityWindow(previous.start_s, max(previous.end_s, frame.end_s))
        else:
            windows.append(ActivityWindow(frame.start_s, frame.end_s))

    if not windows:
        return ActivitySummary(
            windows=(),
            active_duration_s=0.0,
            leading_silence_s=frames[-1].end_s - frames[0].start_s,
            trailing_silence_s=frames[-1].end_s - frames[0].start_s,
            pause_detected=False,
        )

    first = windows[0]
    last = windows[-1]
    recording_start = frames[0].start_s
    recording_end = frames[-1].end_s
    active_duration_s = sum(window.end_s - window.start_s for window in windows)
    trailing_silence_s = max(0.0, recording_end - last.end_s)
    return ActivitySummary(
        windows=tuple(windows),
        active_duration_s=active_duration_s,
        leading_silence_s=max(0.0, first.start_s - recording_start),
        trailing_silence_s=trailing_silence_s,
        pause_detected=trailing_silence_s >= pause_after_s,
    )
