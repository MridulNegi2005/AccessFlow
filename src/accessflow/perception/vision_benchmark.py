"""Opt-in vision quality benchmark over the committed synthetic image inventory."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import time
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..contracts import Frame, FrameEvent
from .local import LocalPerception
from .metrics import normalize_words
from .vision import OllamaVisionProvider


def _image_cases(root: Path) -> list[dict[str, Any]]:
    manifest = json.loads(
        (root / "docs" / "feedback" / "SCENARIO_MATRIX.json").read_text(encoding="utf-8")
    )
    cases = [case for case in manifest["cases"] if case["modality"] == "image"]
    if len(cases) != 12:
        raise ValueError(f"expected 12 image cases, found {len(cases)}")
    return cases


def _token_recall(reference: str, hypothesis: str) -> float:
    expected = Counter(normalize_words(reference))
    if not expected:
        return 1.0
    actual = Counter(normalize_words(hypothesis))
    matched = sum((expected & actual).values())
    return matched / sum(expected.values())


async def run_vision_benchmark(
    provider: Callable[[Path], str],
    *,
    root: Path,
    mode: str,
    backend: str,
    model: str,
    prompt: str,
) -> dict[str, Any]:
    """Run every committed image case and return an evidence-labeled report."""
    cases = _image_cases(root)
    results: list[dict[str, Any]] = []
    adapter = LocalPerception(vision_provider=provider)
    try:
        with TemporaryDirectory(prefix="accessflow-vision-benchmark-") as directory:
            image_root = Path(directory)
            for sequence, case in enumerate(cases, start=1):
                case_id = case["id"]
                raw = base64.b64decode(case["asset"]["payload_base64"], validate=True)
                image_path = image_root / f"{case_id}.png"
                image_path.write_bytes(raw)
                started = time.perf_counter()
                event = FrameEvent(
                    session_id="vision-benchmark",
                    event_id=f"vision-benchmark-{case_id}",
                    timestamp=float(sequence),
                    sequence=sequence,
                    payload=Frame(path=str(image_path), frame_id=case_id),
                )
                result: dict[str, Any] = {
                    "id": case_id,
                    "split": case["split"],
                    "source_id": case_id,
                    "sha256": hashlib.sha256(raw).hexdigest().upper(),
                    "elapsed_s": 0.0,
                    "status": "error",
                    "caption": None,
                    "label_token_recall": 0.0,
                }
                try:
                    observations = [item async for item in adapter.observe(event)]
                    if len(observations) != 1:
                        raise RuntimeError(
                            f"vision provider emitted {len(observations)} observations for {case_id}"
                        )
                    observation = observations[0]
                    result.update(
                        {
                            "status": "completed",
                            "backend": observation.backend,
                            "caption": observation.text,
                            "label_token_recall": _token_recall(
                                case["visual_label"], observation.text
                            ),
                        }
                    )
                except Exception as error:
                    result["failure"] = {
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                result["elapsed_s"] = round(time.perf_counter() - started, 6)
                results.append(result)
    finally:
        await adapter.aclose()

    failures = sum(item["status"] != "completed" for item in results)
    return {
        "report_version": "vision-benchmark.v1",
        "status": "completed" if failures == 0 else "failed",
        "mode": mode,
        "backend": backend,
        "model": model,
        "prompt": prompt,
        "cases": len(results),
        "failures": failures,
        "mean_elapsed_s": round(
            sum(item["elapsed_s"] for item in results) / len(results), 6
        ),
        "mean_label_token_recall": round(
            sum(item["label_token_recall"] for item in results) / len(results), 6
        )
        if results
        else 0.0,
        "results": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="enable the real loopback Ollama vision provider",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ACCESSFLOW_LIVE_VISION_MODEL", "gemma3:4b"),
    )
    parser.add_argument(
        "--endpoint",
        default=os.environ.get(
            "ACCESSFLOW_LIVE_VISION_ENDPOINT",
            "http://127.0.0.1:11434/api/generate",
        ),
    )
    parser.add_argument(
        "--prompt",
        default=os.environ.get(
            "ACCESSFLOW_LIVE_VISION_PROMPT",
            "Describe only the visible device evidence and state uncertainty.",
        ),
    )
    args = parser.parse_args(argv)
    if not args.live:
        print(
            json.dumps(
                {
                    "status": "SKIPPED",
                    "reason": "live vision is opt-in; rerun with --live",
                },
                sort_keys=True,
            )
        )
        return 0

    provider = OllamaVisionProvider(
        model=args.model,
        endpoint=args.endpoint,
        prompt=args.prompt,
    )
    report = asyncio.run(
        run_vision_benchmark(
            provider,
            root=Path(__file__).parents[3],
            mode="live_ollama",
            backend=provider.backend_name,
            model=provider.model,
            prompt=provider.prompt,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
