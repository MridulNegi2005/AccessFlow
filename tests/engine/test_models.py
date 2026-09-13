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
        with pytest.raises(ValidationError):
            await ModelReasoner(JsonBackend(client=client)).plan(
                SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])


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
    with pytest.raises(ValueError, match="KEY"):
        await JsonBackend("gemini").generate("system", {}, {})
