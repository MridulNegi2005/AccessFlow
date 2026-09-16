"""R5: evidence() must never leak provider error body content, only bounded, safe diagnostics."""
import json

import httpx
import pytest

from accessflow.adapters.models import JsonBackend


def _evidence_blob(backend):
    """The full evidence() payload, serialized, for a whole-blob leak check."""
    return json.dumps(backend.evidence())


async def _failing_request(monkeypatch, response):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
        backend = JsonBackend("groq", client)
        with pytest.raises(httpx.HTTPStatusError):
            await backend.generate("system", {}, {})
    return backend


async def test_secret_like_marker_in_error_body_never_reaches_evidence(monkeypatch):
    marker = "SYNTHETIC_PRIVATE_USER_TEXT_sk-live-abc123"
    body = {"error": {"type": "invalid_request_error",
                       "message": f"rejected request containing {marker}"}}
    response = httpx.Response(400, json=body)
    backend = await _failing_request(monkeypatch, response)

    assert marker not in _evidence_blob(backend)
    record = backend.evidence()["requests"][0]
    assert "error_detail" not in record
    assert record["status_code"] == 400
    assert record["category"] in {"client_error", "invalid_json"}


async def test_echoed_prompt_text_in_error_body_never_reaches_evidence(monkeypatch):
    echoed_prompt = "the user's home address is 42 Wallaby Way and their PIN is 4471"
    body = {"error": {"type": "invalid_request_error",
                       "message": f"could not process prompt: {echoed_prompt}"}}
    response = httpx.Response(400, json=body)
    backend = await _failing_request(monkeypatch, response)

    assert echoed_prompt not in _evidence_blob(backend)
    assert "Wallaby" not in _evidence_blob(backend)
    record = backend.evidence()["requests"][0]
    assert "error_detail" not in record


async def test_malformed_non_json_response_body_is_handled_safely(monkeypatch):
    raw = "<html>502 Bad Gateway from upstream proxy at 10.0.0.7</html>" * 5
    response = httpx.Response(502, text=raw)
    backend = await _failing_request(monkeypatch, response)

    assert "10.0.0.7" not in _evidence_blob(backend)
    record = backend.evidence()["requests"][0]
    assert "error_detail" not in record
    assert record["status_code"] == 502
    assert record["category"] in {"server_error", "unknown"}


async def test_legitimate_rate_limit_numeric_quota_survives(monkeypatch):
    message = ("Request too large for the model. Please reduce your prompt; or you can "
               "change your request to be smaller. Limit on output tokens per minute "
               "(OTPM): Limit 1000, Requested 1990. For more info, visit docs.")
    body = {"error": {"type": "rate_limit_exceeded", "message": message}}
    response = httpx.Response(400, json=body)
    backend = await _failing_request(monkeypatch, response)

    record = backend.evidence()["requests"][0]
    assert record["category"] in {"rate_limit", "output_limit"}
    assert record["quota"] == {"unit": "OTPM", "limit": 1000, "requested": 1990}
    # the surrounding free text must not survive even though the numbers do
    assert "Please reduce your prompt" not in _evidence_blob(backend)


async def test_truncated_response_records_length_finish_reason(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    monkeypatch.setenv("ACCESSFLOW_MAX_OUTPUT_TOKENS", "16")
    payload = {"choices": [{"message": {"content": '{"intent": "servi'}, "finish_reason": "length"}],
               "usage": {"completion_tokens": 16}}
    response = httpx.Response(200, json=payload)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
        backend = JsonBackend("groq", client)
        with pytest.raises(json.JSONDecodeError):
            await backend.generate("system", {}, {})

    record = backend.evidence()["requests"][0]
    assert record["finish_reason"] == "length"
    assert backend.evidence()["config"]["max_output_tokens"] == "16"

async def test_accumulated_rate_limit_quota_survives_with_used_value():
    """The accumulated shape reports Used between Limit and Requested."""
    message = ("Rate limit reached for model `openai/gpt-oss-120b` in organization `org_x` "
               "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 6667, "
               "Requested 2325. Please try again in 7.4s.")

    def handler(request):
        return httpx.Response(429, json={"error": {"type": "rate_limit_exceeded", "message": message}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(httpx.HTTPStatusError):
            await backend.generate("system", {"a": 1}, {"type": "object"})
        record = backend.evidence()["requests"][0]
        assert record["quota"] == {"unit": "TPM", "limit": 8000, "used": 6667, "requested": 2325}
        assert "Please try again" not in json.dumps(backend.evidence())
