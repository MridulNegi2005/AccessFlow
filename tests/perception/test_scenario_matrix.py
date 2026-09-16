import json
from collections import Counter
from pathlib import Path


def _manifest():
    root = Path(__file__).parents[2]
    return root, json.loads((root / "docs" / "feedback" / "SCENARIO_MATRIX.json").read_text(encoding="utf-8"))


def test_scenario_matrix_matches_weighted_inventory():
    _, manifest = _manifest()
    cases = manifest["cases"]

    assert len(cases) == 60
    assert Counter(case["modality"] for case in cases) == {"text": 30, "audio": 18, "image": 12}
    assert Counter(case["split"] for case in cases) == {"development": 40, "held_out": 20}
    assert manifest["status"] == "catalog_only"
    assert all(case["evidence_status"] == "catalog_only" for case in cases)


def test_scenario_matrix_case_metadata_is_unique_and_complete():
    _, manifest = _manifest()

    required = {"id", "modality", "split", "stimulus", "expected_boundary", "evidence_status"}
    assert len({case["id"] for case in manifest["cases"]}) == 60
    assert all(required <= case.keys() for case in manifest["cases"])
    assert all(case["stimulus"] and case["expected_boundary"] for case in manifest["cases"])


def test_existing_audio_assets_in_matrix_have_recorded_files():
    root, manifest = _manifest()
    existing_assets = [
        case["asset"]["fixture"]
        for case in manifest["cases"]
        if case["modality"] == "audio" and case["asset"]["fixture"] is not None
    ]

    assert existing_assets
    assert all((root / fixture).is_file() for fixture in existing_assets)
