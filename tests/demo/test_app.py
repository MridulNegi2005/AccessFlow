import base64
import importlib.util
import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from accessflow.contracts import AudioEvent, FrameEvent, Observation, TranscriptEvent


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


def test_demo_page_exposes_all_mock_input_controls():
    html = Path("demo/index.html").read_text(encoding="utf-8")

    assert 'id="text-form"' in html
    assert 'accept="audio/wav,.wav"' in html
    assert 'accept="image/png,.png"' in html
    assert 'id="mic"' in html
    assert 'id="stop-mic"' in html
    assert 'getUserMedia' in html
    assert 'encodeWav' in html


def test_websocket_returns_controller_output_event():
    with TestClient(demo_app.app) as client:
        with client.websocket_connect("/ws") as socket:
            socket.send_json({"kind": "transcript", "payload": {"text": "Book Wednesday"}})
            received = [socket.receive_json(), socket.receive_json()]

    assert {item["kind"] for item in received} == {"acknowledge", "final"}
    final = next(item for item in received if item["kind"] == "final")
    assert final["payload"]["basis"] == "informational"
    assert final["state"]["status"] == "listening"

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
