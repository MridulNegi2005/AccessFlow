"""Perception adapters for text, audio and image input."""

from .timing import ActivitySummary, ActivityWindow, summarize_activity
from .audio import ActivityFrame, AudioBuffer, energy_activity, load_pcm
from .local import LocalPerception, WavFormat, validate_wav

__all__ = [
    "ActivitySummary",
    "ActivityWindow",
    "ActivityFrame",
    "AudioBuffer",
    "LocalPerception",
    "WavFormat",
    "energy_activity",
    "load_pcm",
    "summarize_activity",
    "validate_wav",
]