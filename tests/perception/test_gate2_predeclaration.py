"""Validate fixed Gate 2 development inputs without running any model."""

import base64
import hashlib
import json
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/feedback/GATE2_PREDECLARED_2026-09-25.json"
MATRIX = ROOT / "docs/feedback/SCENARIO_MATRIX.json"


def test_gate2_inputs_are_present_hashed_and_predeclared() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matrix_cases = {
        case["id"]: case
        for case in json.loads(MATRIX.read_text(encoding="utf-8"))["cases"]
    }
    assert manifest["status"] == "NOT_RUN"
    assert [case["id"] for case in manifest["cases"]] == [
        "G2-01", "G2-02", "G2-03", "G2-04"
    ]

    attempt_ids: list[str] = []
    for case in manifest["cases"]:
        assert len(case["attempts"]) == 3
        assert case["reference"] and case["success"]
        attempt_ids.extend(case["attempts"])
        for item in case["inputs"]:
            if item["type"] == "text":
                assert item["value"].strip()
                continue
            if "case_id" in item:
                source = matrix_cases[item["case_id"]]
                assert source["split"] == "development"
                assert item["path"] == "docs/feedback/SCENARIO_MATRIX.json"
                assert item["field"] == "asset.payload_base64"
                payload = base64.b64decode(source["asset"]["payload_base64"], validate=True)
            else:
                path = (ROOT / item["path"]).resolve()
                assert path.is_relative_to(ROOT) and path.is_file()
                payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest().upper() == item["sha256"]
            if item["type"] == "png":
                assert payload.startswith(b"\x89PNG\r\n\x1a\n")
            else:
                assert item["type"] == "wav"
                with wave.open(str(ROOT / item["path"]), "rb") as recording:
                    assert recording.getnchannels() == 1
                    assert recording.getsampwidth() == 2
                    assert recording.getframerate() == 22050
                    assert recording.getnframes() > 0

    assert len(attempt_ids) == len(set(attempt_ids)) == 12
