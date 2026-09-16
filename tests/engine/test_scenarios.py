import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from accessflow.contracts import Observation, SessionView, Snapshot, ToolCall
from accessflow.evaluation.scenarios import Scenario, ScriptedStep, StepReasoner, load_scenario

ROOT = Path(__file__).resolve().parents[2]
DEV_SCENARIO = ROOT / "scenarios/dev/device_correction_during_write.json"


def scenario():
    return {"id": "test-case", "events": [{"kind": "session_start", "session_id": "s", "payload": {}},
            {"kind": "transcript", "session_id": "s", "payload": {
                "utterance_id": "u", "revision": 0, "text": "Book a slot", "final": True}}]}


def test_missing_event_ids_are_stable_across_loads():
    first, second = Scenario.model_validate(scenario()), Scenario.model_validate(scenario())
    assert [e.event_id for e in first.events] == [e.event_id for e in second.events]
    assert first.events[-1].sequence == 1


@pytest.mark.parametrize("mutation", ["session", "id", "duration", "end", "typo"])
def test_invalid_scenarios_fail_before_starting_agent(mutation):
    raw = scenario()
    if mutation == "session":
        raw["events"][1]["session_id"] = "another-session"
    elif mutation == "id":
        raw["id"] = "../../escape"
    elif mutation == "duration":
        raw["completion_timeout_s"] = 110
        raw["event_spacing_s"] = 5
    elif mutation == "end":
        raw["events"].append({"kind": "session_end", "session_id": "s", "payload": {}})
    else:
        raw["expectaton"] = {}
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_event_gaps_default_to_uniform_spacing():
    parsed = Scenario.model_validate({**scenario(), "event_spacing_s": 0.25})
    assert parsed.gaps() == [0.25]


def test_event_gaps_pace_each_pair_independently():
    raw = {**scenario(), "event_gaps_s": [3.5]}
    assert Scenario.model_validate(raw).gaps() == [3.5]


@pytest.mark.parametrize("gaps", [[], [1.0, 1.0], [-1.0], [61.0],
                                   [float("nan")], [float("inf")], [float("-inf")]])
def test_invalid_event_gaps_fail_before_starting_agent(gaps):
    with pytest.raises(ValidationError):
        Scenario.model_validate({**scenario(), "event_gaps_s": gaps})


def test_event_gaps_accept_exact_boundary_values():
    assert Scenario.model_validate({**scenario(), "event_gaps_s": [0.0]}).gaps() == [0.0]
    assert Scenario.model_validate({**scenario(), "event_gaps_s": [60.0]}).gaps() == [60.0]


def test_event_gaps_count_against_the_replay_budget():
    with pytest.raises(ValidationError):
        Scenario.model_validate({**scenario(), "event_gaps_s": [30.0], "completion_timeout_s": 90})


def test_nan_gap_cannot_bypass_the_replay_budget_check():
    # A NaN gap compares False against both `< 0` and `> 60`, so a naive range
    # check alone would let it through; the sum must be checked for finiteness too.
    raw = json.loads(DEV_SCENARIO.read_text(encoding="utf-8"))
    raw["event_gaps_s"] = [float("nan"), 26.0]
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def _audio_scenario_raw(path):
    raw = scenario()
    raw["events"] = [raw["events"][0], {"kind": "audio", "session_id": "s", "payload": {
        "path": path, "utterance_id": "u", "revision": 0}}]
    return raw


def test_load_scenario_resolves_relative_audio_paths_against_scenario_file(tmp_path):
    # A committed scenario's cwd is whatever directory the CLI was invoked from, not
    # the scenario file's own location. The path must not depend on that choice.
    scenario_dir = tmp_path / "nested" / "scenarios"
    scenario_dir.mkdir(parents=True)
    fixture = tmp_path / "fixture.wav"
    fixture.write_bytes(b"not-a-real-wav")
    scenario_path = scenario_dir / "case.json"
    scenario_path.write_text(json.dumps(_audio_scenario_raw("../../fixture.wav")), encoding="utf-8")

    loaded = load_scenario(scenario_path)

    assert loaded.events[1].payload.path == str(fixture.resolve())


def test_load_scenario_resolution_is_independent_of_process_cwd(tmp_path, monkeypatch):
    scenario_dir = tmp_path / "nested" / "scenarios"
    scenario_dir.mkdir(parents=True)
    fixture = tmp_path / "fixture.wav"
    fixture.write_bytes(b"not-a-real-wav")
    scenario_path = scenario_dir / "case.json"
    scenario_path.write_text(json.dumps(_audio_scenario_raw("../../fixture.wav")), encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent if tmp_path.parent.exists() else tmp_path)

    loaded = load_scenario(scenario_path.resolve())

    assert loaded.events[1].payload.path == str(fixture.resolve())


def test_load_scenario_leaves_absolute_audio_paths_unchanged(tmp_path):
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    absolute = str((tmp_path / "elsewhere.wav").resolve())
    scenario_path = scenario_dir / "case.json"
    scenario_path.write_text(json.dumps(_audio_scenario_raw(absolute)), encoding="utf-8")

    loaded = load_scenario(scenario_path)

    assert loaded.events[1].payload.path == absolute


def test_committed_audio_scenario_resolves_to_the_checked_in_fixture():
    loaded = load_scenario(ROOT / "scenarios/live_dev/audio_correction.json")
    audio_event = next(e for e in loaded.events if e.kind == "audio")
    resolved = Path(audio_event.payload.path)
    assert resolved.is_absolute()
    assert resolved == (ROOT / "tests/fixtures/audio/synthetic_pause_correction.wav").resolve()
    assert resolved.is_file()


async def test_step_reasoner_uses_public_call_state_to_resolve_status_query():
    steps = [ScriptedStep(input_event_id="e", after_tools={"renamed_write": "unknown"}, proposal={
        "calls": [{"tool": "renamed_status", "arguments": {"receipt": {"$operation_of": "renamed_write"}}}]
    })]
    view = SessionView(session_id="s", state=Snapshot(), observations=[Observation(event_id="e", source_id="u",
        modality="text", text="request", final=True, backend="test")], results=[], calls=[ToolCall(
            call_id="c", operation_id="op", tool="renamed_write", arguments={}, dependencies={},
            effect="write", status="unknown")])
    plan = await StepReasoner(steps).plan(view, [])
    assert plan.calls[0].arguments == {"receipt": "op"}
    assert steps[0].proposal.calls[0].arguments == {"receipt": {"$operation_of": "renamed_write"}}
