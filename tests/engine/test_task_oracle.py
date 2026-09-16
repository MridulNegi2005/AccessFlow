import pytest
from pydantic import ValidationError

from accessflow.contracts import ToolCall, ToolManifest
from accessflow.evaluation.mock_environment import MockEnvironment, WriteConfig
from accessflow.evaluation.oracle import evaluate_task


def final(slots=None, basis="confirmed_tool_effect"):
    return {"type": "output", "event": {"kind": "final", "payload": {"basis": basis},
            "state": {"slots": slots or {"day": {"value": "Wednesday", "confirmed": True}}}}}


def effect(day="Wednesday"):
    return {"tool": "renamed_booking", "arguments": {"day": day}}


def booking(day="Wednesday", hour="17:00"):
    return {"tool": "reserve_service_slot", "arguments": {"day": day, "hour": hour}}


def slot_manifest():
    return ToolManifest(name="reserve_service_slot", description="mock", effect="write",
                        parameters={"type": "object",
                                    "properties": {"day": {"type": "string"}, "hour": {"type": "string"}},
                                    "required": ["day", "hour"], "additionalProperties": False})


def write_call(call_id, operation_id, day="Wednesday", hour="17:00"):
    return ToolCall(call_id=call_id, operation_id=operation_id, tool="reserve_service_slot",
                    arguments={"day": day, "hour": hour}, dependencies={}, effect="write")


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


# Acceptance check 1: zero effects when one was expected.
def test_zero_effects_fails_when_one_expected():
    result = evaluate_task({"effects": [booking()]}, [final()], {})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 2: duplicate effects fail, proven against the real MockEnvironment.
#
# Finding: MockEnvironment.execute keys the write ledger (self._effects, see
# _execute_write in src/accessflow/evaluation/mock_environment.py) by call.operation_id,
# not by the scenario's declared identity_fields. identity_fields only feed a
# missing-argument check and the same-operation_id conflict check; they never
# collapse two different operation_ids into one ledger entry. So two independent
# writes to the same day/hour, issued under distinct operation ids, commit as two
# separate entries and evaluate_task's multiset count check sees both. Verified
# empirically below, not assumed.
async def test_duplicate_write_under_different_operation_ids_is_not_collapsed_and_fails():
    env = MockEnvironment([slot_manifest()],
                          {"reserve_service_slot": WriteConfig(identity_fields=("day", "hour"))})
    first = await env.execute(write_call("c1", "op-1"))
    second = await env.execute(write_call("c2", "op-2"))
    assert first.status == second.status == "success"
    assert len(env.effects) == 2, "duplicate writes under distinct operation ids were collapsed"

    result = evaluate_task({"effects": [booking()]}, [final()], env.effects)

    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 3: Tuesday instead of Wednesday fails.
def test_wrong_day_fails():
    result = evaluate_task({"effects": [booking("Wednesday", "17:00")]}, [final()],
                           {"op": booking("Tuesday", "17:00")})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 4: the wrong hour fails.
def test_wrong_hour_fails():
    result = evaluate_task({"effects": [booking("Wednesday", "17:00")]}, [final()],
                           {"op": booking("Wednesday", "03:00")})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 5: a premature write fails when zero effects were expected.
def test_premature_write_fails_when_no_effects_expected():
    result = evaluate_task({"effects": [], "require_final": False}, [], {"op": booking()})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 6: a fabricated final claim with no backing effect fails.
def test_fabricated_final_claim_with_no_backing_effect_fails():
    result = evaluate_task({"effects": [booking()], "final_basis": "confirmed_tool_effect"},
                           [final(basis="confirmed_tool_effect")], {})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


# Acceptance check 7: a correctly clarified request with exactly one confirmed
# effect passes.
def test_correctly_confirmed_single_effect_passes():
    result = evaluate_task(
        {"slots": {"day": "Wednesday"}, "effects": [booking("Wednesday", "17:00")],
         "final_basis": "confirmed_tool_effect"},
        [final(basis="confirmed_tool_effect")], {"op": booking("Wednesday", "17:00")})
    assert result["passed"] is True


# M1: a scenario whose declared terminal condition is a clarification (never a
# final) must be scored from that clarification's own state, not from an empty
# dictionary and not from any final that happens to exist.


def clarify(caused_by="ev1", slots=None, text="Do you mean five AM or PM?"):
    return {"type": "output", "event": {"kind": "clarify",
            "payload": {"caused_by_event_id": caused_by, "text": text},
            "state": {"slots": slots or {"day": {"value": "Wednesday", "confirmed": True}}}}}


CLARIFY_EXPECTATION = {"slots": {"day": "Wednesday"}, "effects": [], "require_final": False}


def test_correct_clarification_passes_via_terminal_output_selection():
    result = evaluate_task(CLARIFY_EXPECTATION, [clarify()], {},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is True


def test_clarify_expectation_without_terminal_output_reads_empty_slots_not_success():
    # This is the original defect: no terminal_output means the selector still only
    # knows how to look at finals, so a real clarify snapshot is invisible to it.
    result = evaluate_task(CLARIFY_EXPECTATION, [clarify()], {})
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "slot:day")["passed"] is False


def test_clarification_from_a_different_causing_event_is_not_selected():
    # A stale/irrelevant clarification left over from an earlier, unrelated turn
    # must not be picked just because it is a clarify event that exists somewhere
    # in the trace. Only one caused by the scenario's declared event counts.
    result = evaluate_task(CLARIFY_EXPECTATION, [clarify(caused_by="stale-ev")], {},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    check = next(c for c in result["checks"] if c["name"] == "slot:day")
    assert check["passed"] is False
    assert check["actual"]["present"] is False


def test_clarification_with_wrong_day_fails():
    result = evaluate_task(CLARIFY_EXPECTATION,
                           [clarify(slots={"day": {"value": "Tuesday", "confirmed": True}})], {},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "slot:day")["passed"] is False


def test_unconfirmed_day_in_clarification_fails():
    result = evaluate_task(CLARIFY_EXPECTATION,
                           [clarify(slots={"day": {"value": "Wednesday", "confirmed": False}})], {},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "slot:day")["passed"] is False


def test_a_final_cannot_stand_in_for_the_declared_clarification_outcome():
    # A final claiming a booking never happened must not pass just because it is
    # the last output in the trace: the declared terminal kind is "clarify", so a
    # final is never eligible to be selected as the outcome snapshot.
    result = evaluate_task(CLARIFY_EXPECTATION, [final()], {},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    check = next(c for c in result["checks"] if c["name"] == "slot:day")
    assert check["passed"] is False and check["actual"]["present"] is False


def test_premature_write_still_fails_a_clarification_scenario():
    result = evaluate_task(CLARIFY_EXPECTATION, [clarify()], {"op": booking()},
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "committed_effects")["passed"] is False


def test_silence_is_not_success_for_a_clarification_scenario():
    result = evaluate_task(CLARIFY_EXPECTATION, [], {}, completion_status="timeout",
                           terminal_output={"kind": "clarify"}, terminal_cause="ev1")
    assert result["passed"] is False
    assert next(c for c in result["checks"] if c["name"] == "run_completed")["passed"] is False


def test_final_kind_selection_is_unchanged_when_multiple_finals_exist():
    # Existing final-result scenarios must keep exactly their historical selection:
    # the last final event, regardless of which event caused it. This guards that
    # adding terminal-condition selection for clarify never touches this path.
    early = final(slots={"day": {"value": "Tuesday", "confirmed": True}})
    early["event"]["payload"] = {"caused_by_event_id": "irrelevant"}
    late = final(slots={"day": {"value": "Wednesday", "confirmed": True}})
    late["event"]["payload"] = {"caused_by_event_id": "ev1"}
    expectation = {"slots": {"day": "Wednesday"}, "effects": []}
    assert evaluate_task(expectation, [early, late], {})["passed"] is True
    assert evaluate_task(expectation, [early, late], {},
                         terminal_output={"kind": "final"}, terminal_cause="ev1")["passed"] is True
