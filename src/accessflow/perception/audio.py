"""Small PCM loading and energy-activity helpers for local audio experiments."""

from __future__ import annotations

import math
import struct
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


def _decode_samples(pcm: bytes, sample_width: int) -> list[int]:
    if sample_width not in (1, 2, 3, 4):
        raise ValueError("PCM loader supports sample widths from 1 to 4 bytes")
    if len(pcm) % sample_width:
        raise ValueError("PCM data ends with a partial sample")

    samples = []
    for offset in range(0, len(pcm), sample_width):
        raw = pcm[offset : offset + sample_width]
        if sample_width == 1:
            samples.append(raw[0] - 128)
        elif sample_width == 2:
            samples.append(struct.unpack_from("<h", raw)[0])
        else:
            samples.append(int.from_bytes(raw, "little", signed=True))
    return samples


def _encode_samples(samples: list[int], sample_width: int) -> bytes:
    if sample_width not in (1, 2, 3, 4):
        raise ValueError("PCM loader supports sample widths from 1 to 4 bytes")
    minimum = -(1 << (sample_width * 8 - 1))
    maximum = (1 << (sample_width * 8 - 1)) - 1
    encoded = bytearray()
    for value in samples:
        clipped = max(minimum, min(maximum, value))
        if sample_width == 1:
            encoded.append(clipped + 128)
        elif sample_width == 2:
            encoded.extend(struct.pack("<h", clipped))
        else:
            encoded.extend(clipped.to_bytes(sample_width, "little", signed=True))
    return bytes(encoded)


def _to_pcm16(pcm: bytes, sample_width: int) -> bytes:
    """Convert signed or unsigned PCM samples to little-endian signed 16-bit PCM."""
    samples = _decode_samples(pcm, sample_width)
    if sample_width == 2:
        return pcm

    scale = 1 << (sample_width * 8 - 1)
    normalized = [max(-32768, min(32767, round(sample * 32768 / scale))) for sample in samples]
    return _encode_samples(normalized, 2)


def _downmix_to_mono(pcm: bytes, sample_width: int, channels: int) -> bytes:
    if channels == 1:
        return pcm
    if channels != 2:
        raise ValueError("PCM loader supports mono or stereo WAV input")
    samples = _decode_samples(pcm, sample_width)
    if len(samples) % 2:
        raise ValueError("Stereo PCM data ends with a partial frame")
    mono = [(samples[index] + samples[index + 1]) // 2 for index in range(0, len(samples), 2)]
    return _encode_samples(mono, sample_width)


def _resample_mono(pcm: bytes, sample_width: int, source_rate: int, target_rate: int) -> bytes:
    if source_rate == target_rate:
        return pcm
    samples = _decode_samples(pcm, sample_width)
    if not samples:
        return pcm

    output_count = max(1, (len(samples) * target_rate + source_rate // 2) // source_rate)
    output = []
    for index in range(output_count):
        position = index * source_rate / target_rate
        left = min(int(position), len(samples) - 1)
        right = min(left + 1, len(samples) - 1)
        fraction = position - left
        output.append(round(samples[left] + (samples[right] - samples[left]) * fraction))
    return _encode_samples(output, sample_width)


def _rms(pcm: bytes, sample_width: int) -> int:
    samples = _decode_samples(_to_pcm16(pcm, sample_width), 2)
    if not samples:
        return 0
    return math.isqrt(sum(sample * sample for sample in samples) // len(samples))


def load_pcm(path: Path, *, target_rate: int = 16_000) -> AudioBuffer:
    """Load PCM WAV audio as mono samples at target_rate.

    The decoder and linear resampler use maintained Python standard-library
    primitives so this path remains usable after audioop removal in Python 3.13.
    """
    metadata: WavFormat = validate_wav(path)
    if metadata.channels not in (1, 2):
        raise ValueError("PCM loader supports mono or stereo WAV input")
    if metadata.sample_width not in (1, 2, 3, 4):
        raise ValueError("PCM loader supports sample widths from 1 to 4 bytes")
    if isinstance(target_rate, bool) or not isinstance(target_rate, int) or target_rate < 1:
        raise ValueError("target_rate must be positive")

    with wave.open(str(path), "rb") as handle:
        pcm = handle.readframes(metadata.frames)
    pcm = _downmix_to_mono(pcm, metadata.sample_width, metadata.channels)
    pcm = _resample_mono(pcm, metadata.sample_width, metadata.sample_rate, target_rate)
    return AudioBuffer(pcm=pcm, sample_rate=target_rate, sample_width=metadata.sample_width)


def energy_activity(
    buffer: AudioBuffer,
    *,
    frame_ms: int = 20,
    rms_threshold: int = 500,
) -> tuple[ActivityFrame, ...]:
    """Return a deterministic energy baseline; this is not a speech classifier."""
    if (
        isinstance(buffer.sample_rate, bool)
        or not isinstance(buffer.sample_rate, int)
        or buffer.sample_rate < 1
    ):
        raise ValueError("sample_rate must be a positive integer")
    if (
        isinstance(buffer.sample_width, bool)
        or not isinstance(buffer.sample_width, int)
        or buffer.sample_width not in (1, 2, 3, 4)
    ):
        raise ValueError("PCM loader supports sample widths from 1 to 4 bytes")
    if (
        isinstance(frame_ms, bool)
        or not isinstance(frame_ms, int)
        or frame_ms < 1
        or isinstance(rms_threshold, bool)
        or not isinstance(rms_threshold, int)
        or rms_threshold < 0
    ):
        raise ValueError("frame_ms must be positive and rms_threshold cannot be negative")
    if len(buffer.pcm) % buffer.sample_width:
        raise ValueError("PCM data ends with a partial sample")
    frame_samples = max(1, buffer.sample_rate * frame_ms // 1000)
    frame_bytes = frame_samples * buffer.sample_width
    frames = []
    for offset in range(0, len(buffer.pcm), frame_bytes):
        chunk = buffer.pcm[offset : offset + frame_bytes]
        if len(chunk) < buffer.sample_width:
            break
        start_s = offset / (buffer.sample_rate * buffer.sample_width)
        end_s = (offset + len(chunk)) / (buffer.sample_rate * buffer.sample_width)
        rms = _rms(chunk, buffer.sample_width)
        frames.append(ActivityFrame(start_s, end_s, rms, rms >= rms_threshold))
    return tuple(frames)
