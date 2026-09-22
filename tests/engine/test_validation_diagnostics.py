import json

import httpx
import pytest
from jsonschema import Draft202012Validator
from jsonschema import ValidationError as SchemaValidationError
from pydantic import ValidationError as ModelValidationError
from pydantic_core import PydanticCustomError

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.contracts import PlanProposal
from accessflow.validation_diagnostics import validation_summary

SECRET = "credential-bearer-private-input"


def test_pydantic_summary_redacts_values_extra_keys_and_dynamic_contract_names():
    with pytest.raises(ModelValidationError) as caught:
        PlanProposal.model_validate({
            "calls": [{"tool": SECRET, "arguments": {}, SECRET: SECRET}],
            "write_contracts": [{"tool": SECRET, "delegated_arguments": {
                SECRET: {"slot": SECRET, "source_call_index": SECRET,
                         "collection_pointer": SECRET, "value_pointer": SECRET,
                         "match_slots": {SECRET: {SECRET: SECRET}}}}}],
        })
    summary = validation_summary(caught.value)
    assert SECRET not in json.dumps(summary)
    errors = summary["errors"]
    assert {"category": "extra", "path": ["calls", 0, "<key>"]} in errors
    assert {"category": "type", "path": ["write_contracts", 0,
            "delegated_arguments", "<key>", "source_call_index"]} in errors
    assert {"category": "type", "path": ["write_contracts", 0,
            "delegated_arguments", "<key>", "match_slots", "<key>"]} in errors


def test_pydantic_missing_field_and_model_validator_are_distinguished():
    with pytest.raises(ModelValidationError) as caught:
        PlanProposal.model_validate({"calls": [{"arguments": {}}], "write_contracts": [
            {"tool": SECRET, "delegated_arguments": {SECRET: {
                "slot": SECRET, "collection_pointer": SECRET,
                "value_pointer": SECRET, "match_slots": {"/id": SECRET}}}}]})
    errors = validation_summary(caught.value)["errors"]
    assert {"category": "missing", "path": ["calls", 0, "tool"],
            "missing_field": "tool"} in errors
    assert {"category": "value_error", "path": ["write_contracts", 0,
            "delegated_arguments", "<key>"]} in errors


def test_pydantic_custom_error_code_message_context_input_and_title_are_not_exported():
    error = ModelValidationError.from_exception_data(SECRET, [{
        "type": PydanticCustomError(SECRET, SECRET + " {secret}", {"secret": SECRET}),
        "loc": ("calls", 0, "arguments", "tool", SECRET), "input": SECRET}])
    summary = validation_summary(error)
    assert summary["errors"] == [{"category": "validation", "path": [
        "calls", 0, "arguments", "<key>", "<key>"]}]
    assert SECRET not in json.dumps(summary)


def test_integer_map_keys_are_not_mistaken_for_array_indices():
    error = ModelValidationError.from_exception_data("PlanProposal", [{
        "type": "string_type", "loc": ("slot_updates", 12345, "[key]"), "input": 12345}])
    assert validation_summary(error)["errors"] == [
        {"category": "type", "path": ["slot_updates", "<key>", "<key>"]}]


def test_error_count_path_length_and_numeric_indices_are_bounded():
    error = ModelValidationError.from_exception_data("PlanProposal", [
        {"type": "missing", "loc": ("calls", index, "arguments") + (SECRET,) * 24,
         "input": SECRET} for index in [0, -1, 1_000_001] + list(range(9))])
    summary = validation_summary(error)
    assert summary["error_count"] == 12
    assert summary["truncated"] is True
    assert len(summary["errors"]) == 8
    assert all(len(item["path"]) == 16 and item["path_truncated"]
               for item in summary["errors"])
    assert summary["errors"][0]["path"][1] == 0
    assert summary["errors"][1]["path"][1] == "<index>"
    assert summary["errors"][2]["path"][1] == "<index>"
    assert SECRET not in json.dumps(summary)


def test_schema_required_names_come_only_from_internal_contract():
    schema = {"type": "object", "required": ["calls", SECRET],
              "properties": {SECRET: {"type": "string"}}}
    error = next(Draft202012Validator(schema).iter_errors({SECRET + "-key": SECRET}))
    summary = validation_summary(error)
    assert summary["errors"] == [
        {"category": "required", "path": [], "missing_fields": ["calls"]}]
    assert SECRET not in json.dumps(summary)


def test_schema_required_dynamic_property_that_matches_internal_name_stays_redacted():
    error = SchemaValidationError(SECRET, validator="required", validator_value=["tool"],
                                  path=["calls", 0, "arguments"], instance={},
                                  schema={"properties": {"tool": {}}})
    assert validation_summary(error)["errors"] == [
        {"category": "required", "path": ["calls", 0, "arguments"]}]


@pytest.mark.parametrize("validator, category", [("type", "type"), ("enum", "enum"),
                                                ("maxItems", "constraint"),
                                                (SECRET, "validation")])
def test_schema_messages_context_and_dynamic_keys_are_never_exported(validator, category):
    error = SchemaValidationError(SECRET, validator=validator, validator_value=SECRET,
                                  path=["write_contracts", 0, "delegated_arguments",
                                        "tool", "match_slots", SECRET],
                                  instance=SECRET, schema={SECRET: SECRET},
                                  context=[SchemaValidationError(SECRET)])
    summary = validation_summary(error)
    assert summary["errors"] == [{"category": category, "path": [
        "write_contracts", 0, "delegated_arguments", "<key>", "match_slots", "<key>"]}]
    assert SECRET not in json.dumps(summary)


def test_schema_long_paths_are_bounded_without_misidentifying_missing_fields():
    error = SchemaValidationError(SECRET, validator="required", validator_value=["tool"],
                                  path=["calls", 1_000_001] + [SECRET] * 20,
                                  instance={})
    item = validation_summary(error)["errors"][0]
    assert len(item["path"]) == 16
    assert item["path"][1] == "<index>"
    assert item["path_truncated"] is True
    assert "missing_fields" not in item


def test_unrecognized_exception_has_no_summary():
    error = ValueError(SECRET)
    assert validation_summary(error) is None
    backend = JsonBackend()
    backend._record_request(0, "failure", error)
    assert "validation_summary" not in backend.evidence()["requests"][0]
    assert SECRET not in json.dumps(backend.evidence())


@pytest.mark.parametrize("validation", ["pydantic", "jsonschema"])
@pytest.mark.parametrize("backend_kind", ["ollama", "groq"])
async def test_validation_failures_keep_provider_timings_and_only_safe_diagnostics(
        validation, backend_kind, monkeypatch):
    result = {"calls": [{"arguments": {SECRET: SECRET}}]} if validation == "pydantic" else {}
    if backend_kind == "ollama":
        metrics = {"total_duration": 120, "load_duration": 10, "prompt_eval_duration": 30,
                   "eval_duration": 80, "eval_count": 20}
    else:
        monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", SECRET)
        metrics = {"queue_time": 0.1, "prompt_time": 0.2, "completion_time": 0.4,
                   "total_time": 0.7, "prompt_tokens": 40, "completion_tokens": 20}

    def handler(request):
        if backend_kind == "groq":
            return httpx.Response(200, json={"choices": [
                {"message": {"content": json.dumps(result)}, "finish_reason": "stop"}],
                "usage": metrics})
        return httpx.Response(200, json={"message": {"content": json.dumps(result)},
                                        **metrics})

    def validate(value):
        PlanProposal.model_validate(value)
        Draft202012Validator(ModelReasoner.output_schema()).validate(value)

    exception_type = ModelValidationError if validation == "pydantic" else SchemaValidationError
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(backend=backend_kind, client=client)
        with pytest.raises(exception_type):
            await backend.generate("test", {}, {}, _validator=validate)
    evidence = backend.evidence()
    record = evidence["requests"][0]
    assert record["outcome"] == "failure"
    assert record["exception_type"] == "ValidationError"
    assert record["elapsed_seconds"] >= 0
    assert record["validation_summary"]["source"] == validation
    assert all(record[key] == value for key, value in metrics.items())
    assert evidence["outcome_counts"] == {"success": 0, "failure": 1, "cancelled": 0}
    assert SECRET not in json.dumps(evidence)
    assert backend.local_only_raw_errors() == []
