import json
from pathlib import Path

from scripts.scenario_inventory import ROOT, display_path, scenarios

REAL_SCENARIOS = ROOT / "scenarios"


def _definition(scenario_id):
    return {
        "id": scenario_id,
        "events": [
            {"kind": "session_start", "payload": {"tools": [{"name": "toolA"}]}},
            {"kind": "transcript"},
        ],
    }


def _sort_key(rows):
    return sorted((r["id"], r["path"], r["tools"], tuple(r["modalities"])) for r in rows)


def test_relative_scenarios_path_matches_absolute_path(monkeypatch):
    # A relative Path("scenarios") used to hit path.relative_to(ROOT) with a
    # relative `path` against an absolute ROOT and raise ValueError.
    monkeypatch.chdir(ROOT)
    relative_rows = list(scenarios(Path("scenarios")))
    absolute_rows = list(scenarios(REAL_SCENARIOS))

    assert relative_rows
    assert _sort_key(relative_rows) == _sort_key(absolute_rows)


def test_directory_outside_repo_root_uses_absolute_display_path(tmp_path):
    outside = tmp_path / "external_scenarios"
    outside.mkdir()
    (outside / "s1.json").write_text(json.dumps(_definition("outside-scenario")), encoding="utf-8")
    assert not str(outside).startswith(str(ROOT))

    rows = list(scenarios(outside))

    assert len(rows) == 1
    assert rows[0]["id"] == "outside-scenario"
    # Outside ROOT, display_path falls back to an absolute path instead of raising.
    assert Path(rows[0]["path"]).is_absolute()


def test_display_path_matches_model_scoreboard_policy(tmp_path):
    inside = REAL_SCENARIOS / "dev" / "text_correction.json"
    assert display_path(inside) == inside.relative_to(ROOT).as_posix()

    outside = tmp_path / "elsewhere.json"
    assert display_path(outside) == outside.resolve().as_posix()
