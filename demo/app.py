"""Minimal browser demo backed by the real queue-based controller and labeled mocks."""

from __future__ import annotations

import asyncio
import base64
import os
import binascii
import importlib.util
import math
import tempfile
import threading
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
    Interrupt,
    InterruptEvent,
    Observation,
    OutputEvent,
    PlanProposal,
    Start,
    StartEvent,
    Transcript,
    TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, FinalFlagPolicy, MockOnlyAuthorization
from accessflow.perception import LocalPerception, OllamaVisionProvider, validate_png, validate_wav

ROOT = Path(__file__).parent
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SESSION_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_BASE64_CHARS = 4 * ((MAX_UPLOAD_BYTES + 2) // 3)
MAX_CONTEXT_CHARS = 16_384
MAX_PENDING_INPUTS = 16
MAX_PENDING_OUTPUTS = 16

_reasoner_spec = importlib.util.spec_from_file_location(
    "accessflow_demo_reasoner", ROOT / "reasoner.py"
)
if _reasoner_spec is None or _reasoner_spec.loader is None:
    raise ImportError("Unable to load the demo reasoner")
_reasoner_module = importlib.util.module_from_spec(_reasoner_spec)
_reasoner_spec.loader.exec_module(_reasoner_module)
MAX_REASONER_CONTEXT_CHARS = _reasoner_module.MAX_REASONER_CONTEXT_CHARS
MAX_REASONER_RESPONSE_BYTES = _reasoner_module.MAX_REASONER_RESPONSE_BYTES
OllamaReasoner = _reasoner_module.OllamaReasoner

app = FastAPI(title="AccessFlow mock demo")


class DemoPerception:
    """Demo adapter with an explicit mock default and optional local audio."""

    def __init__(self, *, audio_backend=None, vision_backend=None):
        self._audio_backend = audio_backend
        self._vision_backend = vision_backend
        self._closed = False
        self._vision_perception = (
            LocalPerception(vision_provider=vision_backend)
            if vision_backend is not None
            else None
        )

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        backends = [self._audio_backend, self._vision_perception]
        closers = [getattr(backend, "aclose", None) for backend in backends]
        await asyncio.gather(
            *(closer() for closer in closers if closer is not None),
            return_exceptions=True,
        )

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
        if self._audio_backend is None:
            labels.append("demo/mock audio")
        else:
            audio_backend_name = getattr(self._audio_backend, "audio_backend_name", None)
            if audio_backend_name == "faster-whisper/cpu-int8":
                labels.append("local/Faster Whisper CPU INT8 audio")
            elif audio_backend_name:
                labels.append(f"{audio_backend_name} audio")
            else:
                labels.append("local/unknown-audio")
        if self._vision_backend is None:
            labels.append("demo/mock text/image")
        else:
            vision_model = getattr(self._vision_backend, "model", None)
            vision_backend_name = getattr(self._vision_backend, "backend_name", None)
            if vision_backend_name and vision_backend_name.startswith("ollama/") and vision_model:
                labels.append(f"local/Ollama {vision_model} image")
            elif vision_backend_name:
                labels.append(f"{vision_backend_name} image")
            else:
                labels.append("local/unknown-vision image")
        return " + ".join(labels)

    async def observe(self, event):
        if self._closed:
            return
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
                async for observation in self._vision_perception.observe(event):
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

    @property
    def backend_name(self):
        return "demo/mock-reasoner"

    @classmethod
    def from_environment(cls):
        model = os.environ.get("ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL", "").strip()
        if not model:
            return cls()
        return OllamaReasoner(
            model=model,
            endpoint=os.environ.get(
                "ACCESSFLOW_DEMO_OLLAMA_REASONER_ENDPOINT",
                "http://127.0.0.1:11434/api/generate",
            ),
        )

    async def plan(self, view, manifests) -> PlanProposal:
        latest = view.observations[-1]
        context_items = []
        context_chars = 0
        for observation in reversed(view.observations[:-1]):
            item = f"{observation.modality}: {observation.text}"
            separator = 2 if context_items else 0
            available = MAX_CONTEXT_CHARS - context_chars - separator
            if available <= 0:
                break
            if len(item) > available:
                item = item[:available]
                context_items.append(item)
                break
            context_items.append(item)
            context_chars += separator + len(item)
        prior_context = "; ".join(reversed(context_items))
        context_suffix = f" | multimodal context: {prior_context}" if prior_context else ""
        return PlanProposal(
            response=f"Mock agent received {latest.modality} input: {latest.text}{context_suffix}",
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


class _SessionMediaBudget:
    def __init__(self, limit: int = MAX_SESSION_UPLOAD_BYTES):
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()

    def reserve(self, size: int) -> None:
        with self._lock:
            if self.used + size > self.limit:
                raise ValueError("session media exceeds the 16 MiB aggregate limit")
            self.used += size

    def release(self, size: int) -> None:
        with self._lock:
            self.used -= size


def _materialize_upload(
    kind: str,
    payload: dict[str, Any],
    media_root: Path | None,
    *,
    media_budget: _SessionMediaBudget | None = None,
) -> str:
    data = payload.get("data_base64")
    if data is None:
        fallback = "browser-mock.wav" if kind == "audio" else "browser-mock.png"
        if media_root is None:
            return payload.get("path", fallback)
        return str(media_root / fallback)
    if media_root is None:
        raise ValueError("media upload requires a session directory")
    if not isinstance(data, str):
        raise ValueError("media upload must be base64 text")
    if len(data) > MAX_BASE64_CHARS:
        raise ValueError("media upload exceeds the 8 MiB limit or is empty")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("media upload is not valid base64") from error
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("media upload exceeds the 8 MiB limit or is empty")

    if media_budget is not None:
        media_budget.reserve(len(raw))
    materialized_path: Path | None = None
    try:
        if kind == "audio":
            if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
                raise ValueError("audio upload must be a RIFF WAV file")
            materialized_path = media_root / f"audio-{uuid.uuid4().hex}.wav"
            materialized_path.write_bytes(raw)
            try:
                validate_wav(materialized_path)
            except ValueError as error:
                raise ValueError("audio upload must be a valid PCM WAV file") from error
            return str(materialized_path)

        if kind == "frame":
            materialized_path = media_root / f"frame-{uuid.uuid4().hex}.png"
            materialized_path.write_bytes(raw)
            try:
                validate_png(materialized_path)
            except ValueError as error:
                raise ValueError("image upload must be a valid PNG file") from error
            return str(materialized_path)
        raise ValueError(f"Unsupported upload kind: {kind}")
    except Exception:
        if materialized_path is not None:
            materialized_path.unlink(missing_ok=True)
        if media_budget is not None:
            media_budget.release(len(raw))
        raise


def _source_id(payload: dict[str, Any], key: str) -> str:
    """Return a generated identity for omitted IDs and reject blank identities."""
    if key not in payload:
        return str(uuid.uuid4())
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"browser {key} must be a non-empty string")
    return value


def _finite_timestamp(value: Any, key: str) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"browser {key} must be a finite non-negative number")
    return value


def _revision(payload: dict[str, Any]) -> int:
    value = payload.get("revision", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("browser revision must be a non-negative integer")
    return value


def _sequence(message: dict[str, Any]) -> int:
    value = message.get("sequence", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("browser sequence must be a non-negative integer")
    return value


def _final_flag(payload: dict[str, Any]) -> bool:
    value = payload.get("final", True)
    if not isinstance(value, bool):
        raise ValueError("browser final must be a boolean")
    return value


def _text(payload: dict[str, Any]) -> str:
    value = payload.get("text", "")
    if not isinstance(value, str):
        raise ValueError("browser text must be a string")
    return value


def _interrupt_scope(payload: dict[str, Any]) -> str:
    value = payload.get("scope", "speech")
    if not isinstance(value, str) or value not in {"speech", "task"}:
        raise ValueError("browser interrupt scope must be 'speech' or 'task'")
    return value


def _optional_source_id(payload: dict[str, Any], key: str) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"browser {key} must be a non-empty string when provided")
    return value


def event_from_message(
    session_id: str,
    message: dict[str, Any],
    *,
    media_root: Path | None = None,
    media_budget: _SessionMediaBudget | None = None,
):
    """Translate browser messages into typed v0.1 input events."""
    if not isinstance(message, dict):
        raise ValueError("browser event must be a JSON object")
    kind = message.get("kind")
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("browser event payload must be an object")
    timestamp = _finite_timestamp(
        message.get("timestamp", payload.get("timestamp", 0)), "timestamp"
    )
    sequence = _sequence(message)
    if kind == "interrupt":
        return InterruptEvent(
            session_id=session_id,
            timestamp=timestamp,
            sequence=sequence,
            payload=Interrupt(
                scope=_interrupt_scope(payload),
                utterance_id=_optional_source_id(payload, "utterance_id"),
            ),
        )
    if kind == "transcript":
        speech_start = _finite_timestamp(payload.get("speech_start", 0), "speech_start")
        speech_end = _finite_timestamp(payload.get("speech_end", 0), "speech_end")
        if speech_end < speech_start:
            raise ValueError("browser speech_end must be at least speech_start")
        return TranscriptEvent(
            session_id=session_id,
            timestamp=timestamp,
            sequence=sequence,
            payload=Transcript(
                utterance_id=_source_id(payload, "utterance_id"),
                revision=_revision(payload),
                text=_text(payload),
                final=_final_flag(payload),
                speech_start=speech_start,
                speech_end=speech_end,
            ),
        )
    if kind == "audio":
        speech_start = _finite_timestamp(payload.get("speech_start", 0), "speech_start")
        speech_end = _finite_timestamp(payload.get("speech_end", 0), "speech_end")
        if speech_end < speech_start:
            raise ValueError("browser speech_end must be at least speech_start")
        utterance_id = _source_id(payload, "utterance_id")
        revision = _revision(payload)
        return AudioEvent(
            session_id=session_id,
            timestamp=timestamp,
            sequence=sequence,
            payload=Audio(
                path=_materialize_upload("audio", payload, media_root, media_budget=media_budget),
                utterance_id=utterance_id,
                revision=revision,
                speech_start=speech_start,
                speech_end=speech_end,
            ),
        )
    if kind == "frame":
        frame_id = _source_id(payload, "frame_id")
        return FrameEvent(
            session_id=session_id,
            timestamp=timestamp,
            sequence=sequence,
            payload=Frame(
                path=_materialize_upload("frame", payload, media_root, media_budget=media_budget),
                frame_id=frame_id,
            ),
        )
    raise ValueError(f"Unsupported browser event: {kind}")


async def _materialize_event(
    session_id: str,
    message: dict[str, Any],
    media_root: Path,
    active_tasks: set[asyncio.Task[Any]],
    media_budget: _SessionMediaBudget | None = None,
):
    """Keep threaded upload materialization alive if the receiver is cancelled."""
    task = asyncio.create_task(
        asyncio.to_thread(
            event_from_message,
            session_id,
            message,
            media_root=media_root,
            media_budget=media_budget,
        )
    )
    active_tasks.add(task)
    try:
        return await asyncio.shield(task)
    finally:
        if task.done():
            active_tasks.discard(task)


@app.websocket("/ws")
async def websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = str(uuid.uuid4())
    incoming: asyncio.Queue = asyncio.Queue(maxsize=MAX_PENDING_INPUTS)
    outgoing: asyncio.Queue = asyncio.Queue(maxsize=MAX_PENDING_OUTPUTS)

    async def send_outputs():
        while True:
            event = await outgoing.get()
            if event is None:
                return
            if isinstance(event, OutputEvent):
                event = event.model_dump(mode="json")
            try:
                await websocket.send_json(event)
            except Exception:
                # A closed peer makes the transport unusable; route cleanup owns shutdown.
                return

    sender = asyncio.create_task(send_outputs())
    try:
        perception = DemoPerception.from_environment()
        reasoner_factory = getattr(DemoReasoner, "from_environment", None)
        reasoner = reasoner_factory() if callable(reasoner_factory) else DemoReasoner()
    except ValueError as error:
        await outgoing.put(
            {"kind": "demo_error", "payload": {"backend": "demo/config", "message": str(error)}}
        )
        await outgoing.put(None)
        await asyncio.gather(sender, return_exceptions=True)
        await websocket.close(code=1008)
        return
    await outgoing.put(
        {
            "kind": "demo_status",
            "payload": {
                "perception_backend": perception.backend_label,
                "reasoner_backend": getattr(reasoner, "backend_name", "demo/unknown-reasoner"),
            },
        }
    )
    agent = Agent(
        perception,
        FinalFlagPolicy(),
        reasoner,
        FakeTools(),
        MockOnlyAuthorization(),
    )
    agent_task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id=session_id, payload=Start()))

    with tempfile.TemporaryDirectory(prefix="accessflow-demo-") as media_dir:
        media_root = Path(media_dir)
        media_budget = _SessionMediaBudget()
        materialization_tasks: set[asyncio.Task[Any]] = set()

        async def receive_inputs():
            while True:
                try:
                    message = await websocket.receive_json()
                except ValueError:
                    await outgoing.put(
                        {
                            "kind": "demo_error",
                            "payload": {
                                "backend": "demo/input",
                                "message": "browser event must be valid JSON",
                            },
                        }
                    )
                    continue
                try:
                    event = await _materialize_event(
                        session_id,
                        message,
                        media_root,
                        materialization_tasks,
                        media_budget,
                    )
                except (TypeError, ValueError) as error:
                    await outgoing.put(
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
                    await outgoing.put(
                        {
                            "kind": "demo_status",
                            "payload": {"media_received": event.kind, "source_id": source_id},
                        }
                    )
                await incoming.put(event)

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
            for task in (receiver,):
                if not task.done():
                    task.cancel()
            await asyncio.gather(receiver, return_exceptions=True)
            if materialization_tasks:
                await asyncio.gather(*materialization_tasks, return_exceptions=True)
                materialization_tasks.clear()

            if agent.running and not agent_task.done():
                await incoming.put(EndEvent(session_id=session_id))
            if not agent_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(agent_task), timeout=1)
                except (asyncio.TimeoutError, RuntimeError):
                    agent_task.cancel()
            await asyncio.gather(agent_task, return_exceptions=True)
            if not sender.done():
                await outgoing.put(None)
            await asyncio.gather(sender, return_exceptions=True)
            await perception.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=False)
