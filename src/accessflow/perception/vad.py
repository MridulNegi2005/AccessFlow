"""Optional WebRTC voice-activity detection for local timing experiments."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .audio import ActivityFrame, AudioBuffer, _to_pcm16


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
    if (
        isinstance(buffer.sample_rate, bool)
        or not isinstance(buffer.sample_rate, int)
        or buffer.sample_rate not in (8_000, 16_000, 32_000, 48_000)
    ):
        raise ValueError("WebRTC VAD requires an 8, 16, 32 or 48 kHz sample rate")
    if (
        isinstance(buffer.sample_width, bool)
        or not isinstance(buffer.sample_width, int)
        or buffer.sample_width not in (1, 2, 3, 4)
    ):
        raise ValueError("PCM loader supports sample widths from 1 to 4 bytes")
    if isinstance(frame_ms, bool) or not isinstance(frame_ms, int) or frame_ms not in (10, 20, 30):
        raise ValueError("WebRTC VAD frame_ms must be 10, 20 or 30")
    if (
        isinstance(aggressiveness, bool)
        or not isinstance(aggressiveness, int)
        or aggressiveness not in (0, 1, 2, 3)
    ):
        raise ValueError("WebRTC VAD aggressiveness must be 0, 1, 2 or 3")

    if vad_factory is None:
        try:
            import webrtcvad
        except ImportError as error:
            raise RuntimeError("Install the optional webrtcvad-wheels package to use WebRTC VAD") from error
        vad_factory = webrtcvad.Vad
    detector = vad_factory(aggressiveness)

    pcm16 = _to_pcm16(buffer.pcm, buffer.sample_width)
    frame_samples = buffer.sample_rate * frame_ms // 1000
    frame_bytes = frame_samples * 2
    frames = []
    for offset in range(0, len(pcm16) - frame_bytes + 1, frame_bytes):
        chunk = pcm16[offset : offset + frame_bytes]
        active = bool(detector.is_speech(chunk, buffer.sample_rate))
        start_s = offset / (buffer.sample_rate * 2)
        end_s = (offset + frame_bytes) / (buffer.sample_rate * 2)
        frames.append(ActivityFrame(start_s, end_s, 0, active))
    return tuple(frames)
