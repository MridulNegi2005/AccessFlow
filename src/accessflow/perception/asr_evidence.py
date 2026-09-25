"""Opt-in Faster Whisper measurement; never an agent observation or turn decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from importlib.metadata import version
from numbers import Real
from pathlib import Path
from time import perf_counter
from typing import Any

from .local import validate_wav


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def inspect_whisper(model: Any, wav_path: Path) -> dict[str, Any]:
    """Retain model-supplied evidence without interpreting it as calibrated confidence."""
    metadata = validate_wav(wav_path)
    with wav_path.open("rb") as handle:
        sha256 = hashlib.file_digest(handle, "sha256").hexdigest()

    started = perf_counter()
    segments, info = model.transcribe(
        str(wav_path), beam_size=5, word_timestamps=True
    )
    rows = []
    for segment in segments:
        text = segment.text
        if not isinstance(text, str):
            raise ValueError("ASR segment text must be a string")
        words = []
        for word in getattr(segment, "words", None) or ():
            if not isinstance(word.word, str):
                raise ValueError("ASR word text must be a string")
            words.append(
                {
                    "text": word.word,
                    "start_s": _finite(getattr(word, "start", None)),
                    "end_s": _finite(getattr(word, "end", None)),
                    "decoder_probability": _finite(getattr(word, "probability", None)),
                }
            )
        rows.append(
            {
                "text": text,
                "start_s": _finite(getattr(segment, "start", None)),
                "end_s": _finite(getattr(segment, "end", None)),
                "avg_logprob": _finite(getattr(segment, "avg_logprob", None)),
                "no_speech_prob": _finite(getattr(segment, "no_speech_prob", None)),
                "compression_ratio": _finite(getattr(segment, "compression_ratio", None)),
                "words": words,
            }
        )
    elapsed_s = perf_counter() - started
    return {
        "mode": "direct_model_probe_not_agent_observation",
        "backend": "faster-whisper/cpu-int8",
        "wav_sha256": sha256,
        "wav_format": {
            "channels": metadata.channels,
            "sample_width": metadata.sample_width,
            "sample_rate": metadata.sample_rate,
            "frames": metadata.frames,
            "duration_s": metadata.frames / metadata.sample_rate,
        },
        "inference_elapsed_s": elapsed_s,
        "language": getattr(info, "language", None),
        "language_probability": _finite(getattr(info, "language_probability", None)),
        "status": "decoded_segments" if rows else "no_decoded_segments",
        "transcript": " ".join(row["text"].strip() for row in rows).strip(),
        "segments": rows,
        "decoder_estimates_are_not_calibrated_confidence": True,
        "turn_finality": "not_inferred_from_this_probe",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--wav", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.model_path.is_dir():
        parser.error("--model-path must be an installed directory")
    validate_wav(args.wav)
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise SystemExit("Install the declared audio extra for this opt-in probe") from error

    load_started = perf_counter()
    model = WhisperModel(str(args.model_path), device="cpu", compute_type="int8")
    load_elapsed_s = perf_counter() - load_started
    report = inspect_whisper(model, args.wav)
    report["model_name"] = args.model_name
    report["model_snapshot"] = args.model_path.name
    report["faster_whisper_version"] = version("faster-whisper")
    report["model_load_elapsed_s"] = load_elapsed_s
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
