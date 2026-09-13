"""Small PCM loading and energy-activity helpers for local audio experiments."""

from __future__ import annotations

import audioop
import wave
from dataclasses import dataclass
from pathlib import Path

from .local import WavFormat, validate_wav


@dataclass(frozen=True)
class AudioBuffer:
    """Mono PCM samples after optional rate conversion."""

    pcm: bytes
    sample_rate: int
    sample_width: int


@dataclass(frozen=True)
class ActivityFrame:
    start_s: float
    end_s: float
    rms: int
    active: bool


def load_pcm(path: Path, *, target_rate: int = 16_000) -> AudioBuffer:
    """Load PCM WAV audio as mono samples at ``target_rate``."""
    metadata: WavFormat = validate_wav(path)
    if metadata.channels not in (1, 2):
        raise ValueError("PCM loader supports mono or stereo WAV input")
    if target_rate < 1:
        raise ValueError("target_rate must be positive")

    with wave.open(str(path), "rb") as handle:
        pcm = handle.readframes(metadata.frames)
    if metadata.channels == 2:
        pcm = audioop.tomono(pcm, metadata.sample_width, 0.5, 0.5)
    if metadata.sample_rate != target_rate:
        pcm, _ = audioop.ratecv(
            pcm,
            metadata.sample_width,
            1,
            metadata.sample_rate,
            target_rate,
            None,
        )
    return AudioBuffer(pcm=pcm, sample_rate=target_rate, sample_width=metadata.sample_width)


def energy_activity(
    buffer: AudioBuffer,
    *,
    frame_ms: int = 20,
    rms_threshold: int = 500,
) -> tuple[ActivityFrame, ...]:
    """Return a deterministic energy baseline; this is not a speech classifier."""
    if frame_ms < 1 or rms_threshold < 0:
        raise ValueError("frame_ms must be positive and rms_threshold cannot be negative")
    frame_samples = max(1, buffer.sample_rate * frame_ms // 1000)
    frame_bytes = frame_samples * buffer.sample_width
    frames = []
    for offset in range(0, len(buffer.pcm), frame_bytes):
        chunk = buffer.pcm[offset : offset + frame_bytes]
        if len(chunk) < buffer.sample_width:
            break
        start_s = offset / (buffer.sample_rate * buffer.sample_width)
        end_s = (offset + len(chunk)) / (buffer.sample_rate * buffer.sample_width)
        rms = audioop.rms(chunk, buffer.sample_width)
        frames.append(ActivityFrame(start_s, end_s, rms, rms >= rms_threshold))
    return tuple(frames)