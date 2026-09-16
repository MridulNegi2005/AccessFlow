"""Developer-authored task criteria, kept out of reasoning/perception inputs."""
from typing import Any

from pydantic import Field, model_validator

from accessflow.contracts import Model


class ExpectedEffect(Model):
    tool: str
    arguments: dict[str, Any]


class TaskExpectation(Model):
    slots: dict[str, Any] = Field(default_factory=dict)
    effects: list[ExpectedEffect] | None = None
    require_final: bool = True
    final_basis: str | None = None
    required_error_codes: list[str] = Field(default_factory=list)
    allowed_error_codes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def objective_criteria(self):
        if not self.slots and self.effects is None and self.final_basis is None and not self.required_error_codes:
            raise ValueError("A task oracle needs explicit slot, effect, final-basis or required-error criteria")
        return self


def _select_outcome(outputs, terminal_kind, terminal_code, terminal_cause):
    """Pick the one output event that is this scenario's declared terminal condition.

    A scenario declares what its correct endpoint looks like via `terminal_output`:
    a final answer by default, or something else, such as an unanswered
    clarification. This selects the matching event for that declared kind, so a
    clarification scenario can be scored at all, and so an unrelated turn, a
    stale earlier clarification, or a spurious final response can never be
    selected in its place merely for being the last output. There is no
    fallback to "whatever output came last" and no fallback to a session-end
    snapshot: if nothing matches, there is no outcome, and slot checks read an
    empty dictionary, the same as a stalled or abandoned request.
    """
    if terminal_kind == "final":
        # Existing final-result scenarios keep exactly their original selection:
        # the last final event, regardless of which event caused it.
        finals = [event for event in outputs if event["kind"] == "final"]
        return finals[-1] if finals else None
    matches = [event for event in outputs if event["kind"] == terminal_kind
               and event.get("payload", {}).get("caused_by_event_id") == terminal_cause
               and (terminal_code is None or event.get("payload", {}).get("code") == terminal_code)]
    return matches[-1] if matches else None


def evaluate_task(expectation, rows, effects, manifests=(), completion_status="completed",
                  terminal_output=None, terminal_cause=None):
    """Compare against independent executor state, never attempted tool_call count.

    Effects are matched as an unordered multiset with exact semantic arguments. Only
    the manifest-declared idempotency argument may be omitted by the human oracle.
    This is a labeled mock task outcome, not an official or clinical score.

    `terminal_output` and `terminal_cause` mirror the scenario's own declared terminal
    condition (`Scenario.terminal_output`, and the same predicate `replay.py` uses to
    decide the run is done) and drive which output event's state is read for `slots`
    and `final_basis` -- see `_select_outcome`. Omitting them reproduces the historical
    final-only selection, which existing final-result scenarios keep unchanged.
    """
    if expectation is None:
        return {"passed": None, "checks": [], "reason": "No task expectation supplied"}
    expected = TaskExpectation.model_validate(expectation)
    outputs = [row["event"] for row in rows if row.get("type") == "output"]
    terminal_kind = (terminal_output or {}).get("kind", "final")
    terminal_code = (terminal_output or {}).get("code")
    outcome = _select_outcome(outputs, terminal_kind, terminal_code, terminal_cause)
    checks = []

    def check(name, passed, wanted, actual):
        checks.append({"name": name, "passed": passed, "expected": wanted, "actual": actual})

    check("run_completed", completion_status == "completed", "completed", completion_status)
    if expected.require_final:
        check("final_response", bool(outcome), True, bool(outcome))
    if expected.final_basis is not None:
        actual = outcome.get("payload", {}).get("basis") if outcome else None
        check("final_basis", actual == expected.final_basis, expected.final_basis, actual)
    # The outcome snapshot is the declared terminal event's own state, never a
    # session-end snapshot and never "whatever output happened to come last".
    slots = outcome.get("state", {}).get("slots", {}) if outcome else {}
    for name, value in expected.slots.items():
        slot = slots.get(name)
        actual = slot.get("value") if isinstance(slot, dict) else None
        confirmed = isinstance(slot, dict) and slot.get("confirmed") is True
        check(f"slot:{name}", name in slots and actual == value and confirmed, value,
              {"value": actual, "confirmed": confirmed, "present": name in slots})
    if expected.effects is not None:
        ignored_arguments = {m.name: m.idempotency_parameter for m in manifests}
        actual_effects = []
        for effect in effects.values():
            arguments = dict(effect["arguments"])
            ignored = ignored_arguments.get(effect["tool"])
            if ignored is not None:
                arguments.pop(ignored, None)
            actual_effects.append({"tool": effect["tool"], "arguments": arguments})
        expected_effects = [effect.model_dump() for effect in expected.effects]
        # Full multiset equality: every expected effect must consume one distinct
        # actual effect, and no actual effect may be left over (catches duplicates).
        remaining_actual = actual_effects.copy()
        unmatched_expected = []
        for effect in expected_effects:
            if effect in remaining_actual:
                remaining_actual.remove(effect)
            else:
                unmatched_expected.append(effect)
        matched = not unmatched_expected and not remaining_actual
        check("committed_effects", matched, expected_effects, actual_effects)
    errors = [event.get("payload", {}).get("code") for event in outputs if event["kind"] == "error"]
    for code in expected.required_error_codes:
        check(f"error:{code}", code in errors, "present", "present" if code in errors else "missing")
    allowed = set(expected.allowed_error_codes) | set(expected.required_error_codes)
    unexpected = [code for code in errors if code not in allowed]
    check("unexpected_errors", not unexpected, [], unexpected)
    return {"passed": all(item["passed"] for item in checks), "checks": checks,
            "reason": "Developer-authored mock task oracle; no model receives these expected answers"}
