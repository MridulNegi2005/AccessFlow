"""A6: profile verification (docs/PROFILES.md) must select the right row, export the
values the docs promise, and never re-read a mutable env var after construction."""
import json

import httpx
import pytest

from accessflow.adapters.models import (JsonBackend, ModelReasoner,
                                        missing_promised_config, validate_reasoner_evidence)
from accessflow.contracts import PlanProposal, SessionView, Snapshot
from accessflow.evaluation.replay import load_run_metadata, replay

from pathlib import Path

SCENARIO = Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json"


def _clear_accessflow_env(monkeypatch):
    import os
    for key in list(os.environ):
        if key.startswith("ACCESSFLOW_"):
            monkeypatch.delenv(key, raising=False)


# --- A6.1: run_metadata row selection -------------------------------------------------

async def test_load_run_metadata_selects_the_metadata_row_not_the_last_row(tmp_path):
    trace = tmp_path / "trace.jsonl"
    await replay(SCENARIO, str(trace))
    rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
    assert rows[0]["type"] == "run_metadata"
    assert rows[-1]["type"] != "run_metadata"  # confirms [-1] would pick the wrong row
    metadata = load_run_metadata(str(trace))
    assert metadata["type"] == "run_metadata"
    assert metadata is rows[0] or metadata == rows[0]


def test_load_run_metadata_raises_a_clear_error_when_absent(tmp_path):
    trace = tmp_path / "no-metadata.jsonl"
    trace.write_text(json.dumps({"type": "output", "event": {}}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="found 0"):
        load_run_metadata(str(trace))


def test_load_run_metadata_raises_a_clear_error_when_duplicated(tmp_path):
    trace = tmp_path / "dup-metadata.jsonl"
    row = json.dumps({"type": "run_metadata"})
    trace.write_text(row + "\n" + row + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="found 2"):
        load_run_metadata(str(trace))


# --- A6.2: exported reasoner configuration ---------------------------------------------

async def test_offline_fake_run_has_no_reasoner_evidence_and_validator_says_so(tmp_path):
    trace = tmp_path / "trace.jsonl"
    await replay(SCENARIO, str(trace))
    metadata = load_run_metadata(str(trace))
    assert metadata["reasoner_evidence"] is None
    with pytest.raises(ValueError, match="reasoner_evidence is null"):
        validate_reasoner_evidence(metadata["reasoner_evidence"])


@pytest.mark.parametrize("backend,default_endpoint", [
    ("groq", "https://api.groq.com/openai/v1/chat/completions"),
    ("nvidia", "https://integrate.api.nvidia.com/v1/chat/completions"),
    ("ollama", "http://localhost:11434/api/chat"),
])
def test_evidence_exports_a_resolved_endpoint_with_no_credentials_or_query(
        monkeypatch, backend, default_endpoint):
    _clear_accessflow_env(monkeypatch)
    evidence = JsonBackend(backend).evidence()
    assert evidence["config"]["endpoint"] == default_endpoint
    validate_reasoner_evidence(evidence)


def test_evidence_endpoint_is_sanitized_of_credentials_and_query_string(monkeypatch):
    _clear_accessflow_env(monkeypatch)
    monkeypatch.setenv("ACCESSFLOW_GROQ_URL", "https://user:secret-key@my-proxy:8443/v1?api_key=abc123")
    evidence = JsonBackend("groq").evidence()
    endpoint = evidence["config"]["endpoint"]
    assert endpoint == "https://my-proxy:8443/v1/chat/completions"
    assert "secret-key" not in endpoint
    assert "abc123" not in endpoint


def test_max_output_tokens_is_resolved_once_and_not_reread_at_export(monkeypatch):
    _clear_accessflow_env(monkeypatch)
    backend = JsonBackend("groq")
    assert backend.evidence()["config"]["max_output_tokens"] is None
    # A later, mutable env change must not retroactively change already-resolved evidence.
    monkeypatch.setenv("ACCESSFLOW_MAX_OUTPUT_TOKENS", "950")
    assert backend.evidence()["config"]["max_output_tokens"] is None

    monkeypatch.setenv("ACCESSFLOW_MAX_OUTPUT_TOKENS", "111")
    pinned = JsonBackend("groq")
    monkeypatch.setenv("ACCESSFLOW_MAX_OUTPUT_TOKENS", "222")
    assert pinned.evidence()["config"]["max_output_tokens"] == "111"


def test_endpoint_is_resolved_once_and_not_reread_at_request_time(monkeypatch):
    _clear_accessflow_env(monkeypatch)
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    monkeypatch.setenv("ACCESSFLOW_GROQ_URL", "https://original-host.example/v1")
    backend = JsonBackend("groq")
    # Mutate the env after construction; a live re-read would send the request elsewhere.
    monkeypatch.setenv("ACCESSFLOW_GROQ_URL", "https://different-host.example/v1")
    seen = {}
    def handler(request):
        seen["host"] = request.url.host
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            backend.client = client
            await backend.generate("system", {}, {})
    import asyncio
    asyncio.run(run())
    assert seen["host"] == "original-host.example"
    assert backend.evidence()["config"]["endpoint"] == "https://original-host.example/v1/chat/completions"


async def test_full_profile_evidence_matches_hosted_qwen_profile_with_mock_transport(monkeypatch):
    """Reproduces docs/PROFILES.md's hosted-qwen profile end to end against a cleared
    environment and a mock HTTP transport -- no live key, no network."""
    _clear_accessflow_env(monkeypatch)
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "unit-test-placeholder-not-a-real-key")
    monkeypatch.setenv("ACCESSFLOW_GROQ_MODEL", "qwen/qwen3.8-27b")
    monkeypatch.setenv("ACCESSFLOW_GROQ_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("ACCESSFLOW_MAX_OUTPUT_TOKENS", "950")

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(
            PlanProposal(response="ok").model_dump())}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        reasoner = ModelReasoner(JsonBackend("groq", client=client, timeout=30))
        await reasoner.plan(SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [])

    evidence = validate_reasoner_evidence(reasoner.evidence())
    assert evidence["backend"] == "groq"
    assert evidence["model"] == "qwen/qwen3.8-27b"
    assert evidence["config"]["endpoint"] == "https://api.groq.com/openai/v1/chat/completions"
    assert evidence["config"]["max_output_tokens"] == "950"
    assert evidence["config"]["request_timeout_seconds"] == 30


def test_validate_reasoner_evidence_rejects_evidence_missing_the_promised_endpoint():
    incomplete = {"backend": "groq", "model": "qwen/qwen3.8-27b",
                  "config": {"max_output_tokens": "950", "request_timeout_seconds": 30,
                             "warmup_timeout_seconds": 290}}
    with pytest.raises(ValueError, match="endpoint"):
        validate_reasoner_evidence(incomplete)


def test_validate_reasoner_evidence_accepts_a_profile_with_no_output_cap():
    complete = {"backend": "ollama", "model": "qwen3:4b",
                "config": {"endpoint": "http://localhost:11434/api/chat", "max_output_tokens": None,
                          "request_timeout_seconds": 20, "warmup_timeout_seconds": 290}}
    assert validate_reasoner_evidence(complete) is complete


# --- distinction: controller inference deadline vs HTTP request deadline ---------------

async def test_controller_inference_deadline_is_recorded_independently_of_http_timeout(tmp_path):
    """A controller deadline shorter than the backend's HTTP timeout is valid and must be
    exported as its own field, not conflated with (or flagged against) request_timeout_seconds."""
    trace = tmp_path / "trace.jsonl"
    await replay(SCENARIO, str(trace), inference_timeout=1)
    metadata = load_run_metadata(str(trace))
    assert metadata["config"]["inference_timeout_s"] == 1


def test_legacy_trace_names_absent_fields_instead_of_a_bare_schema_error():
    # No trace recorded on or before 15 September 2026 carries an endpoint, and most
    # carry no output cap. Verification must say which values it cannot confirm.
    legacy = {"backend": "groq", "model": "openai/gpt-oss-120b",
              "config": {"request_timeout_seconds": 30.0, "warmup_timeout_seconds": 290}}
    with pytest.raises(ValueError) as caught:
        validate_reasoner_evidence(legacy)
    assert "endpoint" in str(caught.value) and "max_output_tokens" in str(caught.value)
    assert missing_promised_config(legacy) == ["endpoint", "max_output_tokens"]
    assert validate_reasoner_evidence(legacy, strict=False) is legacy


def test_a_committed_trace_verifies_without_the_endpoint():
    # The evidence bundle is committed; artifacts/ is gitignored, so a clean clone has
    # nothing there. Read the bundle so this acceptance check runs on a fresh checkout.
    bundle = Path(__file__).resolve().parents[2] / "docs/evidence/model-comparison-2026-09-15/traces"
    traces = sorted(bundle.glob("**/*.jsonl"))
    for path in traces:
        metadata = None
        try:
            metadata = load_run_metadata(path)
        except (ValueError, OSError):
            continue
        evidence = metadata.get("reasoner_evidence")
        if not evidence:
            continue
        assert validate_reasoner_evidence(evidence, strict=False) is evidence
        assert "endpoint" in missing_promised_config(evidence)
        return
    pytest.fail("the committed evidence bundle carries no reasoner_evidence")


def test_a_complete_current_config_still_passes_strictly():
    current = {"backend": "groq", "model": "qwen/qwen3.8-27b",
               "config": {"endpoint": "https://api.groq.com/openai/v1/chat/completions",
                          "max_output_tokens": "950", "request_timeout_seconds": 30.0,
                          "warmup_timeout_seconds": 290}}
    assert validate_reasoner_evidence(current) is current
    assert missing_promised_config(current) == []
