import base64
import hashlib
import json
from pathlib import Path

import pytest

from accessflow.perception import vision_benchmark as benchmark


def _manifest():
    root = Path(__file__).parents[2]
    return root, json.loads(
        (root / "docs" / "feedback" / "SCENARIO_MATRIX.json").read_text(encoding="utf-8")
    )


class _ReplayVision:
    backend_name = "fake/replay-vision"

    def __init__(self, captions):
        self._captions = captions

    def __call__(self, path: Path) -> str:
        return self._captions[path.stem]


@pytest.mark.asyncio
async def test_vision_benchmark_replays_all_image_cases_and_scores_labels():
    root, manifest = _manifest()
    image_cases = [case for case in manifest["cases"] if case["modality"] == "image"]
    provider = _ReplayVision({case["id"]: case["visual_label"] for case in image_cases})

    report = await benchmark.run_vision_benchmark(
        provider,
        root=root,
        mode="offline_injected",
        backend=provider.backend_name,
        model="synthetic-replay",
        prompt="synthetic label replay",
    )

    assert report["status"] == "completed"
    assert report["mode"] == "offline_injected"
    assert report["backend"] == "fake/replay-vision"
    assert report["model"] == "synthetic-replay"
    assert report["prompt"] == "synthetic label replay"
    assert report["cases"] == 12
    assert report["failures"] == 0
    assert report["mean_elapsed_s"] >= 0
    assert report["mean_label_token_recall"] == 1.0
    assert all(item["status"] == "completed" for item in report["results"])
    assert all(item["source_id"] == item["id"] for item in report["results"])
    assert all(item["sha256"] for item in report["results"])
    assert all(item["label_token_recall"] == 1.0 for item in report["results"])

    for item, case in zip(report["results"], image_cases):
        expected = base64.b64decode(case["asset"]["payload_base64"], validate=True)
        assert item["id"] == case["id"]
        assert item["sha256"] == hashlib.sha256(expected).hexdigest().upper()


@pytest.mark.asyncio
async def test_vision_benchmark_records_provider_failures_without_caption():
    root, manifest = _manifest()
    image_cases = [case for case in manifest["cases"] if case["modality"] == "image"]

    class FailingVision(_ReplayVision):
        def __call__(self, path: Path) -> str:
            if path.stem == "image-10":
                raise RuntimeError("vision service unavailable")
            return super().__call__(path)

    provider = FailingVision({case["id"]: case["visual_label"] for case in image_cases})
    report = await benchmark.run_vision_benchmark(
        provider,
        root=root,
        mode="offline_injected",
        backend=provider.backend_name,
        model="synthetic-replay",
        prompt="synthetic label replay",
    )

    failed = next(item for item in report["results"] if item["id"] == "image-10")
    assert report["status"] == "failed"
    assert report["cases"] == 12
    assert report["failures"] == 1
    assert report["mean_label_token_recall"] == 0.916667
    assert failed["status"] == "error"
    assert failed["caption"] is None
    assert failed["label_token_recall"] == 0.0
    assert failed["failure"] == {
        "type": "RuntimeError",
        "message": "vision service unavailable",
    }
    assert sum(item["status"] == "completed" for item in report["results"]) == 11


def test_vision_benchmark_is_explicitly_opt_in(capsys):
    assert benchmark.main([]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output == {
        "reason": "live vision is opt-in; rerun with --live",
        "status": "SKIPPED",
    }
