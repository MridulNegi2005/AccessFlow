import struct
import wave
from pathlib import Path

import pytest

from accessflow.perception import ActivityFrame, AudioBuffer, WavFormat, energy_activity, load_pcm, PauseCandidate, pause_candidates, summarize_activity, validate_wav, webrtc_activity


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


def test_checked_in_speech_fixture_has_declared_format():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_speech.wav"

    assert validate_wav(fixture) == WavFormat(
        channels=1,
        sample_width=2,
        sample_rate=22_050,
        frames=116_949,
    )


def test_activity_summary_reports_windows_and_trailing_pause_without_completion():
    frames = (
        ActivityFrame(0.0, 0.02, 0, False),
        ActivityFrame(0.02, 0.04, 1_000, True),
        ActivityFrame(0.04, 0.06, 1_000, True),
        ActivityFrame(0.06, 0.46, 0, False),
    )

    summary = summarize_activity(frames, pause_after_s=0.2)

    assert summary.windows[0].start_s == 0.02
    assert summary.windows[0].end_s == 0.06
    assert summary.active_duration_s == pytest.approx(0.04)
    assert summary.leading_silence_s == 0.02
    assert summary.trailing_silence_s == 0.4
    assert summary.pause_detected is True


def test_all_silence_does_not_look_like_a_pause_after_speech():
    frames = (
        ActivityFrame(0.0, 0.02, 0, False),
        ActivityFrame(0.02, 0.04, 0, False),
    )

    summary = summarize_activity(frames)

    assert summary.windows == ()
    assert summary.pause_detected is False


def test_activity_summary_rejects_empty_frames_and_invalid_threshold():
    with pytest.raises(ValueError, match="at least one"):
        summarize_activity(())

    with pytest.raises(ValueError, match="pause_after_s"):
        summarize_activity((ActivityFrame(0.0, 0.02, 0, False),), pause_after_s=-1)


def test_webrtc_activity_uses_injected_detector_without_optional_import():
    calls = []

    class Detector:
        def __init__(self, aggressiveness: int):
            assert aggressiveness == 2

        def is_speech(self, chunk: bytes, sample_rate: int) -> bool:
            calls.append((len(chunk), sample_rate))
            return len(calls) == 1

    buffer = AudioBuffer(b"\x00\x00" * 640, 16_000, 2)

    frames = webrtc_activity(buffer, frame_ms=20, vad_factory=Detector)

    assert len(frames) == 2
    assert [frame.active for frame in frames] == [True, False]
    assert calls == [(640, 16_000), (640, 16_000)]


def test_webrtc_activity_rejects_unsupported_format():
    with pytest.raises(ValueError, match="requires 16-bit"):
        webrtc_activity(AudioBuffer(b"\x00" * 640, 16_000, 1))

    with pytest.raises(ValueError, match="frame_ms"):
        webrtc_activity(AudioBuffer(b"\x00\x00" * 640, 16_000, 2), frame_ms=25)


def test_checked_in_pause_fixture_has_declared_format():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_pause_correction.wav"

    assert validate_wav(fixture) == WavFormat(
        channels=1,
        sample_width=2,
        sample_rate=22_050,
        frames=132_830,
    )


def test_pause_candidates_keep_internal_and_trailing_gaps_separate():
    frames = (
        ActivityFrame(0.00, 0.02, 1_000, True),
        ActivityFrame(0.02, 0.62, 0, False),
        ActivityFrame(0.62, 0.64, 1_000, True),
        ActivityFrame(0.64, 1.14, 0, False),
    )

    candidates = pause_candidates(frames, min_pause_s=0.4)

    assert len(candidates) == 2
    assert candidates[0] == PauseCandidate(0.02, 0.62, pytest.approx(0.6), trailing=False)
    assert candidates[1].start_s == 0.64
    assert candidates[1].end_s == pytest.approx(1.14)
    assert candidates[1].duration_s == pytest.approx(0.5)
    assert candidates[1].trailing is True


def test_pause_candidates_ignore_short_gaps_and_all_silence():
    frames = (
        ActivityFrame(0.00, 0.02, 1_000, True),
        ActivityFrame(0.02, 0.12, 0, False),
        ActivityFrame(0.12, 0.14, 1_000, True),
    )

    assert pause_candidates(frames, min_pause_s=0.4) == ()
    assert pause_candidates(
        (ActivityFrame(0.0, 0.5, 0, False),),
        min_pause_s=0.1,
    ) == ()
