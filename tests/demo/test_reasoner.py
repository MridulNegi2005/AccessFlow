import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from accessflow.contracts import Observation, SessionView, Snapshot


demo_path = Path(__file__).parents[2] / "demo" / "app.py"
spec = importlib.util.spec_from_file_location("accessflow_demo_reasoner_app", demo_path)
assert spec and spec.loader
demo_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_app)
MAX_REASONER_CONTEXT_CHARS = demo_app.MAX_REASONER_CONTEXT_CHARS
OllamaReasoner = demo_app.OllamaReasoner


class FakeResponse:
    def __init__(self, body):
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


def _view(text="Book Wednesday"):
    return SessionView(
        session_id="reasoner-session",
        state=Snapshot(),
        observations=[
            Observation(
                event_id="event-1",
                source_id="utterance-1",
                modality="text",
                text=text,
                final=True,
                backend="test",
            )
        ],
        results=[],
    )


@pytest.mark.asyncio
async def test_ollama_reasoner_posts_bounded_context_and_parses_plan():
    seen = {}

    def opener(request, *, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "response": json.dumps(
                    {
                        "response": "I can clarify the day.",
                        "clarification": "Which Wednesday time should I use?",
                        "request_complete": False,
                    }
                )
            }
        )

    reasoner = OllamaReasoner(
        model="gemma3:4b",
        endpoint="http://127.0.0.1:11434/api/generate",
        timeout_s=7,
        opener=opener,
    )
    proposal = await reasoner.plan(_view(), [])

    assert proposal.response == "I can clarify the day."
    assert proposal.clarification == "Which Wednesday time should I use?"
    assert proposal.request_complete is False
    assert reasoner.backend_name == "ollama/gemma3:4b"
    assert seen["url"].endswith("/api/generate")
    assert seen["timeout"] == 7
    assert seen["body"]["model"] == "gemma3:4b"
    assert seen["body"]["stream"] is False
    assert seen["body"]["format"] == "json"
    assert "Book Wednesday" in seen["body"]["prompt"]
    assert len(seen["body"]["prompt"]) <= MAX_REASONER_CONTEXT_CHARS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"{not-json", "invalid JSON"),
        ({"response": "not-json"}, "invalid plan JSON"),
        ({"response": json.dumps([])}, "invalid plan shape"),
        ({"response": json.dumps({"request_complete": "yes"})}, "invalid plan proposal"),
    ],
)
async def test_ollama_reasoner_classifies_malformed_plans(body, message):
    reasoner = OllamaReasoner(opener=lambda request, timeout: FakeResponse(body))

    with pytest.raises(RuntimeError, match=message):
        await reasoner.plan(_view(), [])


@pytest.mark.asyncio
async def test_ollama_reasoner_response_bound_is_enforced():
    body = b"x" * (demo_app.MAX_REASONER_RESPONSE_BYTES + 1)
    reasoner = OllamaReasoner(opener=lambda request, timeout: FakeResponse(body))

    with pytest.raises(RuntimeError, match="response is too large"):
        await reasoner.plan(_view(), [])


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": " "}, "model cannot be empty"),
        ({"endpoint": " "}, "endpoint cannot be empty"),
        ({"endpoint": "https://example.com/api/generate"}, "endpoint must use a loopback host"),
        ({"timeout_s": 0}, "timeout_s must be positive"),
        ({"timeout_s": float("nan")}, "timeout_s must be positive"),
        ({"prompt": " "}, "prompt cannot be empty"),
    ],
)
def test_ollama_reasoner_rejects_invalid_configuration(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OllamaReasoner(**kwargs)


def test_demo_reasoner_uses_mock_by_default_and_optional_ollama(monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL", raising=False)
    assert isinstance(demo_app.DemoReasoner.from_environment(), demo_app.DemoReasoner)

    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL", "gemma3:4b")
    monkeypatch.setenv(
        "ACCESSFLOW_DEMO_OLLAMA_REASONER_ENDPOINT",
        "http://localhost:11434/api/generate",
    )
    configured = demo_app.DemoReasoner.from_environment()
    assert isinstance(configured, OllamaReasoner)
    assert configured.backend_name == "ollama/gemma3:4b"


@pytest.mark.asyncio
async def test_ollama_reasoner_keeps_blocking_opener_off_event_loop():
    started = asyncio.Event()

    def opener(request, *, timeout):
        started.set()
        return FakeResponse({"response": json.dumps({})})

    reasoner = OllamaReasoner(opener=opener)
    await reasoner.plan(_view(), [])
    assert started.is_set()
