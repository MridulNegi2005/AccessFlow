import asyncio
import base64
import importlib.util
import json
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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


def _png_bytes():
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = b"\x00\x10\x20\x30\xff"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
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


def test_ollama_reasoner_keeps_bounded_context_valid_and_recent():
    observations = [
        Observation(
            event_id=f"event-{index}",
            source_id=f"source-{index}",
            modality="text",
            text=f"history-{index} " + ("x" * 2000),
            final=True,
            backend="test",
        )
        for index in range(24)
    ]
    view = SessionView(session_id="reasoner-session", state=Snapshot(), observations=observations, results=[])
    reasoner = OllamaReasoner()

    prompt = reasoner._prompt_for(view, [])
    context = json.loads(prompt.split("\n", 1)[1])

    assert len(prompt) <= MAX_REASONER_CONTEXT_CHARS
    assert context["observations"][-1]["source_id"] == "source-23"
    assert context["observations"][0]["source_id"] != "source-0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"{not-json", "invalid JSON"),
        ({"response": "not-json"}, "invalid plan JSON"),
        ({"response": json.dumps([])}, "invalid plan shape"),
        ({"response": json.dumps({"request_complete": "yes"})}, "invalid plan proposal"),
        ({"done": False, "response": json.dumps({})}, "incomplete response"),
        ({"done": "true", "response": json.dumps({})}, "incomplete response"),
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


def test_websocket_environment_reasoner_receives_multimodal_context(monkeypatch):
    class ReasonerHandler(BaseHTTPRequestHandler):
        requests = []
        image_context_received = threading.Event()

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            ReasonerHandler.requests.append(payload)
            if payload.get("images"):
                response = json.dumps({"response": "screen shows the approval prompt"}).encode("utf-8")
            else:
                if "screen shows the approval prompt" in payload.get("prompt", ""):
                    ReasonerHandler.image_context_received.set()
                plan = {
                    "response": "The local reasoner received the spoken request and screen evidence.",
                    "request_complete": True,
                }
                response = json.dumps({"response": json.dumps(plan)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ReasonerHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL", "gemma3:4b")
    monkeypatch.setenv(
        "ACCESSFLOW_DEMO_OLLAMA_REASONER_ENDPOINT",
        f"http://127.0.0.1:{server.server_port}/api/generate",
    )
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL", "gemma3:4b")
    monkeypatch.setenv(
        "ACCESSFLOW_DEMO_OLLAMA_ENDPOINT",
        f"http://127.0.0.1:{server.server_port}/api/generate",
    )

    try:
        encoded_image = base64.b64encode(_png_bytes()).decode("ascii")
        with TestClient(demo_app.app) as client:
            with client.websocket_connect("/ws") as socket:
                status = socket.receive_json()
                socket.send_json(
                    {
                        "kind": "frame",
                        "payload": {"data_base64": encoded_image, "frame_id": "reasoner-frame"},
                    }
                )
                media_status = socket.receive_json()
                assert ReasonerHandler.image_context_received.wait(timeout=1)
                socket.send_json(
                    {
                        "kind": "transcript",
                        "payload": {"text": "What did I send you?"},
                    }
                )
                outputs = []
                while not any(item["kind"] in {"final", "error"} for item in outputs):
                    outputs.append(socket.receive_json())

        final = next(item for item in outputs if item["kind"] == "final")
        assert status["kind"] == "demo_status"
        assert status["payload"]["perception_backend"] == (
            "demo/mock audio + local/Ollama gemma3:4b image"
        )
        assert status["payload"]["reasoner_backend"] == "ollama/gemma3:4b"
        assert media_status["payload"] == {
            "media_received": "frame",
            "source_id": "reasoner-frame",
        }
        assert final["payload"] == {
            "text": "The local reasoner received the spoken request and screen evidence.",
            "basis": "informational",
            "backend": "reasoner",
        }
        assert len(ReasonerHandler.requests) >= 2
        vision_requests = [payload for payload in ReasonerHandler.requests if payload.get("images")]
        reasoner_requests = [payload for payload in ReasonerHandler.requests if not payload.get("images")]
        request_payload = next(
            payload
            for payload in reversed(reasoner_requests)
            if "screen shows the approval prompt" in payload["prompt"]
            and "What did I send you?" in payload["prompt"]
        )
        assert request_payload["model"] == "gemma3:4b"
        assert request_payload["stream"] is False
        assert request_payload["format"] == "json"
        assert "screen shows the approval prompt" in request_payload["prompt"]
        assert "What did I send you?" in request_payload["prompt"]
        assert len(request_payload["prompt"]) <= MAX_REASONER_CONTEXT_CHARS
        assert vision_requests
        assert len(reasoner_requests) >= 2
        assert vision_requests[-1]["model"] == "gemma3:4b"
        assert vision_requests[-1]["images"] == [encoded_image]
    finally:
        server.shutdown()


def test_websocket_reasoner_failure_is_recoverable(monkeypatch):
    class ReasonerHandler(BaseHTTPRequestHandler):
        requests = []

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            ReasonerHandler.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
            if len(ReasonerHandler.requests) == 1:
                response = b"{not-json"
            else:
                plan = {"response": "The recovered local reasoner answered.", "request_complete": True}
                response = json.dumps({"response": json.dumps(plan)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ReasonerHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL", "gemma3:4b")
    monkeypatch.setenv(
        "ACCESSFLOW_DEMO_OLLAMA_REASONER_ENDPOINT",
        f"http://127.0.0.1:{server.server_port}/api/generate",
    )
    monkeypatch.delenv("ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL", raising=False)

    def receive_until(socket, terminal_kind):
        outputs = []
        while not any(item["kind"] == terminal_kind for item in outputs):
            outputs.append(socket.receive_json())
        return outputs

    try:
        with TestClient(demo_app.app) as client:
            with client.websocket_connect("/ws") as socket:
                socket.receive_json()
                socket.send_json(
                    {"kind": "transcript", "payload": {"text": "First request"}}
                )
                failed = receive_until(socket, "error")
                socket.send_json(
                    {"kind": "transcript", "payload": {"text": "Second request"}}
                )
                recovered = receive_until(socket, "final")

        error = next(item for item in failed if item["kind"] == "error")
        final = next(item for item in recovered if item["kind"] == "final")
        assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
        assert final["payload"] == {
            "text": "The recovered local reasoner answered.",
            "basis": "informational",
            "backend": "reasoner",
        }
        assert len(ReasonerHandler.requests) == 2
    finally:
        server.shutdown()
