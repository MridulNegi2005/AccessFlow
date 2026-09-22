from __future__ import annotations

import argparse
import base64
import json
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from accessflow.adapters.process_perception import ProcessPerception
from accessflow.adapters import perception_worker
from accessflow.contracts import Frame, FrameEvent


def _write_png(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"\x00\x40\x80\xff\xff"))
        + chunk(b"IEND", b"")
    )


class _VisionHandler(BaseHTTPRequestHandler):
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        self.__class__.requests.append(json.loads(self.rfile.read(length)))
        body = json.dumps({"message": {"content": "A fixture panel is visible."}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


async def _one(adapter: ProcessPerception, event: FrameEvent):
    return [item async for item in adapter.observe(event)]


def test_worker_defaults_to_audio_only(monkeypatch, tmp_path: Path):
    captured = {}

    class StubPerception:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(perception_worker, "LocalPerception", StubPerception)

    perception_worker._build_perception(tmp_path)

    assert captured == {"model_path": tmp_path}


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "fast"])
def test_worker_rejects_invalid_vision_timeout(value: str):
    with pytest.raises(argparse.ArgumentTypeError, match="finite positive"):
        perception_worker._positive_timeout(value)


@pytest.mark.asyncio
async def test_configured_vision_runs_through_actual_child(tmp_path: Path):
    _VisionHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _VisionHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    image_path = tmp_path / "panel.png"
    _write_png(image_path)
    model_path = tmp_path / "model"
    model_path.mkdir()
    adapter = ProcessPerception(
        model_path=model_path,
        worker_args=(
            "--vision-provider",
            "ollama",
            "--vision-model",
            "fixture:vision",
            "--vision-url",
            f"http://127.0.0.1:{server.server_port}",
            "--vision-timeout",
            "3",
        ),
    )
    event = FrameEvent(
        session_id="s1",
        event_id="frame-event",
        timestamp=4.5,
        payload=Frame(path=str(image_path), frame_id="frame-1"),
    )
    try:
        observations = await _one(adapter, event)
    finally:
        await adapter.aclose()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert len(observations) == 1
    assert observations[0].text == "A fixture panel is visible."
    assert observations[0].backend == "ollama/fixture:vision"
    assert observations[0].source_id == "frame-1"
    assert _VisionHandler.requests[0]["model"] == "fixture:vision"
    assert _VisionHandler.requests[0]["messages"][0]["images"] == [
        base64.b64encode(image_path.read_bytes()).decode("ascii")
    ]
