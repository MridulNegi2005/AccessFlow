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
