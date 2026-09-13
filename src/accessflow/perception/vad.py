"""Optional WebRTC voice-activity detection for local timing experiments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .audio import ActivityFrame, AudioBuffer


def webrtc_activity(
    buffer: AudioBuffer,
    *,
    frame_ms: int = 20,
    aggressiveness: int = 2,
    vad_factory: Callable[[int], Any] | None = None,
) -> tuple[ActivityFrame, ...]:
    """Classify complete PCM frames with WebRTC VAD.

    This produces acoustic activity only. It does not decide whether a transcript
    is complete or whether a tool action is safe.
    """
    if buffer.sample_rate not in (8_000, 16_000, 32_000, 48_000):
        raise ValueError("WebRTC VAD requires an 8, 16, 32 or 48 kHz sample rate")
    if buffer.sample_width != 2:
        raise ValueError("WebRTC VAD requires 16-bit PCM")
    if frame_ms not in (10, 20, 30):
        raise ValueError("WebRTC VAD frame_ms must be 10, 20 or 30")
    if aggressiveness not in (0, 1, 2, 3):
        raise ValueError("WebRTC VAD aggressiveness must be 0, 1, 2 or 3")

    if vad_factory is None:
        try:
            import webrtcvad
        except ImportError as error:
            raise RuntimeError("Install the optional webrtcvad-wheels package to use WebRTC VAD") from error
        vad_factory = webrtcvad.Vad
    detector = vad_factory(aggressiveness)

    frame_samples = buffer.sample_rate * frame_ms // 1000
    frame_bytes = frame_samples * buffer.sample_width
    frames = []
    for offset in range(0, len(buffer.pcm) - frame_bytes + 1, frame_bytes):
        chunk = buffer.pcm[offset : offset + frame_bytes]
        active = bool(detector.is_speech(chunk, buffer.sample_rate))
        start_s = offset / (buffer.sample_rate * buffer.sample_width)
        end_s = (offset + frame_bytes) / (buffer.sample_rate * buffer.sample_width)
        frames.append(ActivityFrame(start_s, end_s, 0, active))
    return tuple(frames)
