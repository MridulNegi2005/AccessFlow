import json
from pathlib import Path

import pytest

from accessflow.perception import validate_wav


def test_held_out_audio_cases_match_declared_provenance():
    root = Path(__file__).parents[2]
    cases = json.loads((root / "docs" / "feedback" / "HELD_OUT_CASES.json").read_text(encoding="utf-8"))["cases"]

    for name, case in cases.items():
        fixture = root / case["fixture"]
        metadata = validate_wav(fixture)

        assert metadata.channels == 1, name
        assert metadata.sample_width == 2, name
        assert metadata.sample_rate == 22_050, name
        assert round(metadata.frames / metadata.sample_rate, 3) == case["duration_s"]

        for pause in case["expected_internal_pauses"]:
            assert 0 <= pause["start_s"] < pause["end_s"] <= case["duration_s"], name
            assert pause["end_s"] - pause["start_s"] == pytest.approx(pause["duration_s"], abs=1 / metadata.sample_rate)



