import math
import struct
import wave
from pathlib import Path

import pytest

from accessflow.perception import ActivityFrame, ActivitySummary, ActivityWindow, AudioBuffer, WavFormat, energy_activity, load_pcm, PauseCandidate, pause_candidates, summarize_activity, validate_wav, webrtc_activity
from accessflow.perception import audio as audio_module


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


def test_loader_rejects_oversized_resampled_payload(tmp_path: Path, monkeypatch):
    wav_path = tmp_path / "resampled-too-large.wav"
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8_000)
        handle.writeframes(b"\x00\x00" * 4)

    monkeypatch.setattr(audio_module, "MAX_WAV_DECODED_BYTES", 8)

    with pytest.raises(ValueError, match="resampled PCM payload"):
        load_pcm(wav_path, target_rate=16_000)


@pytest.mark.parametrize("target_rate", [True, 0, -1, 16_000.0, "16000"])
def test_loader_rejects_invalid_target_rate(target_rate):
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"

    with pytest.raises(ValueError, match="target_rate"):
        load_pcm(fixture, target_rate=target_rate)


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


@pytest.mark.parametrize(
    ("sample_width", "sample"),
    [(1, 64), (2, 16_384), (3, 4_194_304), (4, 1_073_741_824)],
)
def test_energy_activity_normalizes_equivalent_pcm_amplitudes(sample_width: int, sample: int):
    if sample_width == 1:
        encoded = bytes([sample + 128])
    else:
        encoded = sample.to_bytes(sample_width, "little", signed=True)

    frames = energy_activity(AudioBuffer(encoded * 320, 16_000, sample_width), rms_threshold=12_000)

    assert len(frames) == 1
    assert frames[0].rms == 16_384
    assert frames[0].active is True


def test_energy_activity_uses_canonical_full_scale_for_clipped_samples():
    values = {
        1: bytes([255]),
        2: struct.pack("<h", 32_767),
        3: ((1 << 23) - 1).to_bytes(3, "little", signed=True),
        4: ((1 << 31) - 1).to_bytes(4, "little", signed=True),
    }

    for sample_width, encoded in values.items():
        frames = energy_activity(AudioBuffer(encoded * 320, 16_000, sample_width))
        assert frames[0].rms <= 32_767
        assert frames[0].active is True


def test_energy_activity_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="frame_ms"):
        energy_activity(AudioBuffer(b"\x00\x00", 16_000, 2), frame_ms=0)
    with pytest.raises(ValueError, match="frame_ms"):
        energy_activity(AudioBuffer(b"\x00\x00", 16_000, 2), frame_ms=20.0)
    with pytest.raises(ValueError, match="rms_threshold"):
        energy_activity(AudioBuffer(b"\x00\x00", 16_000, 2), rms_threshold=500.0)


def test_energy_activity_rejects_invalid_buffer_metadata():
    for sample_rate in (0, 16_000.0, True):
        with pytest.raises(ValueError, match="sample_rate"):
            energy_activity(AudioBuffer(b"\x00\x00", sample_rate, 2))
    with pytest.raises(ValueError, match="sample widths"):
        energy_activity(AudioBuffer(b"\x00\x00", 16_000, True))


def test_energy_activity_rejects_partial_sample():
    with pytest.raises(ValueError, match="partial sample"):
        energy_activity(AudioBuffer(b"\x00", 16_000, 2))


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


def test_wav_validation_rejects_truncated_pcm_payload(tmp_path: Path):
    wav_path = tmp_path / "truncated.wav"
    with wave.open(str(wav_path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\x00\x00" * 8)

    wav_path.write_bytes(wav_path.read_bytes()[:-2])

    with pytest.raises(ValueError, match="truncated"):
        validate_wav(wav_path)


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


@pytest.mark.parametrize(
    ("start_s", "end_s", "message"),
    [
        (-0.1, 0.1, "start_s"),
        (0.0, -0.1, "end_s"),
        (0.5, 0.5, "end_s"),
        (0.5, 0.4, "end_s"),
        (0.0, math.inf, "end_s"),
        (math.nan, 0.1, "start_s"),
        ("0.0", 0.1, "start_s"),
    ],
)
def test_activity_windows_reject_invalid_values(start_s, end_s, message):
    with pytest.raises(ValueError, match=message):
        ActivityWindow(start_s, end_s)


def test_all_silence_does_not_look_like_a_pause_after_speech():
    frames = (
        ActivityFrame(0.0, 0.02, 0, False),
        ActivityFrame(0.02, 0.04, 0, False),
    )

    summary = summarize_activity(frames)

    assert summary.windows == ()
    assert summary.pause_detected is False


@pytest.mark.parametrize(
    ("active_duration_s", "leading_silence_s", "trailing_silence_s", "pause_detected", "message"),
    [
        (-0.1, 0.0, 0.0, False, "active_duration_s"),
        (0.2, math.nan, 0.0, False, "leading_silence_s"),
        (0.2, 0.0, math.inf, False, "trailing_silence_s"),
        (0.2, 0.0, 0.0, "false", "pause_detected"),
        (0.1, 0.0, 0.0, False, "active_duration_s"),
    ],
)
def test_activity_summaries_reject_invalid_values(
    active_duration_s, leading_silence_s, trailing_silence_s, pause_detected, message
):
    with pytest.raises(ValueError, match=message):
        ActivitySummary(
            windows=(ActivityWindow(0.0, 0.2),),
            active_duration_s=active_duration_s,
            leading_silence_s=leading_silence_s,
            trailing_silence_s=trailing_silence_s,
            pause_detected=pause_detected,
        )


def test_activity_summary_uses_bounded_absolute_duration_tolerance():
    accepted = ActivitySummary(
        windows=(ActivityWindow(0.0, 0.2),),
        active_duration_s=0.2 + 5e-10,
        leading_silence_s=0.0,
        trailing_silence_s=0.0,
        pause_detected=False,
    )

    assert accepted.active_duration_s == pytest.approx(0.2, abs=1e-9)

    with pytest.raises(ValueError, match="active_duration_s"):
        ActivitySummary(
            windows=(ActivityWindow(0.0, 1e9),),
            active_duration_s=1e9 + 0.5,
            leading_silence_s=0.0,
            trailing_silence_s=0.0,
            pause_detected=False,
        )


@pytest.mark.parametrize(
    "windows",
    [
        (ActivityWindow(0.0, 1.0), ActivityWindow(0.5, 1.5)),
        (ActivityWindow(1.0, 2.0), ActivityWindow(0.0, 0.5)),
    ],
)
def test_activity_summary_rejects_overlapping_or_out_of_order_windows(windows):
    with pytest.raises(ValueError, match="chronological and non-overlapping"):
        ActivitySummary(
            windows=windows,
            active_duration_s=sum(window.end_s - window.start_s for window in windows),
            leading_silence_s=0.0,
            trailing_silence_s=0.0,
            pause_detected=False,
        )


def test_activity_summary_rejects_empty_frames_and_invalid_threshold():
    with pytest.raises(ValueError, match="at least one"):
        summarize_activity(())

    with pytest.raises(ValueError, match="pause_after_s"):
        summarize_activity((ActivityFrame(0.0, 0.02, 0, False),), pause_after_s=-1)


@pytest.mark.parametrize(
    ("start_s", "end_s", "rms", "active", "message"),
    [
        (0.2, 0.2, 0, False, "end_s"),
        (0.3, 0.2, 0, False, "end_s"),
        (-0.1, 0.1, 0, False, "start_s"),
        (0.0, math.inf, 0, False, "end_s"),
        (0.0, math.nan, 0, False, "end_s"),
        (0.0, 0.1, -1, False, "rms"),
    ],
)
def test_activity_frames_reject_invalid_values(start_s, end_s, rms, active, message):
    with pytest.raises(ValueError, match=message):
        ActivityFrame(start_s, end_s, rms, active)


def test_activity_summary_rejects_out_of_order_frames():
    frames = (
        ActivityFrame(0.5, 0.6, 1_000, True),
        ActivityFrame(0.0, 0.1, 0, False),
    )

    with pytest.raises(ValueError, match="chronological"):
        summarize_activity(frames)
    with pytest.raises(ValueError, match="chronological"):
        pause_candidates(frames)


@pytest.mark.parametrize(
    "frames",
    [
        (
            ActivityFrame(0.0, 0.5, 1_000, True),
            ActivityFrame(0.4, 0.8, 1_000, True),
        ),
        (
            ActivityFrame(0.0, 0.5, 1_000, True),
            ActivityFrame(0.0, 0.5, 1_000, True),
        ),
    ],
)
def test_activity_summary_rejects_overlapping_frames(frames):
    with pytest.raises(ValueError, match="non-overlapping"):
        summarize_activity(frames)
    with pytest.raises(ValueError, match="non-overlapping"):
        pause_candidates(frames)


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


@pytest.mark.parametrize("sample_width", [1, 3, 4])
def test_webrtc_activity_converts_supported_pcm_widths_to_16_bit(sample_width: int):
    if sample_width == 1:
        sample = bytes([192])
    else:
        sample = (1 << (sample_width * 8 - 2)).to_bytes(sample_width, "little", signed=True)
    observed = []

    class Detector:
        def __init__(self, aggressiveness: int):
            assert aggressiveness == 2

        def is_speech(self, chunk: bytes, sample_rate: int) -> bool:
            observed.append((len(chunk), sample_rate, chunk[:2]))
            return True

    frames = webrtc_activity(
        AudioBuffer(sample * 320, 16_000, sample_width),
        vad_factory=Detector,
    )

    assert len(frames) == 1
    assert observed == [(640, 16_000, struct.pack("<h", 16_384))]


def test_webrtc_activity_rejects_unsupported_format():
    with pytest.raises(ValueError, match="sample widths"):
        webrtc_activity(AudioBuffer(b"\x00" * 640, 16_000, 5))

    with pytest.raises(ValueError, match="frame_ms"):
        webrtc_activity(AudioBuffer(b"\x00\x00" * 640, 16_000, 2), frame_ms=25)
    with pytest.raises(ValueError, match="frame_ms"):
        webrtc_activity(AudioBuffer(b"\x00\x00" * 640, 16_000, 2), frame_ms=20.0)
    with pytest.raises(ValueError, match="aggressiveness"):
        webrtc_activity(AudioBuffer(b"\x00\x00" * 640, 16_000, 2), aggressiveness=2.0)
    with pytest.raises(ValueError, match="sample rate"):
        webrtc_activity(AudioBuffer(b"\x00\x00" * 640, 16_000.0, 2))


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
    assert candidates[0] == PauseCandidate(0.02, 0.62, 0.6, trailing=False)
    assert candidates[0].duration_s == pytest.approx(0.6)
    assert candidates[1].start_s == 0.64
    assert candidates[1].end_s == pytest.approx(1.14)
    assert candidates[1].duration_s == pytest.approx(0.5)
    assert candidates[1].trailing is True


@pytest.mark.parametrize(
    ("start_s", "end_s", "duration_s", "message"),
    [
        (-0.1, 0.2, 0.3, "start_s"),
        (0.2, 0.1, 0.1, "end_s"),
        (0.0, 0.2, -0.1, "duration_s"),
        (0.0, math.inf, 1.0, "end_s"),
        (0.0, 0.2, math.nan, "duration_s"),
        (0.0, 0.2, 0.1, "duration_s"),
        (0.0, 0.2, "0.2", "duration_s"),
        (0.0, 0.2, 0.2, "trailing"),
    ],
)
def test_pause_candidates_reject_invalid_values(start_s, end_s, duration_s, message):
    with pytest.raises(ValueError, match=message):
        PauseCandidate(start_s, end_s, duration_s, trailing="false" if message == "trailing" else False)


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


@pytest.mark.parametrize("threshold", [True, math.nan, math.inf, "0.4"])
def test_pause_thresholds_reject_nonfinite_or_wrong_types(threshold):
    frame = (ActivityFrame(0.0, 0.5, 1_000, True),)

    with pytest.raises(ValueError, match="pause_after_s"):
        summarize_activity(frame, pause_after_s=threshold)
    with pytest.raises(ValueError, match="min_pause_s"):
        pause_candidates(frame, min_pause_s=threshold)
