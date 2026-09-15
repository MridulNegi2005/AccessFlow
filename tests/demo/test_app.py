import io
import asyncio
import base64
import importlib.util
import json
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from accessflow.contracts import (
    AudioEvent,
    EndEvent,
    FrameEvent,
    Observation,
    PlanProposal,
    ProposedCall,
    SessionView,
    Snapshot,
    Start,
    StartEvent,
    TranscriptEvent,
    ToolManifest,
)
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, FinalFlagPolicy, MockOnlyAuthorization


demo_path = Path(__file__).parents[2] / "demo" / "app.py"
spec = importlib.util.spec_from_file_location("accessflow_demo_app", demo_path)
assert spec and spec.loader
demo_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_app)
DemoPerception = demo_app.DemoPerception
event_from_message = demo_app.event_from_message

def _png_bytes(*, width: int = 2, height: int = 3) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    row = b"\x00" + b"\x00\x40\x80\xff" * width
    pixels = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("transcript", TranscriptEvent), ("audio", AudioEvent), ("frame", FrameEvent)],
)
def test_browser_message_becomes_typed_event(kind, expected):
    event = event_from_message("session-1", {"kind": kind, "payload": {"path": "input"}})

    assert isinstance(event, expected)
    assert event.session_id == "session-1"


def test_browser_message_preserves_event_and_audio_source_timestamps():
    event = event_from_message(
        "session-1",
        {
            "kind": "audio",
            "payload": {
                "path": "speech.wav",
                "utterance_id": "audio-1",
                "timestamp": 12.5,
                "speech_start": 8.25,
                "speech_end": 11.75,
            },
        },
    )

    assert event.timestamp == 12.5
    assert event.payload.speech_start == 8.25
    assert event.payload.speech_end == 11.75


def test_browser_frame_preserves_source_timestamp():
    event = event_from_message(
        "session-1",
        {
            "kind": "frame",
            "timestamp": 17.25,
            "payload": {"path": "screen.png", "frame_id": "frame-1"},
        },
    )

    assert event.timestamp == 17.25


@pytest.mark.asyncio
async def test_demo_perception_can_delegate_audio_to_injected_local_backend():
    class LocalAudio:
        audio_backend_name = "faster-whisper/cpu-int8"

        async def observe(self, event):
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.utterance_id,
                revision=event.payload.revision,
                modality="audio",
                text="local transcript",
                final=True,
                backend="faster-whisper/cpu-int8",
            )

    event = event_from_message(
        "session-1",
        {"kind": "audio", "payload": {"path": "speech.wav", "utterance_id": "audio-1"}},
    )

    perception = DemoPerception(audio_backend=LocalAudio())
    observations = [item async for item in perception.observe(event)]

    assert observations[0].text == "local transcript"
    assert observations[0].backend == "faster-whisper/cpu-int8"
    assert "local/Faster Whisper CPU INT8" in perception.backend_label


def test_demo_perception_does_not_overclaim_unknown_audio_backend():
    class UnknownAudio:
        async def observe(self, event):
            if False:
                yield None

    perception = DemoPerception(audio_backend=UnknownAudio())

    assert perception.backend_label == "local/unknown-audio + demo/mock text/image"


def test_demo_perception_labels_injected_audio_backend_truthfully():
    perception = DemoPerception(
        audio_backend=demo_app.LocalPerception(transcriber=lambda _: "text")
    )

    assert perception.backend_label == "local/injected-asr audio + demo/mock text/image"


def test_demo_perception_does_not_overclaim_model_only_vision_backend():
    class ModelOnlyVision:
        model = "gemma3:4b"

    perception = DemoPerception(vision_backend=ModelOnlyVision())

    assert perception.backend_label == "demo/mock audio + local/unknown-vision image"


def test_demo_perception_does_not_overclaim_unknown_vision_backend():
    class UnknownVision:
        pass

    perception = DemoPerception(vision_backend=UnknownVision())

    assert perception.backend_label == "demo/mock audio + local/unknown-vision image"


@pytest.mark.asyncio
async def test_demo_perception_can_delegate_image_to_injected_local_backend(tmp_path: Path):
    class LocalVision:
        model = "gemma3:4b"
        backend_name = "ollama/gemma3:4b"

        def __call__(self, path: Path) -> str:
            assert path.name == "screen.png"
            return "screen evidence"

    image = tmp_path / "screen.png"
    image.write_bytes(
        _png_bytes(width=4, height=5)
    )
    event = event_from_message(
        "session-1",
        {"kind": "frame", "payload": {"path": str(image), "frame_id": "frame-local"}},
    )

    perception = DemoPerception(vision_backend=LocalVision())
    observations = [item async for item in perception.observe(event)]

    assert observations[0].text == "screen evidence"
    assert observations[0].backend == "ollama/gemma3:4b"
    assert "local/Ollama gemma3:4b image" in perception.backend_label


@pytest.mark.asyncio
async def test_demo_perception_labels_mock_image_and_preserves_frame_id(tmp_path: Path):
    event = event_from_message(
        "session-1",
        {
            "kind": "frame",
            "payload": {"path": "device.png", "frame_id": "frame-9", "timestamp": 19.5},
        },
    )

    observations = [item async for item in DemoPerception().observe(event)]

    assert len(observations) == 1
    observation: Observation = observations[0]
    assert observation.source_id == "frame-9"
    assert observation.revision == 0
    assert observation.modality == "image"
    assert observation.backend == "demo/mock-image"
    assert observation.speech_start == observation.speech_end == 19.5
    assert "device.png" in observation.text


def test_demo_perception_environment_can_enable_local_audio(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ACCESSFLOW_DEMO_WHISPER_MODEL", str(tmp_path))

    perception = DemoPerception.from_environment()

    assert "local/Faster Whisper CPU INT8" in perception.backend_label





def test_demo_perception_environment_can_enable_local_vision(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL", "gemma3:4b")
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/generate")

    perception = DemoPerception.from_environment()

    assert "local/Ollama gemma3:4b image" in perception.backend_label


def test_demo_perception_environment_rejects_missing_local_model(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ACCESSFLOW_DEMO_WHISPER_MODEL", str(tmp_path / "missing"))

    with pytest.raises(ValueError, match="existing local model directory"):
        DemoPerception.from_environment()


def test_demo_favicon_is_served():
    with TestClient(demo_app.app) as client:
        response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "AccessFlow" in response.text


def test_demo_recorder_worklet_is_served():
    with TestClient(demo_app.app) as client:
        response = client.get("/recorder-worklet.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert "registerProcessor" in response.text


def test_demo_page_exposes_input_controls_and_backend_label():
    html = Path("demo/index.html").read_text(encoding="utf-8")

    assert 'id="text-form"' in html
    assert 'accept="audio/wav,.wav"' in html
    assert 'accept="image/png,.png"' in html
    assert 'id="mic"' in html
    assert 'id="stop-mic"' in html
    assert 'id="backend-label"' in html
    assert 'getUserMedia' in html
    assert 'encodeWav' in html
    assert 'AudioWorkletNode' in html
    assert 'recorder-worklet.js' in html
    assert 'performance.timeOrigin' in html
    assert 'timestamp: sourceTimestamp' in html
    assert 'card.innerHTML' not in html
    assert 'heading.textContent = event.kind' in html
    assert 'details.textContent = JSON.stringify(event, null, 2)' in html


@pytest.mark.asyncio
async def test_demo_reasoner_surfaces_prior_multimodal_context():
    view = SessionView(
        session_id="session-1",
        state=Snapshot(),
        observations=[
            Observation(
                event_id="audio-event",
                source_id="audio-1",
                modality="audio",
                text="Book Wednesday",
                final=True,
                backend="local/injected-asr",
            ),
            Observation(
                event_id="frame-event",
                source_id="frame-1",
                modality="image",
                text="screen shows the approval prompt",
                final=True,
                backend="local/injected-vision",
            ),
        ],
        results=[],
    )

    proposal = await demo_app.DemoReasoner().plan(view, [])

    assert proposal.request_complete
    assert proposal.response == (
        "Mock agent received image input: screen shows the approval prompt"
        " | multimodal context: audio: Book Wednesday"
    )


@pytest.mark.asyncio
async def test_demo_reasoner_bounds_prior_multimodal_context():
    history = [
        Observation(
            event_id=f"history-event-{index}",
            source_id=f"history-{index}",
            modality="audio" if index % 2 == 0 else "image",
            text=f"history-{index} " + "x" * 100,
            final=True,
            backend="test/provider",
        )
        for index in range(240)
    ]
    history.append(
        Observation(
            event_id="latest-event",
            source_id="latest",
            modality="text",
            text="latest request",
            final=True,
            backend="test/text",
        )
    )
    view = SessionView(session_id="session-1", state=Snapshot(), observations=history, results=[])

    proposal = await demo_app.DemoReasoner().plan(view, [])

    assert proposal.response is not None
    assert "latest request" in proposal.response
    assert "history-239" in proposal.response
    assert "history-0" not in proposal.response
    context = proposal.response.split(" | multimodal context: ", 1)[1]
    assert len(context) <= demo_app.MAX_CONTEXT_CHARS
    assert proposal.request_complete is True

    oversized = Observation(
        event_id="oversized-event",
        source_id="oversized",
        modality="image",
        text="oversized " + "y" * (demo_app.MAX_CONTEXT_CHARS * 2),
        final=True,
        backend="test/provider",
    )
    oversized_view = SessionView(
        session_id="session-1",
        state=Snapshot(),
        observations=[oversized, history[-1]],
        results=[],
    )
    oversized_proposal = await demo_app.DemoReasoner().plan(oversized_view, [])
    oversized_context = oversized_proposal.response.split(" | multimodal context: ", 1)[1]
    assert len(oversized_context) == demo_app.MAX_CONTEXT_CHARS
    assert oversized_context.startswith("image: oversized ")


def test_websocket_reports_invalid_local_model_configuration(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("ACCESSFLOW_DEMO_WHISPER_MODEL", str(tmp_path / "missing"))

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            error = socket.receive_json()

    assert error["kind"] == "demo_error"
    assert error["payload"]["backend"] == "demo/config"
    assert "existing local model directory" in error["payload"]["message"]


def test_websocket_returns_controller_output_event():
    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            socket.send_json({"kind": "transcript", "payload": {"text": "Book Wednesday"}})
            received = []
            output_kinds = {"acknowledge", "final"}
            while len([item for item in received if item["kind"] in output_kinds]) < 2:
                received.append(socket.receive_json())

    outputs = [item for item in received if item["kind"] in {"acknowledge", "final"}]
    assert {item["kind"] for item in outputs} == {"acknowledge", "final"}
    final = next(item for item in outputs if item["kind"] == "final")
    assert final["payload"]["basis"] == "informational"
    assert "Book Wednesday" in final["payload"]["text"]
    assert final["state"]["status"] == "listening"

def _receive_controller_outputs(socket):
    received = []
    while not any(item["kind"] in {"final", "error"} for item in received):
        received.append(socket.receive_json())
    return received


def test_websocket_audio_upload_reaches_mock_controller():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded = base64.b64encode(fixture.read_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {"kind": "audio", "payload": {"data_base64": encoded, "utterance_id": "ws-audio"}}
            )
            media_status = socket.receive_json()
            received = _receive_controller_outputs(socket)

    assert status["payload"]["perception_backend"] == "demo/mock"
    assert media_status["payload"] == {"media_received": "audio", "source_id": "ws-audio"}
    final = next(item for item in received if item["kind"] == "final")
    assert "Mock agent received audio input" in final["payload"]["text"]
    assert final["payload"]["backend"] == "reasoner"


def test_websocket_local_perception_timeout_is_recoverable(monkeypatch):
    started = threading.Event()
    finished = threading.Event()

    def transcriber(path: Path) -> str:
        started.set()
        try:
            time.sleep(0.2)
            return "late transcript"
        finally:
            finished.set()

    def configured_perception(cls):
        return DemoPerception(
            audio_backend=demo_app.LocalPerception(
                transcriber=transcriber,
                timeout_s=0.05,
            )
        )

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {
                    "kind": "audio",
                    "payload": {
                        "data_base64": encoded_audio,
                        "utterance_id": "timed-out-upload",
                    },
                }
            )
            media_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json({"kind": "transcript", "payload": {"text": "Still connected"}})
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "local/injected-asr audio + demo/mock text/image"
    assert media_status["payload"] == {"media_received": "audio", "source_id": "timed-out-upload"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected" in final["payload"]["text"]
    assert started.wait(timeout=1)
    assert finished.wait(timeout=1)


def test_browser_message_rejects_non_object_payload():
    with pytest.raises(ValueError, match="payload must be an object"):
        event_from_message("session-1", {"kind": "frame", "payload": []})


def test_websocket_reports_recoverable_structural_input_error():
    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json({"kind": "frame", "payload": []})
            error = socket.receive_json()
            socket.send_json({"kind": "transcript", "payload": {"text": "Still connected"}})
            received = _receive_controller_outputs(socket)

    assert status["kind"] == "demo_status"
    assert error["kind"] == "demo_error"
    assert error["payload"]["backend"] == "demo/input"
    assert "payload must be an object" in error["payload"]["message"]
    final = next(item for item in received if item["kind"] == "final")
    assert "Still connected" in final["payload"]["text"]


def test_websocket_reports_recoverable_media_input_error():
    encoded = base64.b64encode(b"not a wav").decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json({"kind": "audio", "payload": {"data_base64": encoded}})
            error = socket.receive_json()
            socket.send_json({"kind": "transcript", "payload": {"text": "Still connected"}})
            received = _receive_controller_outputs(socket)

    assert status["payload"]["perception_backend"] == "demo/mock"
    assert error["kind"] == "demo_error"
    assert error["payload"]["backend"] == "demo/input"
    assert "RIFF WAV" in error["payload"]["message"]
    final = next(item for item in received if item["kind"] == "final")
    assert "Still connected" in final["payload"]["text"]


def test_invalid_wav_materialization_is_removed(tmp_path: Path):
    with pytest.raises(ValueError, match="valid PCM WAV"):
        event_from_message(
            "session-1",
            {
                "kind": "audio",
                "payload": {"data_base64": base64.b64encode(b"RIFF\x04\x00\x00\x00WAVE").decode()},
            },
            media_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_invalid_png_materialization_is_removed(tmp_path: Path):
    with pytest.raises(ValueError, match="valid PNG"):
        event_from_message(
            "session-1",
            {
                "kind": "frame",
                "payload": {"data_base64": base64.b64encode(b"not a png").decode()},
            },
            media_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_websocket_reports_recoverable_image_input_error():
    encoded = base64.b64encode(b"not a png").decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json({"kind": "frame", "payload": {"data_base64": encoded}})
            error = socket.receive_json()
            socket.send_json({"kind": "transcript", "payload": {"text": "Still connected"}})
            received = _receive_controller_outputs(socket)

    assert status["payload"]["perception_backend"] == "demo/mock"
    assert error["kind"] == "demo_error"
    assert error["payload"]["backend"] == "demo/input"
    assert "PNG" in error["payload"]["message"]
    final = next(item for item in received if item["kind"] == "final")
    assert "Still connected" in final["payload"]["text"]


def test_websocket_reports_recoverable_truncated_image_input_error():
    encoded = base64.b64encode(_png_bytes()[:-4]).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json({"kind": "frame", "payload": {"data_base64": encoded}})
            error = socket.receive_json()
            socket.send_json({"kind": "transcript", "payload": {"text": "Still connected"}})
            received = _receive_controller_outputs(socket)

    assert status["payload"]["perception_backend"] == "demo/mock"
    assert error["kind"] == "demo_error"
    assert error["payload"]["backend"] == "demo/input"
    assert "valid PNG" in error["payload"]["message"]
    final = next(item for item in received if item["kind"] == "final")
    assert "Still connected" in final["payload"]["text"]

def test_websocket_png_upload_reaches_mock_controller():
    png = _png_bytes(width=2, height=3)
    encoded = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded, "frame_id": "ws-frame"}}
            )
            media_status = socket.receive_json()
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
            )
            received = _receive_controller_outputs(socket)

    assert status["payload"]["perception_backend"] == "demo/mock"
    assert media_status["payload"] == {"media_received": "frame", "source_id": "ws-frame"}
    final = next(item for item in received if item["kind"] == "final")
    assert "Mock agent received text input" in final["payload"]["text"]
    assert final["payload"]["backend"] == "reasoner"


def test_websocket_combined_media_context_is_visible():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()

            socket.send_json(
                {
                    "kind": "audio",
                    "payload": {"data_base64": encoded_audio, "utterance_id": "ws-audio"},
                }
            )
            audio_status = socket.receive_json()
            audio_outputs = _receive_controller_outputs(socket)

            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "ws-frame"},
                }
            )
            frame_status = socket.receive_json()
            frame_outputs = _receive_controller_outputs(socket)

            socket.send_json(
                {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
            )
            text_outputs = _receive_controller_outputs(socket)

    audio_final = next(item for item in audio_outputs if item["kind"] == "final")
    frame_final = next(item for item in frame_outputs if item["kind"] == "final")
    text_final = next(item for item in text_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock"
    assert audio_status["payload"] == {"media_received": "audio", "source_id": "ws-audio"}
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "ws-frame"}
    assert "Mock agent received audio input" in audio_final["payload"]["text"]
    assert "multimodal context: audio:" in frame_final["payload"]["text"]
    assert "multimodal context: audio:" in text_final["payload"]["text"]
    assert "image:" in text_final["payload"]["text"]


def test_websocket_session_reset_does_not_inherit_multimodal_context():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    encoded_image = base64.b64encode(_png_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as first_socket:
            first_socket.receive_json()
            first_socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "first-frame"}}
            )
            first_socket.receive_json()
            first_socket.send_json(
                {"kind": "audio", "payload": {"data_base64": encoded_audio, "utterance_id": "first-audio"}}
            )
            first_socket.receive_json()
            _receive_controller_outputs(first_socket)
            first_socket.send_json(
                {"kind": "transcript", "payload": {"text": "Describe this screen"}}
            )
            first_outputs = _receive_controller_outputs(first_socket)

        with client.websocket_connect("/ws") as second_socket:
            second_socket.receive_json()
            second_socket.send_json(
                {"kind": "transcript", "payload": {"text": "Fresh session"}}
            )
            second_outputs = _receive_controller_outputs(second_socket)

    first_final = next(item for item in first_outputs if item["kind"] == "final")
    second_final = next(item for item in second_outputs if item["kind"] == "final")
    assert "image:" in first_final["payload"]["text"]
    assert "audio:" in first_final["payload"]["text"]
    assert "Fresh session" in second_final["payload"]["text"]
    assert "image:" not in second_final["payload"]["text"]
    assert "audio:" not in second_final["payload"]["text"]


def test_websocket_image_before_audio_context_is_visible():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "ws-frame-first"},
                }
            )
            frame_status = socket.receive_json()

            socket.send_json(
                {
                    "kind": "audio",
                    "payload": {"data_base64": encoded_audio, "utterance_id": "ws-audio-after-frame"},
                }
            )
            audio_status = socket.receive_json()
            outputs = _receive_controller_outputs(socket)

    final = next(item for item in outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock"
    assert frame_status["payload"] == {
        "media_received": "frame",
        "source_id": "ws-frame-first",
    }
    assert audio_status["payload"] == {
        "media_received": "audio",
        "source_id": "ws-audio-after-frame",
    }
    assert "Mock agent received audio input" in final["payload"]["text"]
    assert "multimodal context: image:" in final["payload"]["text"]



def test_websocket_environment_vision_provider_reaches_multimodal_context(monkeypatch):
    class VisionHandler(BaseHTTPRequestHandler):
        requests = []
        request_received = threading.Event()

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            VisionHandler.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
            VisionHandler.request_received.set()
            response = json.dumps({"response": "screen shows the approval prompt"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    class ObservingReasoner(demo_app.DemoReasoner):
        image_seen = threading.Event()

        async def plan(self, view, manifests):
            if any(item.modality == "image" for item in view.observations):
                ObservingReasoner.image_seen.set()
            return await super().plan(view, manifests)

    monkeypatch.setattr(demo_app, "DemoReasoner", ObservingReasoner)
    server = ThreadingHTTPServer(("127.0.0.1", 0), VisionHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
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
                    {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "env-frame"}}
                )
                media_status = socket.receive_json()
                assert ObservingReasoner.image_seen.wait(timeout=1)
                assert VisionHandler.request_received.wait(timeout=1)
                socket.send_json(
                    {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
                )
                outputs = _receive_controller_outputs(socket)

        final = next(item for item in outputs if item["kind"] == "final")
        assert status["payload"]["perception_backend"] == "demo/mock audio + local/Ollama gemma3:4b image"
        assert media_status["payload"] == {"media_received": "frame", "source_id": "env-frame"}
        assert "screen shows the approval prompt" in final["payload"]["text"]
        assert "What is on this screen?" in final["payload"]["text"]
        assert final["payload"]["basis"] == "informational"
        request = VisionHandler.requests[-1]
        assert request["model"] == "gemma3:4b"
        assert request["images"] == [base64.b64encode(_png_bytes()).decode("ascii")]
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)



def test_websocket_configured_audio_and_vision_share_context(monkeypatch, tmp_path: Path):
    class VisionHandler(BaseHTTPRequestHandler):
        requests = []

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            VisionHandler.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
            response = json.dumps({"response": "screen shows the approval prompt"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    class MultimodalReasoner:
        latest_view = None

        async def plan(self, view, manifests):
            modalities = {item.modality for item in view.observations}
            if {"audio", "image"} <= modalities:
                MultimodalReasoner.latest_view = view.model_copy(deep=True)
                return PlanProposal(
                    response="Audio context and screen evidence are available together.",
                    request_complete=True,
                )
            return PlanProposal()

    class ConfiguredLocalPerception:
        audio_backend_name = "local/injected-asr"

        def __init__(self, *, model_path=None, vision_provider=None):
            self.model_path = model_path
            self.vision_provider = vision_provider

        async def observe(self, event):
            if isinstance(event, AudioEvent):
                yield Observation(
                    event_id=event.event_id,
                    source_id=event.payload.utterance_id,
                    revision=event.payload.revision,
                    modality="audio",
                    text="Please inspect the attached screen",
                    final=True,
                    backend="local/injected-asr",
                )
                return
            if isinstance(event, FrameEvent):
                yield Observation(
                    event_id=event.event_id,
                    source_id=event.payload.frame_id,
                    revision=0,
                    modality="image",
                    text=self.vision_provider(Path(event.payload.path)),
                    final=True,
                    backend=getattr(self.vision_provider, "backend_name", "local/injected-vision"),
                )
                return
            raise AssertionError(f"unexpected event: {event.kind}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), VisionHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    model_dir = tmp_path / "whisper-model"
    model_dir.mkdir()
    monkeypatch.setenv("ACCESSFLOW_DEMO_WHISPER_MODEL", str(model_dir))
    monkeypatch.setenv("ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL", "gemma3:4b")
    monkeypatch.setenv(
        "ACCESSFLOW_DEMO_OLLAMA_ENDPOINT",
        f"http://127.0.0.1:{server.server_port}/api/generate",
    )
    monkeypatch.setattr(demo_app, "LocalPerception", ConfiguredLocalPerception)

    monkeypatch.setattr(demo_app, "DemoReasoner", MultimodalReasoner)

    def receive_media_status(socket, media_kind):
        while True:
            message = socket.receive_json()
            if (
                message.get("kind") == "demo_status"
                and message.get("payload", {}).get("media_received") == media_kind
            ):
                return message

    try:
        fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
        encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
        png = _png_bytes(width=2, height=3)
        encoded_image = base64.b64encode(png).decode("ascii")

        with TestClient(demo_app.app) as client:
            with client.websocket_connect("/ws") as socket:
                status = socket.receive_json()
                socket.send_json(
                    {"kind": "audio", "payload": {"data_base64": encoded_audio, "utterance_id": "configured-audio"}}
                )
                audio_status = receive_media_status(socket, "audio")
                socket.send_json(
                    {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "configured-frame"}}
                )
                frame_status = receive_media_status(socket, "frame")
                outputs = _receive_controller_outputs(socket)

        final = next(item for item in outputs if item["kind"] == "final")
        assert status["payload"]["perception_backend"] == (
            "local/injected-asr audio + local/Ollama gemma3:4b image"
        )
        assert audio_status["payload"] == {
            "media_received": "audio",
            "source_id": "configured-audio",
        }
        assert frame_status["payload"] == {
            "media_received": "frame",
            "source_id": "configured-frame",
        }
        assert final["payload"]["text"] == "Audio context and screen evidence are available together."
        assert final["payload"]["basis"] == "informational"
        assert MultimodalReasoner.latest_view is not None
        observations = {item.source_id: item for item in MultimodalReasoner.latest_view.observations}
        assert observations["configured-audio"].backend == "local/injected-asr"
        assert observations["configured-frame"].backend == "ollama/gemma3:4b"
        assert observations["configured-frame"].text == "screen shows the approval prompt"
        request = VisionHandler.requests[-1]
        assert request["model"] == "gemma3:4b"
        assert request["prompt"] == "Describe only the visible device evidence and state uncertainty."
        assert request["images"] == [base64.b64encode(png).decode("ascii")]
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)

def test_websocket_audio_backend_failure_keeps_multimodal_session_usable(monkeypatch):
    class FailingAudio:
        async def observe(self, event):
            if False:
                yield None
            raise RuntimeError("audio service unavailable")

    class LocalVision:
        model = "injected-vision"
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            return "screen shows the approval prompt"

    class ObservingReasoner(demo_app.DemoReasoner):
        image_seen = threading.Event()

        async def plan(self, view, manifests):
            if any(item.modality == "image" for item in view.observations):
                ObservingReasoner.image_seen.set()
            return await super().plan(view, manifests)

    def configured_perception(cls):
        return DemoPerception(audio_backend=FailingAudio(), vision_backend=LocalVision())

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    monkeypatch.setattr(demo_app, "DemoReasoner", ObservingReasoner)

    def receive_media_status(socket, media_kind):
        while True:
            message = socket.receive_json()
            if (
                message.get("kind") == "demo_status"
                and message.get("payload", {}).get("media_received") == media_kind
            ):
                return message

    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            socket.receive_json()
            socket.send_json(
                {"kind": "audio", "payload": {"data_base64": encoded_audio, "utterance_id": "failed-audio"}}
            )
            audio_status = receive_media_status(socket, "audio")
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "after-audio-failure"}}
            )
            frame_status = receive_media_status(socket, "frame")
            assert ObservingReasoner.image_seen.wait(timeout=1)
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
            )
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert audio_status["payload"] == {"media_received": "audio", "source_id": "failed-audio"}
    assert frame_status["payload"] == {
        "media_received": "frame",
        "source_id": "after-audio-failure",
    }
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "What is on this screen?" in final["payload"]["text"]
    assert "screen shows the approval prompt" in final["payload"]["text"]
    assert final["payload"]["basis"] == "informational"

def test_websocket_configured_vision_failure_is_recoverable(monkeypatch):
    class FailingVision:
        model = "failing-vision"
        backend_name = "local/failing-vision"

        def __call__(self, path: Path) -> str:
            raise RuntimeError("vision service unavailable")

    def configured_perception(cls):
        return DemoPerception(vision_backend=FailingVision())

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "frame-failure"},
                }
            )
            media_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "Still connected"}}
            )
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert "local/failing-vision image" in status["payload"]["perception_backend"]
    assert media_status["payload"] == {"media_received": "frame", "source_id": "frame-failure"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected" in final["payload"]["text"]



def test_websocket_vision_failure_recovers_to_multimodal_session(monkeypatch):
    class RecoveringVision:
        backend_name = "local/recovering-vision"

        def __init__(self):
            self.calls = 0

        def __call__(self, path: Path) -> str:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("vision service unavailable")
            return "screen shows the approval prompt"

    vision = RecoveringVision()

    def transcribe(path: Path) -> str:
        return "Please inspect the attached screen"

    def configured_perception(cls):
        return DemoPerception(
            audio_backend=demo_app.LocalPerception(transcriber=transcribe),
            vision_backend=vision,
        )

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()

            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "failed-frame"},
                }
            )
            failed_frame_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)

            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "recovered-frame"},
                }
            )
            recovered_frame_status = socket.receive_json()

            socket.send_json(
                {
                    "kind": "audio",
                    "payload": {
                        "data_base64": encoded_audio,
                        "utterance_id": "recovered-audio",
                    },
                }
            )
            audio_status = socket.receive_json()
            multimodal_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in multimodal_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == (
        "local/injected-asr audio + local/recovering-vision image"
    )
    assert failed_frame_status["payload"] == {
        "media_received": "frame",
        "source_id": "failed-frame",
    }
    assert recovered_frame_status["payload"] == {
        "media_received": "frame",
        "source_id": "recovered-frame",
    }
    assert audio_status["payload"] == {
        "media_received": "audio",
        "source_id": "recovered-audio",
    }
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Please inspect the attached screen" in final["payload"]["text"]
    assert "screen shows the approval prompt" in final["payload"]["text"]
    assert vision.calls == 2
    assert final["payload"]["basis"] == "informational"

@pytest.mark.parametrize("vision_response", [b"[]", b"{not-json"])
def test_websocket_malformed_vision_json_is_recoverable(monkeypatch, vision_response):
    class MalformedVisionHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            response = vision_response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), MalformedVisionHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    def configured_perception(cls):
        return DemoPerception(
            vision_backend=demo_app.OllamaVisionProvider(
                model="gemma3:4b",
                endpoint=f"http://127.0.0.1:{server.server_port}/api/generate",
            )
        )

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    encoded_image = base64.b64encode(_png_bytes()).decode("ascii")
    try:
        with TestClient(demo_app.app) as client:
            with client.websocket_connect("/ws") as socket:
                status = socket.receive_json()
                socket.send_json(
                    {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "bad-json-frame"}}
                )
                frame_status = socket.receive_json()
                failed_outputs = _receive_controller_outputs(socket)
                socket.send_json(
                    {"kind": "transcript", "payload": {"text": "Still connected"}}
                )
                continued_outputs = _receive_controller_outputs(socket)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock audio + local/Ollama gemma3:4b image"
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "bad-json-frame"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected" in final["payload"]["text"]


def test_websocket_vision_quota_exhaustion_is_recoverable(monkeypatch):
    class QuotaResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"error": "quota exhausted"}).encode("utf-8")

    provider = demo_app.OllamaVisionProvider(
        model="gemma3:4b",
        timeout_s=0.1,
        opener=lambda request, timeout: QuotaResponse(),
    )

    def configured_perception(cls):
        return DemoPerception(vision_backend=provider)

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    encoded_image = base64.b64encode(_png_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "quota-frame"}}
            )
            frame_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "Still connected"}}
            )
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock audio + local/Ollama gemma3:4b image"
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "quota-frame"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected" in final["payload"]["text"]



def test_websocket_http_vision_quota_exhaustion_is_recoverable(monkeypatch):
    def opener(request, *, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            {},
            io.BytesIO(json.dumps({"error": "quota exhausted"}).encode("utf-8")),
        )

    provider = demo_app.OllamaVisionProvider(
        model="gemma3:4b",
        timeout_s=0.1,
        opener=opener,
    )

    def configured_perception(cls):
        return DemoPerception(vision_backend=provider)

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    encoded_image = base64.b64encode(_png_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "http-quota-frame"}}
            )
            frame_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "Still connected after HTTP quota"}}
            )
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock audio + local/Ollama gemma3:4b image"
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "http-quota-frame"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected after HTTP quota" in final["payload"]["text"]

def test_websocket_vision_timeout_is_recoverable(monkeypatch):
    def opener(request, *, timeout):
        raise TimeoutError("vision request timed out")

    provider = demo_app.OllamaVisionProvider(
        model="gemma3:4b",
        timeout_s=0.1,
        opener=opener,
    )

    def configured_perception(cls):
        return DemoPerception(vision_backend=provider)

    monkeypatch.setattr(
        demo_app.DemoPerception,
        "from_environment",
        classmethod(configured_perception),
    )
    encoded_image = base64.b64encode(_png_bytes()).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "timeout-frame"}}
            )
            frame_status = socket.receive_json()
            failed_outputs = _receive_controller_outputs(socket)
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "Still connected"}}
            )
            continued_outputs = _receive_controller_outputs(socket)

    error = next(item for item in failed_outputs if item["kind"] == "error")
    final = next(item for item in continued_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock audio + local/Ollama gemma3:4b image"
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "timeout-frame"}
    assert error["payload"] == {"code": "backend_failure", "detail": "RuntimeError"}
    assert "Still connected" in final["payload"]["text"]


@pytest.mark.asyncio
async def test_configured_vision_failure_emits_backend_error_without_final(tmp_path: Path):
    class FailingVision:
        backend_name = "local/failing-vision"

        def __call__(self, path: Path) -> str:
            assert path.parent == tmp_path
            raise RuntimeError("vision service unavailable")

    png = _png_bytes(width=2, height=3)
    image = event_from_message(
        "vision-failure-session",
        {
            "kind": "frame",
            "payload": {
                "data_base64": base64.b64encode(png).decode("ascii"),
                "frame_id": "frame-failure",
            },
        },
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    agent = Agent(
        DemoPerception(vision_backend=FailingVision()),
        FinalFlagPolicy(),
        demo_app.DemoReasoner(),
        scenario_timeout=2,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id="vision-failure-session", payload=Start()))
        await incoming.put(image)
        error = None
        while error is None:
            event = await asyncio.wait_for(outgoing.get(), timeout=1)
            if event.kind == "error":
                error = event
        assert error.payload["code"] == "backend_failure"
        assert error.payload["detail"] == "RuntimeError"
        assert outgoing.empty()
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id="vision-failure-session"))
        await asyncio.wait_for(task, timeout=1)



@pytest.mark.xfail(
    strict=True,
    reason="The current Agent retains prior frame observations when the active frame changes.",
)
def test_websocket_new_frame_replaces_previous_frame():
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()
            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "ws-frame-1"},
                }
            )
            first_status = socket.receive_json()
            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "ws-frame-2"},
                }
            )
            second_status = socket.receive_json()
            socket.send_json(
                {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
            )
            outputs = _receive_controller_outputs(socket)

    final = next(item for item in outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock"
    assert first_status["payload"] == {"media_received": "frame", "source_id": "ws-frame-1"}
    assert second_status["payload"] == {"media_received": "frame", "source_id": "ws-frame-2"}
    assert final["payload"]["text"].count("image:") == 1



def test_websocket_multimodal_revision_keeps_latest_text_and_frame():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            status = socket.receive_json()

            socket.send_json(
                {
                    "kind": "audio",
                    "payload": {"data_base64": encoded_audio, "utterance_id": "ws-audio"},
                }
            )
            audio_status = socket.receive_json()
            _receive_controller_outputs(socket)

            socket.send_json(
                {
                    "kind": "transcript",
                    "payload": {
                        "utterance_id": "utterance-1",
                        "revision": 0,
                        "text": "Book Tuesday",
                    },
                }
            )
            _receive_controller_outputs(socket)

            socket.send_json(
                {
                    "kind": "transcript",
                    "payload": {
                        "utterance_id": "utterance-1",
                        "revision": 1,
                        "text": "Actually Wednesday",
                    },
                }
            )
            revised_outputs = _receive_controller_outputs(socket)

            socket.send_json(
                {
                    "kind": "frame",
                    "payload": {"data_base64": encoded_image, "frame_id": "ws-frame"},
                }
            )
            frame_status = socket.receive_json()
            frame_outputs = _receive_controller_outputs(socket)

            socket.send_json(
                {"kind": "transcript", "payload": {"text": "What is on this screen?"}}
            )
            final_outputs = _receive_controller_outputs(socket)

    revised_final = next(item for item in revised_outputs if item["kind"] == "final")
    frame_final = next(item for item in frame_outputs if item["kind"] == "final")
    final = next(item for item in final_outputs if item["kind"] == "final")
    assert status["payload"]["perception_backend"] == "demo/mock"
    assert audio_status["payload"] == {"media_received": "audio", "source_id": "ws-audio"}
    assert frame_status["payload"] == {"media_received": "frame", "source_id": "ws-frame"}
    assert "Actually Wednesday" in revised_final["payload"]["text"]
    assert "Book Tuesday" not in revised_final["payload"]["text"]
    assert "Actually Wednesday" in frame_final["payload"]["text"]
    assert "Book Tuesday" not in frame_final["payload"]["text"]
    assert "Actually Wednesday" in final["payload"]["text"]
    assert "Book Tuesday" not in final["payload"]["text"]
    assert "image:" in final["payload"]["text"]


@pytest.mark.asyncio
@pytest.mark.parametrize("event_order", [("audio", "image"), ("image", "audio")])
async def test_multimodal_audio_and_image_reach_one_agent_context(
    tmp_path: Path, event_order: tuple[str, str]
):
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    class LocalVision:
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            assert path.parent == tmp_path
            return "screen shows the approval prompt"

    class MultimodalReasoner:
        def __init__(self):
            self.views = []
            self.audio_seen = asyncio.Event()
            self.both_seen = asyncio.Event()

        async def plan(self, view, manifests):
            snapshot = view.model_copy(deep=True)
            self.views.append(snapshot)
            modalities = {item.modality for item in snapshot.observations}
            if "audio" in modalities:
                self.audio_seen.set()
            if {"audio", "image"} <= modalities:
                self.both_seen.set()
                return PlanProposal(
                    response="Audio context and screen evidence are available together.",
                    request_complete=True,
                )
            return PlanProposal()

    def transcribe(path: Path) -> str:
        assert path.parent == tmp_path
        return "Please inspect the attached screen"

    perception = DemoPerception(
        audio_backend=demo_app.LocalPerception(transcriber=transcribe),
        vision_backend=LocalVision(),
    )
    reasoner = MultimodalReasoner()
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=2,
        inference_timeout=1,
    )
    session_id = "multimodal-session"
    audio_event = event_from_message(
        session_id,
        {"kind": "audio", "payload": {"data_base64": encoded_audio, "utterance_id": "audio-1"}},
        media_root=tmp_path,
    )
    image_event = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "frame-1"}},
        media_root=tmp_path,
    )

    task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id=session_id, payload=Start()))
    events = {"audio": audio_event, "image": image_event}
    for kind in event_order:
        await incoming.put(events[kind])
    await asyncio.wait_for(reasoner.audio_seen.wait(), timeout=1)
    await asyncio.wait_for(reasoner.both_seen.wait(), timeout=1)

    outputs = []
    while not any(item.kind == "final" for item in outputs):
        outputs.append(await asyncio.wait_for(outgoing.get(), timeout=1))
    await incoming.put(EndEvent(session_id=session_id))
    await asyncio.wait_for(task, timeout=1)

    multimodal_view = next(
        view for view in reasoner.views
        if {item.modality for item in view.observations} == {"audio", "image"}
    )
    observations = {item.source_id: item for item in multimodal_view.observations}
    assert observations["audio-1"].text == "Please inspect the attached screen"
    assert observations["audio-1"].backend == "local/injected-asr"
    assert observations["frame-1"].text == "screen shows the approval prompt"
    assert observations["frame-1"].backend == "local/injected-vision"
    assert next(item for item in outputs if item.kind == "final").payload["basis"] == "informational"


@pytest.mark.asyncio
async def test_inflight_audio_is_retained_when_frame_arrives(tmp_path: Path):
    class SlowMultimodalPerception:
        def __init__(self):
            self.audio_started = asyncio.Event()
            self.release_audio = asyncio.Event()
            self.audio_finished = asyncio.Event()

        async def observe(self, event):
            if isinstance(event, AudioEvent):
                self.audio_started.set()
                await self.release_audio.wait()
                self.audio_finished.set()
                yield Observation(
                    event_id=event.event_id,
                    source_id=event.payload.utterance_id,
                    revision=event.payload.revision,
                    modality="audio",
                    text="Please inspect the attached screen",
                    final=True,
                    backend="local/injected-asr",
                )
                return
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.frame_id,
                revision=0,
                modality="image",
                text="screen shows the approval prompt",
                final=True,
                speech_start=event.timestamp,
                speech_end=event.timestamp,
                backend="local/injected-vision",
            )

    class MultimodalReasoner:
        def __init__(self):
            self.image_seen = asyncio.Event()
            self.both_seen = asyncio.Event()

        async def plan(self, view, manifests):
            modalities = {item.modality for item in view.observations}
            if "image" in modalities:
                self.image_seen.set()
            if {"audio", "image"} <= modalities:
                self.both_seen.set()
            return PlanProposal()

    session_id = "inflight-audio-frame-session"
    audio = event_from_message(
        session_id,
        {
            "kind": "audio",
            "payload": {"path": "speech.wav", "utterance_id": "audio-1"},
        },
        media_root=tmp_path,
    )
    frame = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "screen.png", "frame_id": "frame-1"}},
        media_root=tmp_path,
    )
    perception = SlowMultimodalPerception()
    reasoner = MultimodalReasoner()
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=2,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start()))
        await incoming.put(audio)
        await asyncio.wait_for(perception.audio_started.wait(), timeout=1)
        await incoming.put(frame)
        await asyncio.wait_for(reasoner.image_seen.wait(), timeout=1)
        perception.release_audio.set()
        await asyncio.wait_for(perception.audio_finished.wait(), timeout=1)
        await asyncio.wait_for(reasoner.both_seen.wait(), timeout=1)
    finally:
        perception.release_audio.set()
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
async def test_inflight_old_frame_cannot_enter_multimodal_context(tmp_path: Path):
    class SlowPerception:
        def __init__(self):
            self.first_started = asyncio.Event()
            self.release_first = asyncio.Event()
            self.first_finished = asyncio.Event()

        async def observe(self, event):
            if event.payload.frame_id == "frame-1":
                self.first_started.set()
                await self.release_first.wait()
                self.first_finished.set()
                text = "stale first frame"
            else:
                text = "current second frame"
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.frame_id,
                revision=0,
                modality="image",
                text=text,
                final=True,
                speech_start=event.timestamp,
                speech_end=event.timestamp,
                backend="local/injected-vision",
            )

    class FrameReasoner:
        def __init__(self):
            self.views = []
            self.second_seen = asyncio.Event()

        async def plan(self, view, manifests):
            snapshot = view.model_copy(deep=True)
            self.views.append(snapshot)
            frame_ids = [item.source_id for item in snapshot.observations if item.modality == "image"]
            if "frame-2" in frame_ids:
                self.second_seen.set()
            return PlanProposal()

    perception = SlowPerception()
    reasoner = FrameReasoner()
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=2,
        inference_timeout=1,
    )
    session_id = "inflight-frame-session"
    first = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "first.png", "frame_id": "frame-1"}},
        media_root=tmp_path,
    )
    second = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "second.png", "frame_id": "frame-2"}},
        media_root=tmp_path,
    )

    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start()))
        await incoming.put(first)
        for _ in range(100):
            if perception.first_started.is_set():
                break
            await asyncio.sleep(0.01)
        assert perception.first_started.is_set()
        await incoming.put(second)
        await asyncio.wait_for(reasoner.second_seen.wait(), timeout=1)
        perception.release_first.set()
        for _ in range(100):
            if perception.first_finished.is_set():
                break
            await asyncio.sleep(0.01)
        assert perception.first_finished.is_set()
        await asyncio.sleep(0.05)

        frame_views = [
            view
            for view in reasoner.views
            if any(item.source_id == "frame-2" for item in view.observations)
        ]
        assert frame_views
        assert all(
            [item.source_id for item in view.observations if item.modality == "image"] == ["frame-2"]
            for view in frame_views
        )
    finally:
        perception.release_first.set()
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)
@pytest.mark.asyncio
async def test_multimodal_context_uses_loopback_ollama_transport(tmp_path: Path):
    class VisionHandler(BaseHTTPRequestHandler):
        requests = []

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            VisionHandler.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
            response = json.dumps({"response": "screen shows the approval prompt"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), VisionHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
        encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
        png = _png_bytes(width=2, height=3)
        encoded_image = base64.b64encode(png).decode("ascii")

        def transcribe(path: Path) -> str:
            assert path.parent == tmp_path
            return "Please inspect the attached screen"

        class MultimodalReasoner:
            def __init__(self):
                self.view = None
                self.both_seen = asyncio.Event()

            async def plan(self, view, manifests):
                self.view = view.model_copy(deep=True)
                if {item.modality for item in view.observations} >= {"audio", "image"}:
                    self.both_seen.set()
                    return PlanProposal(
                        response="Audio context and screen evidence are available together.",
                        request_complete=True,
                    )
                return PlanProposal()

        perception = DemoPerception(
            audio_backend=demo_app.LocalPerception(transcriber=transcribe),
            vision_backend=demo_app.OllamaVisionProvider(
                model="gemma3:4b",
                endpoint=f"http://127.0.0.1:{server.server_port}/api/generate",
                prompt="Describe the screen.",
            ),
        )
        reasoner = MultimodalReasoner()
        incoming = asyncio.Queue()
        outgoing = asyncio.Queue()
        agent = Agent(
            perception,
            FinalFlagPolicy(),
            reasoner,
            scenario_timeout=2,
            inference_timeout=1,
        )
        session_id = "loopback-ollama-multimodal-session"
        audio_event = event_from_message(
            session_id,
            {"kind": "audio", "payload": {"data_base64": encoded_audio, "utterance_id": "audio-1"}},
            media_root=tmp_path,
        )
        image_event = event_from_message(
            session_id,
            {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "frame-1"}},
            media_root=tmp_path,
        )

        task = asyncio.create_task(agent.run(incoming, outgoing))
        await incoming.put(StartEvent(session_id=session_id, payload=Start()))
        await incoming.put(audio_event)
        await incoming.put(image_event)
        await asyncio.wait_for(reasoner.both_seen.wait(), timeout=1)

        outputs = []
        while not any(item.kind == "final" for item in outputs):
            outputs.append(await asyncio.wait_for(outgoing.get(), timeout=1))
        await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)

        assert reasoner.view is not None
        observations = {item.source_id: item for item in reasoner.view.observations}
        assert observations["audio-1"].backend == "local/injected-asr"
        assert observations["frame-1"].text == "screen shows the approval prompt"
        assert observations["frame-1"].backend == "ollama/gemma3:4b"
        request = VisionHandler.requests[-1]
        assert request["model"] == "gemma3:4b"
        assert request["prompt"] == "Describe the screen."
        assert request["stream"] is False
        assert request["images"] == [base64.b64encode(png).decode("ascii")]
        assert next(item for item in outputs if item.kind == "final").payload["basis"] == "informational"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)


@pytest.mark.asyncio
async def test_multimodal_audio_revision_replaces_old_speech_and_keeps_frame(tmp_path: Path):
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")

    class LocalVision:
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            return "screen shows the approval prompt"

    class RevisionReasoner:
        def __init__(self):
            self.views = []
            self.first_audio_seen = asyncio.Event()
            self.revision_one_seen = asyncio.Event()
            self.both_seen = asyncio.Event()

        async def plan(self, view, manifests):
            snapshot = view.model_copy(deep=True)
            self.views.append(snapshot)
            audio = [item for item in snapshot.observations if item.modality == "audio"]
            if audio and audio[-1].revision == 0:
                self.first_audio_seen.set()
            if audio and audio[-1].revision == 1:
                self.revision_one_seen.set()
            if {"audio", "image"} <= {item.modality for item in snapshot.observations}:
                self.both_seen.set()
                return PlanProposal(
                    response="The corrected speech and screen evidence are available together.",
                    request_complete=True,
                )
            return PlanProposal()

    transcripts = iter(["Book Tuesday", "Actually Wednesday"])

    def transcribe(path: Path) -> str:
        return next(transcripts)

    perception = DemoPerception(
        audio_backend=demo_app.LocalPerception(transcriber=transcribe),
        vision_backend=LocalVision(),
    )
    reasoner = RevisionReasoner()
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=2,
        inference_timeout=1,
    )
    session_id = "multimodal-revision-session"
    first_audio = event_from_message(
        session_id,
        {
            "kind": "audio",
            "payload": {
                "data_base64": encoded_audio,
                "utterance_id": "utterance-1",
                "revision": 0,
            },
        },
        media_root=tmp_path,
    )
    revised_audio = event_from_message(
        session_id,
        {
            "kind": "audio",
            "payload": {
                "data_base64": encoded_audio,
                "utterance_id": "utterance-1",
                "revision": 1,
            },
        },
        media_root=tmp_path,
    )
    image = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "frame-1"}},
        media_root=tmp_path,
    )

    task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id=session_id, payload=Start()))
    try:
        await incoming.put(first_audio)
        await asyncio.wait_for(reasoner.first_audio_seen.wait(), timeout=1)
        await incoming.put(revised_audio)
        await asyncio.wait_for(reasoner.revision_one_seen.wait(), timeout=1)
        await incoming.put(image)
        await asyncio.wait_for(reasoner.both_seen.wait(), timeout=1)

        outputs = []
        while not any(item.kind == "final" for item in outputs):
            outputs.append(await asyncio.wait_for(outgoing.get(), timeout=1))

        multimodal_view = next(
            view
            for view in reasoner.views
            if {item.modality for item in view.observations} == {"audio", "image"}
        )
        observations = {item.source_id: item for item in multimodal_view.observations}
        assert observations["utterance-1"].revision == 1
        assert observations["utterance-1"].text == "Actually Wednesday"
        assert observations["frame-1"].text == "screen shows the approval prompt"
        assert next(item for item in outputs if item.kind == "final").payload["basis"] == "informational"
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_image_evidence_never_authorizes_a_write_without_spoken_request(tmp_path: Path):
    class LocalVision:
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            assert path.parent == tmp_path
            return "Book Wednesday"

    class ImageWriteReasoner:
        def __init__(self):
            self.seen = asyncio.Event()

        async def plan(self, view, manifests):
            self.seen.set()
            return PlanProposal(
                intent="service",
                slot_updates={"day": "Wednesday"},
                request_complete=True,
                write_requested=True,
                calls=[
                    ProposedCall(
                        tool="calendar",
                        arguments={"day": "Wednesday"},
                        dependencies=["day"],
                    )
                ],
            )

    manifest = ToolManifest(
        name="calendar",
        description="Test calendar service",
        effect="write",
        timeout_s=1,
        parameters={
            "type": "object",
            "properties": {"day": {"type": "string"}},
            "required": ["day"],
            "additionalProperties": False,
        },
    )
    png = _png_bytes(width=2, height=3)
    image = event_from_message(
        "image-only-safety-session",
        {
            "kind": "frame",
            "payload": {
                "data_base64": base64.b64encode(png).decode("ascii"),
                "frame_id": "frame-only",
            },
        },
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    reasoner = ImageWriteReasoner()
    agent = Agent(
        DemoPerception(vision_backend=LocalVision()),
        FinalFlagPolicy(),
        reasoner,
        FakeTools(),
        MockOnlyAuthorization(),
        scenario_timeout=2,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id="image-only-safety-session", payload=Start(tools=[manifest])))
        await incoming.put(image)
        await asyncio.wait_for(reasoner.seen.wait(), timeout=1)
        await asyncio.sleep(0.05)
        assert agent.state.correction_pending
        assert not agent.executor.calls
        assert not agent.executor.effects
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id="image-only-safety-session"))
        await asyncio.wait_for(task, timeout=1)



async def test_partial_speech_and_final_image_never_authorize_a_write(tmp_path: Path):
    class LocalVision:
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            assert path.parent == tmp_path
            return "Wednesday appointment"

    class SafetyReasoner:
        def __init__(self):
            self.plans = [
                PlanProposal(),
                PlanProposal(
                    intent="service",
                    slot_updates={"day": "Wednesday"},
                    request_complete=True,
                    write_requested=True,
                    calls=[
                        ProposedCall(
                            tool="calendar",
                            arguments={"day": "Wednesday"},
                            dependencies=["day"],
                        )
                    ],
                ),
            ]
            self.views = []

        async def plan(self, view, manifests):
            self.views.append(view.model_copy(deep=True))
            return self.plans.pop(0)

    manifest = ToolManifest(
        name="calendar",
        description="Test calendar service",
        effect="write",
        timeout_s=1,
        parameters={
            "type": "object",
            "properties": {"day": {"type": "string"}},
            "required": ["day"],
            "additionalProperties": False,
        },
    )
    png = _png_bytes(width=2, height=3)
    encoded_image = base64.b64encode(png).decode("ascii")
    session_id = "partial-image-safety-session"
    partial = event_from_message(
        session_id,
        {
            "kind": "transcript",
            "payload": {
                "utterance_id": "utterance-1",
                "text": "Book the date shown in this image",
                "final": False,
            },
        },
    )
    image = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"data_base64": encoded_image, "frame_id": "frame-1"}},
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    reasoner = SafetyReasoner()
    applied = asyncio.Event()

    class ObservedAgent(Agent):
        async def _apply(self, proposal, *args, **kwargs):
            await super()._apply(proposal, *args, **kwargs)
            applied.set()

    agent = ObservedAgent(
        DemoPerception(vision_backend=LocalVision()),
        FinalFlagPolicy(),
        reasoner,
        FakeTools(),
        MockOnlyAuthorization(),
        scenario_timeout=2,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start(tools=[manifest])))
        await incoming.put(partial)
        await asyncio.wait_for(applied.wait(), timeout=1)
        applied.clear()
        await incoming.put(image)
        await asyncio.wait_for(applied.wait(), timeout=1)
        assert agent.state.correction_pending
        assert not agent.executor.calls
        assert not agent.executor.effects
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="The current controller does not represent conflicting frame evidence before a write.",
)
async def test_conflicting_frames_require_resolution_before_write(tmp_path: Path):
    class ConflictingVision:
        backend_name = "local/injected-vision"

        def __call__(self, path: Path) -> str:
            return "Wednesday" if path.name == "second.png" else "Tuesday"

    class ConflictReasoner:
        def __init__(self):
            self.conflict_seen = asyncio.Event()

        async def plan(self, view, manifests):
            frame_ids = {item.source_id for item in view.observations if item.modality == "image"}
            if {"frame-1", "frame-2"} <= frame_ids:
                self.conflict_seen.set()
                return PlanProposal(
                    intent="service",
                    slot_updates={"day": "Wednesday"},
                    request_complete=True,
                    write_requested=True,
                    calls=[
                        ProposedCall(
                            tool="calendar",
                            arguments={"day": "Wednesday"},
                            dependencies=["day"],
                        )
                    ],
                )
            return PlanProposal()

    manifest = ToolManifest(
        name="calendar",
        description="Test calendar service",
        effect="write",
        timeout_s=1,
        parameters={
            "type": "object",
            "properties": {"day": {"type": "string"}},
            "required": ["day"],
            "additionalProperties": False,
        },
    )
    session_id = "conflicting-frame-session"
    transcript = event_from_message(
        session_id,
        {
            "kind": "transcript",
            "payload": {
                "utterance_id": "utterance-1",
                "text": "Book the appointment using the date shown on screen",
                "final": True,
            },
        },
    )
    frame_one = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "first.png", "frame_id": "frame-1"}},
        media_root=tmp_path,
    )
    frame_two = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "second.png", "frame_id": "frame-2"}},
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    reasoner = ConflictReasoner()
    executor = FakeTools()
    agent = Agent(
        DemoPerception(vision_backend=ConflictingVision()),
        FinalFlagPolicy(),
        reasoner,
        executor,
        MockOnlyAuthorization(),
        scenario_timeout=2,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start(tools=[manifest])))
        await incoming.put(transcript)
        await incoming.put(frame_one)
        await incoming.put(frame_two)
        await asyncio.wait_for(reasoner.conflict_seen.wait(), timeout=1)
        await asyncio.sleep(0.05)
        assert not executor.calls
        assert not executor.effects
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="The current Agent retains prior frame observations when the active frame changes.",
)
async def test_new_frame_replaces_previous_frame_in_reasoner_context(tmp_path: Path):
    class FrameReasoner:
        def __init__(self):
            self.views = []
            self.frame_one_seen = asyncio.Event()
            self.frame_two_seen = asyncio.Event()

        async def plan(self, view, manifests):
            snapshot = view.model_copy(deep=True)
            self.views.append(snapshot)
            frame_ids = [item.source_id for item in snapshot.observations if item.modality == "image"]
            if "frame-1" in frame_ids:
                self.frame_one_seen.set()
            if "frame-2" in frame_ids:
                self.frame_two_seen.set()
            return PlanProposal()

    session_id = "changed-frame-session"
    frame_one = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "first.png", "frame_id": "frame-1"}},
        media_root=tmp_path,
    )
    frame_two = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "second.png", "frame_id": "frame-2"}},
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    reasoner = FrameReasoner()
    agent = Agent(
        DemoPerception(),
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=1,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start()))
        await incoming.put(frame_one)
        await asyncio.wait_for(reasoner.frame_one_seen.wait(), timeout=1)
        await incoming.put(frame_two)
        await asyncio.wait_for(reasoner.frame_two_seen.wait(), timeout=1)
        latest_view = reasoner.views[-1]
        assert [item.source_id for item in latest_view.observations if item.modality == "image"] == [
            "frame-2"
        ]
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="The current Agent only emits informational responses after completed speech.",
)
async def test_image_only_informational_response_needs_additive_controller_support(tmp_path: Path):
    class ImageOnlyReasoner:
        def __init__(self):
            self.view = None
            self.seen = asyncio.Event()

        async def plan(self, view, manifests):
            self.view = view.model_copy(deep=True)
            self.seen.set()
            return PlanProposal(
                response="Screen evidence is available.",
                request_complete=True,
            )

    session_id = "image-only-session"
    image_event = event_from_message(
        session_id,
        {"kind": "frame", "payload": {"path": "screen.png", "frame_id": "frame-only"}},
        media_root=tmp_path,
    )
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    reasoner = ImageOnlyReasoner()
    agent = Agent(
        DemoPerception(),
        FinalFlagPolicy(),
        reasoner,
        scenario_timeout=1,
        inference_timeout=1,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id=session_id, payload=Start()))
        await incoming.put(image_event)
        await asyncio.wait_for(reasoner.seen.wait(), timeout=1)
        assert reasoner.view is not None
        assert [item.modality for item in reasoner.view.observations] == ["image"]
        await asyncio.sleep(0.05)
        outputs = []
        while not outgoing.empty():
            outputs.append(outgoing.get_nowait())
        assert any(item.kind == "final" for item in outputs)
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        await asyncio.wait_for(task, timeout=1)


def test_browser_path_is_not_used_when_session_upload_root_exists(tmp_path: Path):
    event = event_from_message(
        "session-1",
        {"kind": "audio", "payload": {"path": r"C:\private\recording.wav"}},
        media_root=tmp_path,
    )

    materialized = Path(event.payload.path)
    assert materialized == tmp_path / "browser-mock.wav"
    assert "private" not in str(materialized)


def test_browser_audio_upload_is_materialized_and_validated(tmp_path: Path):
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded = base64.b64encode(fixture.read_bytes()).decode("ascii")

    event = event_from_message(
        "session-1",
        {"kind": "audio", "payload": {"data_base64": encoded, "utterance_id": "upload-1"}},
        media_root=tmp_path,
    )

    materialized = Path(event.payload.path)
    assert materialized.parent == tmp_path
    assert materialized.suffix == ".wav"
    assert materialized.read_bytes() == fixture.read_bytes()
    assert event.payload.utterance_id == "upload-1"


def test_browser_png_upload_is_materialized_and_validated(tmp_path: Path):
    png = _png_bytes(width=2, height=3)
    encoded = base64.b64encode(png).decode("ascii")

    event = event_from_message(
        "session-1",
        {"kind": "frame", "payload": {"data_base64": encoded, "frame_id": "upload-frame"}},
        media_root=tmp_path,
    )

    materialized = Path(event.payload.path)
    assert materialized.parent == tmp_path
    assert materialized.suffix == ".png"
    assert materialized.read_bytes() == png
    assert event.payload.frame_id == "upload-frame"


def test_browser_media_upload_rejects_oversized_encoded_payload(tmp_path: Path):
    oversized = "A" * (demo_app.MAX_BASE64_CHARS + 1)

    with pytest.raises(ValueError, match="8 MiB limit"):
        event_from_message(
            "session-1",
            {"kind": "frame", "payload": {"data_base64": oversized}},
            media_root=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_browser_media_upload_rejects_wrong_file_type(tmp_path: Path):
    encoded = base64.b64encode(b"not media").decode("ascii")

    with pytest.raises(ValueError, match="RIFF WAV"):
        event_from_message(
            "session-1",
            {"kind": "audio", "payload": {"data_base64": encoded}},
            media_root=tmp_path,
        )
