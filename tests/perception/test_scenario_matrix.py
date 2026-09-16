import base64
import hashlib
import json
from collections import Counter
from pathlib import Path

from accessflow.perception.local import validate_png, validate_wav


def _manifest():
    root = Path(__file__).parents[2]
    return root, json.loads((root / "docs" / "feedback" / "SCENARIO_MATRIX.json").read_text(encoding="utf-8"))


def test_scenario_matrix_matches_weighted_inventory():
    _, manifest = _manifest()
    cases = manifest["cases"]

    assert len(cases) == 60
    assert Counter(case["modality"] for case in cases) == {"text": 30, "audio": 18, "image": 12}
    assert Counter(case["split"] for case in cases) == {"development": 40, "held_out": 20}
    assert manifest["status"] == "authored_provenance_tracked_fake_replay"
    assert manifest["execution"]["mode"] == "offline_fake_mode"
    assert manifest["execution"]["cases_replayed"] == 60
    assert manifest["execution"]["observations_emitted"] == 60
    assert all(case["evidence_status"] == "fake_mode_replayed" for case in cases)


def test_scenario_matrix_case_metadata_is_unique_and_complete():
    _, manifest = _manifest()

    required = {
        "id",
        "modality",
        "split",
        "stimulus",
        "expected_boundary",
        "evidence_status",
        "provenance",
    }
    assert len({case["id"] for case in manifest["cases"]}) == 60
    assert all(required <= case.keys() for case in manifest["cases"])
    assert all(case["stimulus"] and case["expected_boundary"] for case in manifest["cases"])
    assert all(
        case["provenance"]["author"]
        and case["provenance"]["created"]
        and case["provenance"]["consent_license"]
        and case["provenance"]["expected_outcome"]
        for case in manifest["cases"]
    )
    assert all(
        "reference_text" in case
        for case in manifest["cases"]
        if case["modality"] == "audio"
    )
    assert all(
        "visual_label" in case
        for case in manifest["cases"]
        if case["modality"] == "image"
    )


def test_matrix_assets_are_present_and_hash_recorded():
    root, manifest = _manifest()
    assets = [case["asset"] for case in manifest["cases"] if "asset" in case]
    assert len(assets) == 30
    assert all(asset["bytes"] > 0 and asset["sha256"] for asset in assets)
    for asset in assets:
        if "fixture" in asset:
            data = (root / asset["fixture"]).read_bytes()
        else:
            data = base64.b64decode(asset["payload_base64"], validate=True)
        assert len(data) == asset["bytes"]
        assert hashlib.sha256(data).hexdigest().upper() == asset["sha256"]


def test_matrix_audio_and_image_assets_are_structurally_valid(tmp_path: Path):
    root, manifest = _manifest()
    for case in manifest["cases"]:
        asset = case.get("asset")
        if asset is None:
            continue
        if case["modality"] == "audio":
            assert validate_wav(root / asset["fixture"]).frames > 0
        else:
            fixture = tmp_path / f"{case['id']}.png"
            fixture.write_bytes(base64.b64decode(asset["payload_base64"], validate=True))
            image = validate_png(fixture)
            assert image.width > 0 and image.height > 0


def test_live_audio_result_covers_every_audio_case():
    root, manifest = _manifest()
    result = json.loads(
        (root / "docs" / "feedback" / "ASR_SCENARIO_RESULTS.json").read_text(encoding="utf-8")
    )
    audio_cases = {case["id"] for case in manifest["cases"] if case["modality"] == "audio"}
    result_cases = {item["id"] for item in result["results"]}
    assert result["mode"] == "live_local_asr"
    assert result["cases"] == 18
    assert result_cases == audio_cases
    assert all(item["backend"] == "faster-whisper/cpu-int8" for item in result["results"])
    assert all(
        item["live_evidence_status"] == "live_local_asr_scored"
        for item in manifest["cases"]
        if item["modality"] == "audio"
    )


def test_mixed_e2e_result_covers_entire_inventory():
    root, manifest = _manifest()
    result = json.loads(
        (root / "docs" / "feedback" / "MULTIMODAL_SCENARIO_RESULTS.json").read_text(
            encoding="utf-8"
        )
    )
    case_ids = {case["id"] for case in manifest["cases"]}
    result_ids = {item["id"] for item in result["results"]}
    assert result["mode"] == "mixed_local_audio_injected_vision_mock_reasoning"
    assert result["cases"] == result["observations"] == 60
    assert result_ids == case_ids
    assert Counter(item["backend"] for item in result["results"]) == {
        "demo/mock-text": 30,
        "faster-whisper/cpu-int8": 18,
        "fake/replay-vision": 12,
    }
    assert all(item["controller_output_kind"] == "final" for item in result["results"])
    assert all(case["e2e_evidence_status"] == "mixed_e2e_replayed" for case in manifest["cases"])
