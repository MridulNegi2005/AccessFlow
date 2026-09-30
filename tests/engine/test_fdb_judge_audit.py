"""Offline SDK transport tests, not evidence of live judge or agent performance."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

openai = pytest.importorskip("openai", reason="Install the frozen fdb extra for SDK audit tests")
httpx = pytest.importorskip("httpx")

from scripts import fdb_judge_audit as audit  # noqa: E402


def client_for(body, code=200, requests=None):
    def respond(request):
        if requests is not None:
            requests.append(json.loads(request.content))
        return httpx.Response(code, json=body)

    return openai.OpenAI(api_key="private-dummy-key", max_retries=0,
                         http_client=httpx.Client(transport=httpx.MockTransport(respond)))


def completion(content):
    return {"id": "synthetic", "object": "chat.completion", "created": 0,
            "model": "gpt-4o", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}}


def test_actual_sdk_preserves_request_and_reply_without_recording_content():
    sent, rows = [], []
    content = '{"correct":false,"explanation":"private model response"}'
    client = client_for(completion(content), requests=sent)
    method = audit.observe_requests
    from openai.resources.chat.completions import Completions
    original = Completions.create
    messages = [{"role": "user", "content": "private user input"}]
    with client, method("correctness", rows):
        response = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0, max_tokens=200)
    assert Completions.create is original
    assert response.choices[0].message.content == content
    assert sent == [{"model": "gpt-4o", "messages": messages, "temperature": 0, "max_tokens": 200}]
    assert rows[0]["status"] == "valid_response"  # False judgments are valid, not failures.
    assert rows[0]["total_tokens"] == 20
    assert "private" not in json.dumps(audit.summary(Path("evaluate_tool_calls.py"), rows))


def test_swallowed_auth_error_is_still_visible_and_secrets_are_omitted():
    rows = []
    client = client_for({"error": {"message": "private key/input leak", "type": "authentication_error"}}, 401)
    with client, audit.observe_requests("correctness", rows):
        try:
            client.chat.completions.create(model="gpt-4o", messages=[])
        except openai.AuthenticationError:
            fallback = "exact-match fallback"  # Pinned evaluator catches errors this way.
    assert fallback == "exact-match fallback"
    report = audit.summary(Path("evaluate_tool_calls.py"), rows)
    assert report["status"] == "unverified_failures"
    assert report["failed_requests"] == 1
    assert rows[0]["error_type"] == "AuthenticationError"
    assert "private" not in json.dumps(report)


@pytest.mark.parametrize("content", ["not JSON", "[]", '{"correct":"false","explanation":"x"}',
                                     '{"correct":true}', "", '{"correct":true,"explanation":null}'])
def test_malformed_reply_cannot_be_reported_as_verified_judging(content):
    rows = []
    with client_for(completion(content)) as client, audit.observe_requests("correctness", rows):
        response = client.chat.completions.create(model="gpt-4o", messages=[])
    assert response.choices[0].message.content == content
    assert audit.summary(Path("evaluate_pass_rate.py"), rows)["failed_requests"] == 1


def test_fenced_json_is_accepted_like_the_pinned_judge():
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        content='```json\n{"correct":true,"explanation":"okay"}\n```'))])
    assert audit.valid_reply(response, "correctness")


@pytest.mark.parametrize("invalid", ["2.0", True, float("nan"), float("inf")])
def test_latency_times_require_finite_numbers_or_null(invalid):
    row = {"filler_sentence": "", "key_info_sentence": "answer",
           "filler_start_time": None, "filler_end_time": None,
           "key_info_start_time": invalid, "key_info_end_time": 3.0}
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(row)))])
    assert not audit.valid_reply(response, "latency")
    row["key_info_start_time"] = 2.0
    response.choices[0].message.content = json.dumps(row)
    assert audit.valid_reply(response, "latency")


def test_no_request_never_becomes_verified_judging():
    report = audit.summary(Path("evaluate_pass_rate.py"), [])
    assert report["status"] == "no_requests_observed"
    assert report["observed_requests"] == 0


def test_wrapper_restores_sdk_even_when_the_original_exception_propagates(monkeypatch):
    from openai.resources.chat.completions import Completions
    error = RuntimeError("private error")

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(Completions, "create", fail)
    rows = []
    with pytest.raises(RuntimeError) as caught, audit.observe_requests("correctness", rows):
        Completions.create(None, model="gpt-4o")
    assert caught.value is error
    assert Completions.create is fail
    assert rows[0]["status"] == "request_error"


def test_script_failure_still_persists_an_audit_and_restores_arguments(tmp_path):
    import sys
    script = tmp_path / "evaluate_tool_calls.py"
    script.write_text("import sys\nassert sys.argv[1:] == ['--use-llm']\nraise SystemExit(7)\n")
    output = tmp_path / "audit.json"
    old_argv, old_path = sys.argv[:], sys.path[:]
    with pytest.raises(SystemExit) as caught:
        audit.main(["--script", str(script), "--output", str(output), "--", "--use-llm"])
    assert caught.value.code == 7
    assert sys.argv == old_argv and sys.path == old_path
    assert json.loads(output.read_text())["status"] == "no_requests_observed"
    with pytest.raises(SystemExit):
        audit.main(["--script", str(script), "--output", str(output)])
