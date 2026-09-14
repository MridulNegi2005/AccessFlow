"""Perception adapters for text, audio and image input."""

from .timing import ActivitySummary, ActivityWindow, PauseCandidate, pause_candidates, summarize_activity
from .audio import ActivityFrame, AudioBuffer, energy_activity, load_pcm
from .vad import webrtc_activity
from .local import LocalPerception, PngFormat, WavFormat, validate_png, validate_wav
from .vision import OllamaVisionProvider

__all__ = [
    "ActivitySummary",
    "ActivityWindow",
    "PauseCandidate",
    "ActivityFrame",
    "AudioBuffer",
    "LocalPerception",
    "OllamaVisionProvider",
    "PngFormat",
    "WavFormat",
    "energy_activity",
    "load_pcm",
    "pause_candidates",
    "summarize_activity",
    "validate_png",
    "validate_wav",
    "webrtc_activity",
]
