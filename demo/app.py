"""Minimal browser demo backed by the real queue-based controller and labeled mocks."""

from __future__ import annotations

import asyncio
import base64
import os
import binascii
import struct
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from accessflow.contracts import (
    Audio,
    AudioEvent,
    EndEvent,
    Frame,
    FrameEvent,
    Observation,
    PlanProposal,
    Start,
    StartEvent,
    Transcript,
    TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, FinalFlagPolicy, MockOnlyAuthorization
from accessflow.perception import LocalPerception, OllamaVisionProvider, validate_wav

ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
app = FastAPI(title="AccessFlow mock demo")


class DemoPerception:
    """Demo adapter with an explicit mock default and optional local audio."""

    def __init__(self, *, audio_backend=None, vision_backend=None):
        self._audio_backend = audio_backend
        self._vision_backend = vision_backend

    @classmethod
    def from_environment(cls):
        model_path = os.environ.get("ACCESSFLOW_DEMO_WHISPER_MODEL", "").strip()
        if not model_path:
            audio_backend = None
        else:
            resolved_model_path = Path(model_path).expanduser()
        if model_path and not resolved_model_path.is_dir():
            raise ValueError(
                "ACCESSFLOW_DEMO_WHISPER_MODEL must point to an existing local model directory"
            )
        if model_path:
            audio_backend = LocalPerception(model_path=resolved_model_path)

        vision_model = os.environ.get("ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL", "").strip()
        vision_backend = None
        if vision_model:
            vision_backend = OllamaVisionProvider(
                model=vision_model,
                endpoint=os.environ.get(
                    "ACCESSFLOW_DEMO_OLLAMA_ENDPOINT",
                    "http://127.0.0.1:11434/api/generate",
                ),
            )
        return cls(audio_backend=audio_backend, vision_backend=vision_backend)

    @property
    def backend_label(self):
        if self._audio_backend is None and self._vision_backend is None:
            return "demo/mock"
        labels = []
        labels.append(
            "local/Faster Whisper CPU INT8 audio"
            if self._audio_backend is not None
            else "demo/mock audio"
        )
        labels.append(
            f"local/Ollama {self._vision_backend.model} image"
            if self._vision_backend is not None
            else "demo/mock text/image"
        )
        return " + ".join(labels)

    async def observe(self, event):
        if isinstance(event, TranscriptEvent):
            payload = event.payload
            yield Observation(
                event_id=event.event_id,
                source_id=payload.utterance_id,
                revision=payload.revision,
                modality="text",
                text=payload.text,
                final=payload.final,
                speech_start=payload.speech_start,
                speech_end=payload.speech_end,
                backend="demo/mock-text",
            )
            return
        if isinstance(event, AudioEvent):
            if self._audio_backend is not None:
                async for observation in self._audio_backend.observe(event):
                    yield observation
                return
            payload = event.payload
            yield Observation(
                event_id=event.event_id,
                source_id=payload.utterance_id,
                revision=payload.revision,
                modality="audio",
                text=f"Mock audio input received: {Path(payload.path).name}",
                final=True,
                speech_start=payload.speech_start,
                speech_end=payload.speech_end,
                backend="demo/mock-audio",
            )
            return
        if isinstance(event, FrameEvent):
            if self._vision_backend is not None:
                async for observation in LocalPerception(
                    vision_provider=self._vision_backend
                ).observe(event):
                    yield observation
                return
            payload = event.payload
            yield Observation(
                event_id=event.event_id,
                source_id=payload.frame_id,
                revision=0,
                modality="image",
                text=f"Mock image input received: {Path(payload.path).name}",
                final=True,
                speech_start=event.timestamp,
                speech_end=event.timestamp,
                backend="demo/mock-image",
            )
            return
        raise ValueError(f"Unsupported demo event: {event.kind}")


class DemoReasoner:
    """Return a visible mock response while the real reasoner is developed separately."""

    async def plan(self, view, manifests) -> PlanProposal:
        latest = view.observations[-1]
        return PlanProposal(
            response=f"Mock agent received {latest.modality} input: {latest.text}",
            request_complete=True,
        )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/favicon.svg")
async def favicon() -> FileResponse:
    return FileResponse(ROOT / "favicon.svg", media_type="image/svg+xml")


@app.get("/recorder-worklet.js")
async def recorder_worklet() -> FileResponse:
    return FileResponse(ROOT / "recorder-worklet.js", media_type="application/javascript")


def _materialize_upload(kind: str, payload: dict[str, Any], media_root: Path | None) -> str:
    data = payload.get("data_base64")
    if data is None:
        fallback = "browser-mock.wav" if kind == "audio" else "browser-mock.png"
        if media_root is None:
            return payload.get("path", fallback)
        return str(media_root / fallback)
    if media_root is None:
        raise ValueError("media upload requires a session directory")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("media upload is not valid base64") from error
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("media upload exceeds the 8 MiB limit or is empty")

    if kind == "audio":
        if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
            raise ValueError("audio upload must be a RIFF WAV file")
        path = media_root / f"audio-{uuid.uuid4().hex}.wav"
        path.write_bytes(raw)
        validate_wav(path)
        return str(path)

    if kind == "frame":
        if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
            raise ValueError("image upload must be a PNG file")
        width, height = struct.unpack(">II", raw[16:24])
        if width < 1 or height < 1:
            raise ValueError("image upload has invalid dimensions")
        path = media_root / f"frame-{uuid.uuid4().hex}.png"
        path.write_bytes(raw)
        return str(path)

    raise ValueError(f"Unsupported upload kind: {kind}")


def event_from_message(
    session_id: str,
    message: dict[str, Any],
    *,
    media_root: Path | None = None,
):
    """Translate browser messages into typed v0.1 input events."""
    kind = message.get("kind")
    payload = message.get("payload", {})
    if kind == "transcript":
        return TranscriptEvent(
            session_id=session_id,
            payload=Transcript(
                utterance_id=payload.get("utterance_id", str(uuid.uuid4())),
                revision=payload.get("revision", 0),
                text=payload.get("text", ""),
                final=payload.get("final", True),
                speech_start=payload.get("speech_start", 0),
                speech_end=payload.get("speech_end", 0),
            ),
        )
    if kind == "audio":
        return AudioEvent(
            session_id=session_id,
            payload=Audio(
                path=_materialize_upload("audio", payload, media_root),
                utterance_id=payload.get("utterance_id", str(uuid.uuid4())),
                revision=payload.get("revision", 0),
            ),
        )
    if kind == "frame":
        return FrameEvent(
            session_id=session_id,
            payload=Frame(
                path=_materialize_upload("frame", payload, media_root),
                frame_id=payload.get("frame_id", str(uuid.uuid4())),
            ),
        )
    raise ValueError(f"Unsupported browser event: {kind}")


@app.websocket("/ws")
async def websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = str(uuid.uuid4())
    incoming: asyncio.Queue = asyncio.Queue()
    outgoing: asyncio.Queue = asyncio.Queue()
    try:
        perception = DemoPerception.from_environment()
    except ValueError as error:
        await websocket.send_json(
            {"kind": "demo_error", "payload": {"backend": "demo/config", "message": str(error)}}
        )
        await websocket.close(code=1008)
        return
    await websocket.send_json({"kind": "demo_status", "payload": {"perception_backend": perception.backend_label}})
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        DemoReasoner(),
        FakeTools(),
        MockOnlyAuthorization(),
    )
    agent_task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id=session_id, payload=Start()))

    async def send_outputs():
        while True:
            event = await outgoing.get()
            await websocket.send_json(event.model_dump(mode="json"))

    with tempfile.TemporaryDirectory(prefix="accessflow-demo-") as media_dir:
        media_root = Path(media_dir)

        async def receive_inputs():
            while True:
                message = await websocket.receive_json()
                try:
                    event = event_from_message(
                        session_id,
                        message,
                        media_root=media_root,
                    )
                except (TypeError, ValueError) as error:
                    await websocket.send_json(
                        {
                            "kind": "demo_error",
                            "payload": {"backend": "demo/input", "message": str(error)},
                        }
                    )
                    continue
                if isinstance(event, AudioEvent):
                    source_id = event.payload.utterance_id
                elif isinstance(event, FrameEvent):
                    source_id = event.payload.frame_id
                else:
                    source_id = None
                if source_id is not None:
                    await websocket.send_json(
                        {
                            "kind": "demo_status",
                            "payload": {"media_received": event.kind, "source_id": source_id},
                        }
                    )
                await incoming.put(event)

        sender = asyncio.create_task(send_outputs())
        receiver = asyncio.create_task(receive_inputs())
        try:
            done, _ = await asyncio.wait(
                {sender, receiver, agent_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                if not task.cancelled() and task.exception():
                    raise task.exception()
        except (WebSocketDisconnect, RuntimeError, ValueError):
            pass
        finally:
            for task in (sender, receiver):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)

            if agent.running and not agent_task.done():
                await incoming.put(EndEvent(session_id=session_id))
            if not agent_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(agent_task), timeout=1)
                except (asyncio.TimeoutError, RuntimeError):
                    agent_task.cancel()
            await asyncio.gather(agent_task, return_exceptions=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=False)
