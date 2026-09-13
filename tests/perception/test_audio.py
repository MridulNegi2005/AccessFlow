import struct
import wave
from pathlib import Path

import pytest

from accessflow.perception import AudioBuffer, WavFormat, energy_activity, load_pcm


def _write_stereo_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(8_000)
        handle.writeframes(b"\x00\x00\x00\x00" * 80)


def test_checked_in_fixture_loads_as_target_rate():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"

    buffer = load_pcm(fixture)

    assert buffer.sample_rate == 16_000
    assert buffer.sample_width == 2
    assert len(buffer.pcm) == 16_000


def test_stereo_input_is_downmixed_and_resampled(tmp_path: Path):
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_wav(wav_path)

    buffer = load_pcm(wav_path, target_rate=16_000)

    assert buffer.sample_rate == 16_000
    assert len(buffer.pcm) / 2 == pytest.approx(160, abs=1)


def test_energy_activity_exposes_frame_timing_without_claiming_vad():
    silence = b"\x00\x00" * 320
    tone = b"".join(struct.pack("<h", 10_000) for _ in range(320))

    frames = energy_activity(AudioBuffer(silence + tone, 16_000, 2), rms_threshold=500)

    assert len(frames) == 2
    assert frames[0].active is False
    assert frames[0].start_s == 0
    assert frames[0].end_s == pytest.approx(0.02)
    assert frames[1].active is True
    assert frames[1].rms == 10_000


def test_energy_activity_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="frame_ms"):
        energy_activity(AudioBuffer(b"\x00\x00", 16_000, 2), frame_ms=0)


def test_audio_buffer_metadata_is_explicit():
    assert WavFormat(channels=1, sample_width=2, sample_rate=16_000, frames=8_000)

@pytest.mark.parametrize(
    ("sample_width", "frames"),
    [
        (1, bytes([128, 255, 0])),
        (2, b"\x00\x00\xff\x7f\x00\x80"),
        (3, b"\x00\x00\x00\xff\xff\x7f\x00\x00\x80"),
        (4, b"\x00\x00\x00\x00\xff\xff\xff\x7f\x00\x00\x00\x80"),
    ],
)
def test_loader_preserves_common_pcm_widths(tmp_path: Path, sample_width: int, frames: bytes):
    wav_path = tmp_path / f"width-{sample_width}.wav"
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(sample_width)
        handle.setframerate(16_000)
        handle.writeframes(frames)

    buffer = load_pcm(wav_path)

    assert buffer.sample_width == sample_width
    assert buffer.pcm == frames
