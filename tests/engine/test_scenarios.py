import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from accessflow.contracts import Observation, PlanProposal, ProposedCall, SessionView, Snapshot, ToolCall
from accessflow.evaluation.replay import replay
from accessflow.evaluation.scenarios import Scenario, ScriptedStep, StepReasoner, load_scenario
from accessflow.fakes import EventReasoner, FakePerception

ROOT = Path(__file__).resolve().parents[2]
DEV_SCENARIO = ROOT / "scenarios/dev/device_correction_during_write.json"
CLARIFY_FIXTURE = ROOT / "scenarios/live_dev/audio_correction_ambiguous_hour_clarification.json"
CLARIFY_AUDIO = (ROOT / "tests/fixtures/audio/synthetic_pause_correction.wav").resolve()


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


# M1: scenarios/live_dev/audio_correction_ambiguous_hour_clarification.json declares
# a clarification, never a final, as its correct endpoint. These drive the ACTUAL
# committed fixture through real replay() with explicitly labelled fake perception
# and a scripted reasoner -- no ASR, no live model, per the fixture's own provenance.


def _clarify_fixture(tmp_path, timeout=0.3):
    raw = json.loads(CLARIFY_FIXTURE.read_text(encoding="utf-8"))
    raw["completion_timeout_s"] = timeout
    raw["events"][-1]["payload"]["path"] = str(CLARIFY_AUDIO)
    path = tmp_path / "clarify.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


async def _replay_clarify(tmp_path, proposal, timeout=0.3, deliver_observation=True):
    source = _clarify_fixture(tmp_path, timeout)
    definition = load_scenario(source)
    event_id = definition.events[-1].event_id
    observations = [Observation(event_id=event_id, source_id="u1", revision=0, modality="audio",
                                text="Book Tuesday. Actually, Wednesday at five.", final=True,
                                backend="test/injected-audio-observation")] if deliver_observation else []
    perception = FakePerception(scripted={event_id: observations})
    reasoner = EventReasoner({event_id: proposal} if proposal is not None else {})
    trace = tmp_path / "trace.jsonl"
    return await replay(source, trace, reasoner=reasoner, perception=perception)


async def test_clarify_fixture_passes_on_correct_clarification_through_real_replay(tmp_path):
    proposal = PlanProposal(slot_updates={"day": "Wednesday"},
                            clarification="Do you mean five AM or PM?", request_complete=True)
    result = await _replay_clarify(tmp_path, proposal)
    assert result["completion_status"] == "completed"
    assert result["task_oracle"]["passed"] is True
    assert result["mock_effects"] == 0


async def test_clarify_fixture_fails_on_wrong_day_through_real_replay(tmp_path):
    proposal = PlanProposal(slot_updates={"day": "Tuesday"},
                            clarification="Do you mean five AM or PM?", request_complete=True)
    result = await _replay_clarify(tmp_path, proposal)
    assert result["completion_status"] == "completed"
    assert result["task_oracle"]["passed"] is False
    checks = {c["name"]: c["passed"] for c in result["task_oracle"]["checks"]}
    assert checks["slot:day"] is False


async def test_clarify_fixture_fails_on_silence_through_real_replay(tmp_path):
    result = await _replay_clarify(tmp_path, None, timeout=0.2, deliver_observation=False)
    assert result["completion_status"] == "timeout"
    assert result["task_oracle"]["passed"] is False
    rows = [json.loads(line) for line in Path(result["trace"]).read_text().splitlines()]
    kinds = [r["event"]["kind"] for r in rows if r.get("type") == "output"]
    assert "clarify" not in kinds


async def test_clarify_fixture_fails_on_acknowledgement_only_through_real_replay(tmp_path):
    # The engine emits its own "I'll check that." acknowledgement for any complete
    # utterance; an empty proposal that never actually asks the clarifying question
    # must still fail, not be credited for that ambient acknowledgement.
    result = await _replay_clarify(tmp_path, PlanProposal(), timeout=0.2)
    assert result["completion_status"] == "timeout"
    assert result["task_oracle"]["passed"] is False
    rows = [json.loads(line) for line in Path(result["trace"]).read_text().splitlines()]
    kinds = [r["event"]["kind"] for r in rows if r.get("type") == "output"]
    assert "acknowledge" in kinds
    assert "clarify" not in kinds


async def test_clarify_fixture_fails_on_fabricated_final_through_real_replay(tmp_path):
    # A confident final claiming the booking happened, with no tool call at all,
    # must not be accepted just because it exists: the scenario's declared
    # terminal condition is a clarify, so a final is never eligible to stand in.
    proposal = PlanProposal(slot_updates={"day": "Wednesday"}, request_complete=True,
                            response="Booked your Wednesday appointment.")
    result = await _replay_clarify(tmp_path, proposal, timeout=0.2)
    assert result["task_oracle"]["passed"] is False
    checks = {c["name"]: c["passed"] for c in result["task_oracle"]["checks"]}
    assert checks["slot:day"] is False
    assert result["mock_effects"] == 0


async def test_clarify_fixture_fails_on_premature_write_through_real_replay(tmp_path):
    # A controller that guesses the hour and writes anyway must fail the exact
    # zero-effects check even though the day it guessed happens to be right.
    proposal = PlanProposal(
        slot_updates={"day": "Wednesday", "hour": "17:00"}, request_complete=True, write_requested=True,
        calls=[ProposedCall(tool="reserve_service_slot", arguments={"day": "Wednesday", "hour": "17:00"},
                            dependencies=["day", "hour"])])
    result = await _replay_clarify(tmp_path, proposal, timeout=0.3)
    assert result["mock_effects"] == 1
    assert result["task_oracle"]["passed"] is False
    checks = {c["name"]: c["passed"] for c in result["task_oracle"]["checks"]}
    assert checks["committed_effects"] is False


async def test_clarify_fixture_ignores_a_stale_clarification_from_an_earlier_turn(tmp_path):
    # A clarification left over from an earlier, unrelated turn must not be picked
    # as the scored outcome merely because it is the only clarify in the trace.
    # Only one caused by the scenario's own declared (last) event counts.
    raw = json.loads(CLARIFY_FIXTURE.read_text(encoding="utf-8"))
    raw["completion_timeout_s"] = 0.4
    raw["event_gaps_s"] = [0.02, 0.15]
    raw["events"][-1]["payload"]["path"] = str(CLARIFY_AUDIO)
    stale_turn = {"kind": "transcript", "session_id": raw["events"][0]["session_id"],
                 "payload": {"utterance_id": "u0", "revision": 0,
                             "text": "Do you carry the premium warranty plan?", "final": True}}
    raw["events"].insert(1, stale_turn)
    source = tmp_path / "clarify-with-stale-turn.json"
    source.write_text(json.dumps(raw), encoding="utf-8")

    definition = load_scenario(source)
    stale_id, real_id = definition.events[1].event_id, definition.events[2].event_id
    real_observation = Observation(event_id=real_id, source_id="u1", revision=0, modality="audio",
                                   text="Book Tuesday. Actually, Wednesday at five.", final=True,
                                   backend="test/injected-audio-observation")
    # The stale turn's transcript is left unscripted: FakePerception's own
    # text-pass-through synthesizes its Observation, same as any ordinary transcript.
    perception = FakePerception(scripted={real_id: [real_observation]})
    reasoner = EventReasoner({stale_id: PlanProposal(clarification="Standard or express service?",
                                                     request_complete=True),
                              real_id: PlanProposal(request_complete=True)})
    trace = tmp_path / "trace.jsonl"
    result = await replay(source, trace, reasoner=reasoner, perception=perception)

    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    clarifies = [r["event"] for r in rows if r.get("type") == "output" and r["event"]["kind"] == "clarify"]
    assert len(clarifies) == 1
    assert clarifies[0]["payload"]["caused_by_event_id"] == stale_id
    assert result["completion_status"] == "timeout"
    assert result["task_oracle"]["passed"] is False
    checks = {c["name"]: c["passed"] for c in result["task_oracle"]["checks"]}
    assert checks["slot:day"] is False


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
