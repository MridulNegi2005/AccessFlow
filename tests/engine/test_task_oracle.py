import pytest
from pydantic import ValidationError

from accessflow.contracts import ToolManifest
from accessflow.evaluation.oracle import evaluate_task


def final(slots=None, basis="confirmed_tool_effect"):
    return {"type": "output", "event": {"kind": "final", "payload": {"basis": basis},
            "state": {"slots": slots or {"day": {"value": "Wednesday", "confirmed": True}}}}}


def effect(day="Wednesday"):
    return {"tool": "renamed_booking", "arguments": {"day": day}}


def test_correct_slots_do_not_hide_wrong_committed_effect():
    result = evaluate_task({"slots": {"day": "Wednesday"}, "effects": [effect()]},
                           [final()], {"op": effect("Tuesday")})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


def test_duplicate_effect_fails_even_with_identical_final_response():
    assert evaluate_task({"effects": [effect()]}, [final()], {"one": effect(), "two": effect()})["passed"] is False


def test_attempt_is_not_commit_evidence():
    attempted = {"type": "output", "event": {"kind": "tool_call", "payload": effect()}}
    assert evaluate_task({"effects": [effect()]}, [attempted, final()], {})["passed"] is False


def test_only_declared_idempotency_argument_is_ignored():
    manifest = ToolManifest(name="renamed_booking", description="mock", effect="write",
                            parameters={"type": "object", "properties": {"key": {"type": "string"}}},
                            idempotency_parameter="key")
    actual = effect()
    actual["arguments"]["key"] = "generated-operation-id"
    assert evaluate_task({"effects": [effect()]}, [final()], {"op": actual}, [manifest])["passed"] is True
    assert evaluate_task({"effects": [effect()]}, [final()], {"op": actual})["passed"] is False


@pytest.mark.parametrize("slots", [{"day": {"value": "Wednesday", "confirmed": False}}, {}])
def test_unconfirmed_or_missing_slot_fails(slots):
    row = final()
    row["event"]["state"]["slots"] = slots
    assert evaluate_task({"slots": {"day": "Wednesday"}}, [row], {})["passed"] is False


def test_no_expectation_is_unscored_and_timeout_is_not_success():
    assert evaluate_task(None, [final()], {})["passed"] is None
    assert evaluate_task({"effects": []}, [final()], {}, completion_status="timeout")["passed"] is False


def test_empty_oracle_cannot_turn_any_final_into_a_pass():
    with pytest.raises(ValidationError):
        evaluate_task({}, [final()], {})


def test_expected_failure_code_can_be_part_of_successful_safety_scenario():
    row = {"type": "output", "event": {"kind": "error", "payload": {"code": "write_outcome_unknown"}}}
    expected = {"effects": [], "require_final": False, "required_error_codes": ["write_outcome_unknown"]}
    assert evaluate_task(expected, [row], {})["passed"] is True
