from pathlib import Path
from types import SimpleNamespace

import pytest

from accessflow.perception.asr_evidence import inspect_whisper


FIXTURE = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"


def test_probe_preserves_repetition_correction_and_uncalibrated_word_estimates():
    class Model:
        def transcribe(self, path, *, beam_size, word_timestamps):
            assert Path(path) == FIXTURE
            assert beam_size == 5
            assert word_timestamps is True
            return (
                [
                    SimpleNamespace(
                        text=" Tuesday, Tuesday.",
                        start=0.1,
                        end=1.2,
                        avg_logprob=-0.5,
                        no_speech_prob=0.02,
                        compression_ratio=1.1,
                        words=[SimpleNamespace(word=" Tuesday,", start=0.1, end=0.5, probability=0.7)],
                    ),
                    SimpleNamespace(
                        text=" Actually Wednesday at five.",
                        start=2.0,
                        end=3.5,
                        avg_logprob=-0.4,
                        no_speech_prob=0.01,
                        compression_ratio=1.0,
                        words=None,
                    ),
                ],
                SimpleNamespace(language="en", language_probability=0.9),
            )

    report = inspect_whisper(Model(), FIXTURE)

    assert report["transcript"] == "Tuesday, Tuesday. Actually Wednesday at five."
    assert report["segments"][0]["words"][0]["decoder_probability"] == 0.7
    assert report["segments"][1]["start_s"] == 2.0
    assert report["language_probability"] == 0.9
    assert report["decoder_estimates_are_not_calibrated_confidence"] is True
    assert report["turn_finality"] == "not_inferred_from_this_probe"
    assert len(report["wav_sha256"]) == 64


def test_probe_marks_zero_segments_without_claiming_silence():
    class Model:
        def transcribe(self, path, *, beam_size, word_timestamps):
            return [], SimpleNamespace(language=None, language_probability=None)

    report = inspect_whisper(Model(), FIXTURE)

    assert report["status"] == "no_decoded_segments"
    assert report["transcript"] == ""
    assert report["segments"] == []
    assert report["turn_finality"] == "not_inferred_from_this_probe"


def test_probe_rejects_nontext_segment():
    class Model:
        def transcribe(self, path, *, beam_size, word_timestamps):
            return [SimpleNamespace(text=None)], None

    with pytest.raises(ValueError, match="segment text"):
        inspect_whisper(Model(), FIXTURE)
