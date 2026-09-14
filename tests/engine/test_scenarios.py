import pytest
from pydantic import ValidationError

from accessflow.contracts import Observation, SessionView, Snapshot, ToolCall
from accessflow.evaluation.scenarios import Scenario, ScriptedStep, StepReasoner


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


@pytest.mark.parametrize("gaps", [[], [1.0, 1.0], [-1.0], [61.0]])
def test_invalid_event_gaps_fail_before_starting_agent(gaps):
    with pytest.raises(ValidationError):
        Scenario.model_validate({**scenario(), "event_gaps_s": gaps})


def test_event_gaps_count_against_the_replay_budget():
    with pytest.raises(ValidationError):
        Scenario.model_validate({**scenario(), "event_gaps_s": [30.0], "completion_timeout_s": 90})


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
