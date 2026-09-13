import asyncio
import json

import httpx
import jsonschema
import pytest
from pydantic import ValidationError

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.contracts import PlanProposal, SessionView, Snapshot, ToolCall, ToolManifest


async def test_unknown_effect_guidance_uses_ledger_identity_and_manifest_status_tool():
    observed = []
    class Backend:
        async def generate(self, system, data, schema):
            observed.append(data)
            return PlanProposal(clarification="Outcome unknown").model_dump()
    writer = ToolManifest(name="opaque_dispatch", description="Mock write", effect="write",
                          parameters={"type": "object"}, status_tool="opaque_lookup")
    calls = [ToolCall(call_id=f"c-{status}", operation_id=f"op-{status}", tool=writer.name,
                      arguments={}, dependencies={}, effect="write", status=status)
             for status in ("unknown", "cancelled", "success", "failed", "pending")]
    calls.append(ToolCall(call_id="r", operation_id="read-op", tool="opaque_lookup",
                          arguments={}, dependencies={}, effect="read", status="unknown"))
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[], calls=calls)
    await ModelReasoner(Backend()).plan(view, [writer])
    assert observed[0]["required_next_step"]["operations"] == [
        {"operation_id": "op-unknown", "write_tool": "opaque_dispatch", "status_tool": "opaque_lookup"},
        {"operation_id": "op-cancelled", "write_tool": "opaque_dispatch", "status_tool": "opaque_lookup"}]
    assert view.calls == calls
    view.calls = []
    await ModelReasoner(Backend()).plan(view, [writer])
    assert "required_next_step" not in observed[1]


def test_missing_manifest_does_not_invent_a_status_tool():
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[], calls=[
        ToolCall(call_id="c", operation_id="op", tool="missing", arguments={}, dependencies={},
                 effect="write", status="unknown")])
    assert ModelReasoner.reconciliation_context(view, [])[0]["status_tool"] is None


def test_model_generation_requires_explicit_completion_and_action_decisions():
    schema = ModelReasoner.output_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"slot_updates": {"day": "Wednesday"}}, schema)
    complete = {"intent": "appointment", "slot_updates": {"day": "Wednesday"},
                "calls": [{"tool": "unfamiliar_reserve", "arguments": {"day": "Wednesday"},
                           "dependencies": ["day"], "argument_slots": {}}],
                "clarification": None, "response": None,
                "request_complete": True, "write_requested": True}
    jsonschema.validate(complete, schema)
    del complete["calls"][0]["dependencies"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(complete, schema)


def test_model_generation_schema_binds_calls_to_supplied_manifest_names():
    manifest = ToolManifest(name="calendar_lookup_v2", description="Look up availability",
                            effect="read", parameters={"type": "object"})
    schema = ModelReasoner.output_schema([manifest])
    assert schema["$defs"]["ProposedCall"]["properties"]["tool"]["enum"] == [manifest.name]
    valid = {"intent": "availability", "slot_updates": {},
             "calls": [{"tool": manifest.name, "arguments": {}, "dependencies": [],
                        "argument_slots": {}}],
             "clarification": None, "response": None, "request_complete": True,
             "write_requested": False}
    jsonschema.validate(valid, schema)
    valid["calls"][0]["tool"] = "invented_lookup"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(valid, schema)


def test_model_generation_schema_for_no_tools_disallows_calls():
    schema = ModelReasoner.output_schema([])
    assert schema["$defs"]["ProposedCall"]["properties"]["tool"]["enum"] == []
    assert schema["properties"]["calls"]["maxItems"] == 0
    proposal = {"intent": None, "slot_updates": {}, "calls": [], "clarification": None,
                "response": "General information", "request_complete": True,
                "write_requested": False}
    jsonschema.validate(proposal, schema)
    proposal["calls"] = [{"tool": "invented", "arguments": {}, "dependencies": [],
                           "argument_slots": {}}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(proposal, schema)


def test_unresolved_writes_make_model_schema_read_only():
    read = ToolManifest(name="inspect_v2", description="Inspect outcome", effect="read",
                        parameters={"type": "object"})
    write = ToolManifest(name="reserve_v2", description="Reserve item", effect="write",
                         parameters={"type": "object"})
    schema = ModelReasoner.output_schema([read, write], allow_write_calls=False)
    assert schema["$defs"]["ProposedCall"]["properties"]["tool"]["enum"] == [read.name]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"intent": None, "slot_updates": {}, "calls": [
            {"tool": write.name, "arguments": {}, "dependencies": [], "argument_slots": {}}],
            "clarification": None, "response": None, "request_complete": False,
            "write_requested": False}, schema)


async def test_plan_passes_read_only_schema_when_write_outcome_is_unresolved():
    observed = []

    class Backend:
        async def generate(self, system, data, schema):
            observed.append(schema)
            return PlanProposal(clarification="I am checking the outcome").model_dump()

    read = ToolManifest(name="inspect_v2", description="Inspect outcome", effect="read",
                        parameters={"type": "object"})
    write = ToolManifest(name="reserve_v2", description="Reserve item", effect="write",
                         parameters={"type": "object"})
    view = SessionView(
        session_id="s", state=Snapshot(), observations=[], results=[],
        calls=[ToolCall(call_id="c", operation_id="op", tool=write.name, arguments={},
                        dependencies={}, effect="write", status="unknown")])
    await ModelReasoner(Backend()).plan(view, [read, write])
    assert observed[0]["$defs"]["ProposedCall"]["properties"]["tool"]["enum"] == [read.name]


async def test_reasoner_sends_required_decision_schema_without_changing_internal_defaults():
    from accessflow.contracts import PlanProposal

    def handler(request):
        payload = json.loads(request.content)
        schema = payload["format"]
        assert set(schema["required"]) == set(PlanProposal.model_fields)
        grounded_schema = payload["messages"][-1]["content"].split("\nJSON schema:\n")[1]
        assert json.loads(grounded_schema) == schema
        assert "Slot names" in schema["$defs"]["ProposedCall"]["properties"]["dependencies"]["description"]
        assert "same-name slot" in schema["$defs"]["ProposedCall"]["properties"]["argument_slots"]["description"]
        return httpx.Response(200, json={"message": {"content": json.dumps(
            PlanProposal(clarification="Which day?").model_dump())}})

    assert PlanProposal().request_complete is False
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ModelReasoner(JsonBackend(client=client)).plan(
            SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])
        assert result.clarification == "Which day?"


async def test_context_bound_includes_schema_and_system_before_network():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"message": {"content": "{}"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(ValueError, match="Bounded context"):
            await backend.generate("s" * 7000, {}, {"description": "x" * 7000})
        assert not requests
        assert backend.evidence()["outcome_counts"]["failure"] == 1


@pytest.mark.parametrize("layers", [None, "0", "35", "-1"])
async def test_explicit_gpu_profile_is_sent_and_recorded(monkeypatch, layers):
    monkeypatch.delenv("ACCESSFLOW_OLLAMA_NUM_GPU", raising=False)
    if layers is not None:
        monkeypatch.setenv("ACCESSFLOW_OLLAMA_NUM_GPU", layers)
    def handler(request):
        options = json.loads(request.content)["options"]
        if layers is None:
            assert "num_gpu" not in options
        else:
            assert options["num_gpu"] == int(layers)
        return httpx.Response(200, json={"message": {"content": "{}"},
                                      "total_duration": 15, "load_duration": 5,
                                      "prompt_eval_cached_count": 0})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        await backend.generate("", {}, {})
        evidence = backend.evidence()
        assert evidence["config"]["num_gpu"] == (int(layers) if layers is not None else None)
        assert evidence["requests"][0]["load_duration"] == 5
        assert evidence["requests"][0]["total_duration"] == 15


@pytest.mark.parametrize("layers", [-2, True, 1.5, "35"])
def test_invalid_constructor_gpu_profile_rejected(layers):
    with pytest.raises(ValueError, match="num_gpu"):
        JsonBackend(num_gpu=layers)


async def test_ollama_request_uses_explicit_model_and_schema():
    def handler(request):
        assert request.url.path == "/api/chat"
        return httpx.Response(200, json={"message": {"content": '{"response":"Here is general information"}'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reasoner = ModelReasoner(JsonBackend(client=client))
        result = await reasoner.plan(SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])
        assert result.response == "Here is general information"


async def test_malformed_model_plan_rejected():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:
            httpx.Response(200, json={"message": {"content": '{"invented_field":true}'}}))) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(ValidationError):
            await ModelReasoner(backend).plan(
                SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])
    assert backend.evidence()["requests"][0]["outcome"] == "failure"
    assert backend.evidence()["requests"][0]["exception_type"] == "ValidationError"


async def test_quota_failure_not_retried_or_switched(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GEMINI_API_KEY", "unit-test-placeholder-not-a-real-key")
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": "quota"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await JsonBackend("gemini", client).generate("system", {}, {})
    assert len(calls) == 1


async def test_missing_hosted_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_GEMINI_API_KEY", raising=False)
    backend = JsonBackend("gemini")
    with pytest.raises(ValueError, match="KEY"):
        await backend.generate("system", {}, {})
    evidence = backend.evidence()
    assert evidence["request_count"] == 1
    assert evidence["requests"][0]["outcome"] == "failure"
    assert evidence["requests"][0]["exception_type"] == "ValueError"


async def test_ollama_evidence_keeps_safe_metrics_and_reasoner_forwards_it():
    def handler(request):
        return httpx.Response(200, json={
            "message": {"content": '{"response":"Here is general information"}'},
            "prompt_eval_count": 12,
            "prompt_eval_duration": 345678,
            "eval_count": 7,
            "eval_duration": 901234,
            "load_duration": -1,
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        reasoner = ModelReasoner(backend)
        await reasoner.plan(SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])
    evidence = reasoner.evidence()
    assert json.loads(json.dumps(evidence)) == evidence
    assert evidence["backend"] == "ollama"
    assert evidence["model"]
    assert evidence["config"]["request_timeout_seconds"] == 20
    assert evidence["config"]["num_ctx"] == 4096
    assert evidence["config"]["temperature"] == 0
    assert evidence["config"]["ollama_duration_unit"] == "nanoseconds"
    assert evidence["request_count"] == 1
    assert evidence["outcome_counts"] == {"success": 1, "failure": 0, "cancelled": 0}
    record = evidence["requests"][0]
    assert record["outcome"] == "success"
    assert record["prompt_eval_count"] == 12
    assert record["prompt_eval_duration"] == 345678
    assert record["eval_count"] == 7
    assert record["eval_duration"] == 901234
    assert "load_duration" not in record
    assert "total_duration" not in record
    assert "system" not in json.dumps(evidence)
    assert "Here is general information" not in json.dumps(evidence)


def test_ollama_metrics_drop_nonfinite_values():
    assert JsonBackend._ollama_metrics({"eval_count": float("nan"), "eval_duration": float("inf")}) is None


async def test_malformed_json_is_recorded_as_failure():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:
            httpx.Response(200, json={"message": {"content": "not json"}}))) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(json.JSONDecodeError):
            await backend.generate("system", {}, {})
    assert backend.evidence()["requests"][0]["outcome"] == "failure"
    assert backend.evidence()["requests"][0]["exception_type"] == "JSONDecodeError"


async def test_cancellation_is_recorded():
    started = asyncio.Event()

    async def handler(request):
        started.set()
        await asyncio.sleep(60)
        return httpx.Response(200, json={"message": {"content": "{}"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        task = asyncio.create_task(backend.generate("system", {}, {}))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    record = backend.evidence()["requests"][0]
    assert record["outcome"] == "cancelled"
    assert record["exception_type"] == "CancelledError"


async def test_history_omissions_remain_explicit():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:
            httpx.Response(200, json={"message": {"content": "{}"}}))) as client:
        backend = JsonBackend(client=client, history_limit=2)
        for _ in range(3):
            await backend.generate("system", {}, {})
    evidence = backend.evidence()
    assert evidence["request_count"] == 3
    assert evidence["omitted_count"] == 1
    assert evidence["outcome_counts"] == {"success": 3, "failure": 0, "cancelled": 0}
    assert len(evidence["requests"]) == 2


async def test_warmup_requires_ready_true():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:
            httpx.Response(200, json={"message": {"content": '{"ready":false}'}}))) as client:
        backend = JsonBackend(client=client, warmup_timeout=1)
        with pytest.raises(ValueError, match="ready=true"):
            await backend.warmup()


async def test_warmup_timeout_is_per_request_override():
    observed = []

    async def handler(request):
        await asyncio.sleep(0.01)
        return httpx.Response(200, json={"message": {"content": '{"ready":true}'}})

    class RecordingBackend(JsonBackend):
        async def _request(self, client, system, prompt, schema, *, timeout=None):
            observed.append((self.timeout, self.warmup_timeout, timeout))
            return await super()._request(client, system, prompt, schema, timeout=timeout)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = RecordingBackend(client=client, timeout=20, warmup_timeout=0.2)
        await backend.warmup()
    assert backend.timeout == 20
    assert observed == [(20, 0.2, 0.2)]


async def test_groq_request_shape_and_default_json_object(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    monkeypatch.delenv("ACCESSFLOW_GROQ_STRUCTURED", raising=False)
    seen = {}
    def handler(request):
        seen["path"] = request.url.path
        seen["host"] = request.url.host
        seen["auth"] = request.headers.get("Authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {
            "content": '{"response":"Here is general information"}'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reasoner = ModelReasoner(JsonBackend("groq", client))
        result = await reasoner.plan(
            SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])
    assert result.response == "Here is general information"
    assert seen["host"] == "api.groq.com"
    assert seen["path"] == "/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer unit-test-placeholder-not-a-real-key"
    assert seen["body"]["model"] == "llama-3.3-70b-versatile"
    assert seen["body"]["temperature"] == 0
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert [message["role"] for message in seen["body"]["messages"]] == ["system", "user"]


async def test_groq_structured_output_is_opt_in(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    monkeypatch.setenv("ACCESSFLOW_GROQ_STRUCTURED", "1")
    seen = {}
    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ready":true}'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await JsonBackend("groq", client).generate("system", {}, {"type": "object"})
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert seen["body"]["response_format"]["json_schema"]["schema"] == {"type": "object"}


async def test_groq_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_GROQ_API_KEY", raising=False)
    backend = JsonBackend("groq")
    with pytest.raises(ValueError, match="KEY"):
        await backend.generate("system", {}, {})
    evidence = backend.evidence()
    assert evidence["request_count"] == 1
    assert evidence["requests"][0]["exception_type"] == "ValueError"


async def test_groq_quota_failure_not_retried_or_switched(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": "rate_limit_exceeded"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await JsonBackend("groq", client).generate("system", {}, {})
    assert len(calls) == 1


async def test_groq_evidence_keeps_safe_usage_metrics(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    def handler(request):
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"ready":true}'}}],
            "usage": {"queue_time": 0.01, "prompt_tokens": 120, "prompt_time": 0.02,
                      "completion_tokens": 40, "completion_time": 0.08, "total_tokens": 160,
                      "total_time": 0.11, "unexpected": "ignored", "prompt_cost": -1}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend("groq", client)
        await backend.generate("system", {}, {})
    record = backend.evidence()["requests"][0]
    assert record["outcome"] == "success"
    assert record["total_tokens"] == 160 and record["total_time"] == 0.11
    assert "unexpected" not in record and "prompt_cost" not in record


def test_groq_rejects_gpu_placement():
    with pytest.raises(ValueError, match="num_gpu"):
        JsonBackend("groq", num_gpu=35)


def test_unknown_backend_rejected():
    with pytest.raises(ValueError, match="Explicit backend"):
        JsonBackend("openai")


def test_cli_request_timeout_reaches_backend(monkeypatch):
    import sys

    from accessflow import cli
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    captured = {}
    real = cli.JsonBackend
    def spy(backend, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        instance = real(backend, *args, **kwargs)
        async def warmup():
            return {"ready": True}
        instance.warmup = warmup
        return instance
    monkeypatch.setattr(cli, "JsonBackend", spy)
    monkeypatch.setattr(sys, "argv", ["accessflow", "warmup", "--backend", "groq",
                                      "--request-timeout", "45"])
    cli.main()
    assert captured["timeout"] == 45.0


@pytest.mark.parametrize("value", ["0", "-5"])
def test_cli_rejects_non_positive_request_timeout(monkeypatch, value):
    import sys

    from accessflow import cli
    monkeypatch.setattr(sys, "argv", ["accessflow", "warmup", "--backend", "ollama",
                                      "--request-timeout", value])
    with pytest.raises(SystemExit):
        cli.main()


async def test_http_status_failures_record_code_and_bounded_detail(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    body = {"error": {"type": "invalid_request_error", "message": "context too long"}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(400, json=body))) as client:
        backend = JsonBackend("groq", client)
        with pytest.raises(httpx.HTTPStatusError):
            await backend.generate("system", {}, {})
    record = backend.evidence()["requests"][0]
    assert record["status_code"] == 400
    assert record["exception_type"] == "HTTPStatusError"
    assert "invalid_request_error" in record["error_detail"]

    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(429, text="y" * 900))) as client:
        bounded = JsonBackend("groq", client)
        with pytest.raises(httpx.HTTPStatusError):
            await bounded.generate("system", {}, {})
    throttled = bounded.evidence()["requests"][0]
    assert throttled["status_code"] == 429
    assert len(throttled["error_detail"]) == 400


@pytest.mark.parametrize("value,expected", [("0", False), ("false", False), ("1", True), ("true", True)])
async def test_ollama_think_flag_sent_only_when_configured(monkeypatch, value, expected):
    monkeypatch.setenv("ACCESSFLOW_OLLAMA_THINK", value)
    seen = {}
    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"ready":true}'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await JsonBackend("ollama", client).generate("system", {}, {})
    assert seen["body"]["think"] is expected


async def test_ollama_think_absent_by_default(monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_OLLAMA_THINK", raising=False)
    seen = {}
    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": '{"ready":true}'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await JsonBackend("ollama", client).generate("system", {}, {})
    assert "think" not in seen["body"]


def test_outstanding_write_forbids_a_final_response():
    schema = ModelReasoner.output_schema([], allow_final_response=False)
    assert schema["properties"]["response"]["type"] == "null"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"intent": "service", "slot_updates": {}, "calls": [],
                             "clarification": None, "response": "Support notes say book a visit.",
                             "request_complete": True, "write_requested": True}, schema)
    jsonschema.validate({"intent": "service", "slot_updates": {}, "calls": [],
                         "clarification": "Which day suits you?", "response": None,
                         "request_complete": True, "write_requested": True}, schema)


def test_write_outstanding_tracks_dispatched_calls():
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[])
    assert ModelReasoner.write_outstanding(view) is True
    for status in ("pending", "success", "unknown"):
        dispatched = view.model_copy(update={"calls": [ToolCall(
            call_id="c", operation_id="op", tool="reserve", arguments={}, dependencies={},
            effect="write", status=status)]})
        assert ModelReasoner.write_outstanding(dispatched) is False
    read_only = view.model_copy(update={"calls": [ToolCall(
        call_id="r", operation_id="op", tool="inspect", arguments={}, dependencies={},
        effect="read", status="success")]})
    assert ModelReasoner.write_outstanding(read_only) is True


async def test_pending_write_sends_continuation_step_and_null_response_schema():
    seen = {}

    class Backend:
        async def generate(self, system, data, schema):
            seen["data"], seen["schema"] = data, schema
            return PlanProposal(clarification="Which day?").model_dump()

    read = ToolManifest(name="inspect_support_notes", description="Read notes", effect="read",
                        parameters={"type": "object"})
    write = ToolManifest(name="file_visit_request", description="Book visit", effect="write",
                         parameters={"type": "object"})
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[],
                       calls=[ToolCall(call_id="r", operation_id="op", tool=read.name,
                                       arguments={}, dependencies={}, effect="read",
                                       status="success")],
                       write_pending=True)
    await ModelReasoner(Backend()).plan(view, [read, write])
    assert seen["data"]["required_next_step"]["kind"] == "complete_requested_write"
    assert seen["schema"]["properties"]["response"]["type"] == "null"
    # The write tool stays available: this is a continuation, not a read-only turn.
    assert write.name in seen["schema"]["$defs"]["ProposedCall"]["properties"]["tool"]["enum"]


async def test_no_continuation_step_without_a_pending_write():
    seen = {}

    class Backend:
        async def generate(self, system, data, schema):
            seen["data"], seen["schema"] = data, schema
            return PlanProposal(response="Here is general information").model_dump()

    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[])
    assert view.write_pending is False
    await ModelReasoner(Backend()).plan(view, [])
    assert "required_next_step" not in seen["data"]
    # The unconstrained field is str | None, so it is an anyOf rather than a null-only stub.
    assert seen["schema"]["properties"]["response"].get("type") != "null"
    jsonschema.validate({"intent": None, "slot_updates": {}, "calls": [], "clarification": None,
                         "response": "Here is general information", "request_complete": True,
                         "write_requested": False}, seen["schema"])
