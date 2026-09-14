import asyncio
import base64
import importlib.util
import struct
from pathlib import Path

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


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("transcript", TranscriptEvent), ("audio", AudioEvent), ("frame", FrameEvent)],
)
def test_browser_message_becomes_typed_event(kind, expected):
    event = event_from_message("session-1", {"kind": kind, "payload": {"path": "input"}})

    assert isinstance(event, expected)
    assert event.session_id == "session-1"


@pytest.mark.asyncio
async def test_demo_perception_can_delegate_audio_to_injected_local_backend():
    class LocalAudio:
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
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 4, 5)
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
        {"kind": "frame", "payload": {"path": "device.png", "frame_id": "frame-9"}},
    )

    observations = [item async for item in DemoPerception().observe(event)]

    assert len(observations) == 1
    observation: Observation = observations[0]
    assert observation.source_id == "frame-9"
    assert observation.revision == 0
    assert observation.modality == "image"
    assert observation.backend == "demo/mock-image"
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



def test_websocket_png_upload_reaches_mock_controller():
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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


def test_websocket_image_before_audio_context_is_visible():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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



@pytest.mark.xfail(
    strict=True,
    reason="The current Agent retains prior frame observations when the active frame changes.",
)
def test_websocket_new_frame_replaces_previous_frame():
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
async def test_multimodal_audio_revision_replaces_old_speech_and_keeps_frame(tmp_path: Path):
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    encoded_audio = base64.b64encode(fixture.read_bytes()).decode("ascii")
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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
    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 2, 3)
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


def test_browser_media_upload_rejects_wrong_file_type(tmp_path: Path):
    encoded = base64.b64encode(b"not media").decode("ascii")

    with pytest.raises(ValueError, match="RIFF WAV"):
        event_from_message(
            "session-1",
            {"kind": "audio", "payload": {"data_base64": encoded}},
            media_root=tmp_path,
        )
