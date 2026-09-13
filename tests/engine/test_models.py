import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.contracts import SessionView, Snapshot


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
