"""Minimal browser demo backed by the real queue-based controller and labeled mocks."""

from __future__ import annotations

import asyncio
import base64
import os
import binascii
import importlib.util
import json
import math
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from accessflow.adapters.configured_agent import build_configured_agent
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
    SpeechStatus,
    SpeechStatusEvent,
    Start,
    StartEvent,
    ToolManifest,
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
MAX_BROWSER_TEXT_CHARS = MAX_CONTEXT_CHARS
MAX_BROWSER_SOURCE_ID_CHARS = 256
MAX_BROWSER_MESSAGE_BYTES = 12 * 1024 * 1024
MAX_PENDING_INPUTS = 16
MAX_PENDING_OUTPUTS = 16
MAX_PREVIEW_SOURCES = 64

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

app = FastAPI(title="AccessFlow demo")


def _demo_agent_mode() -> str:
    mode = os.environ.get("ACCESSFLOW_DEMO_AGENT_MODE", "mock").strip()
    if mode not in {"mock", "configured"}:
        raise ValueError("ACCESSFLOW_DEMO_AGENT_MODE must be mock or configured")
    return mode


def _mock_external_tools() -> list[ToolManifest]:
    """Only the configured demo advertises this in-memory, non-calendar effect."""
    return [
        ToolManifest(
            name="mock_calendar_create",
            description="Create a mock calendar event in this session only; no real calendar is changed.",
            effect="write",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "date": {"type": "string", "format": "date"},
                    "time": {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"},
                    "timezone": {"type": "string", "minLength": 1},
                    "operation_id": {"type": "string"},
                },
                "required": ["title", "date", "time", "timezone", "operation_id"],
                "additionalProperties": False,
            },
            idempotency_parameter="operation_id",
        ),
    ]


class _ObservedConfiguredPerception:
    """Demo-only final-observation projection; inference remains the factory's."""

    def __init__(self, inner, callback, label: str):
        self.inner = inner
        self.observation_callback = callback
        self.backend_label = label

    def validate_media_source(self, event: Any) -> None:
        if isinstance(event, (AudioEvent, FrameEvent)) and not Path(event.payload.path).is_file():
            raise ValueError("configured perception requires uploaded media bytes")

    async def observe(self, event):
        async for observation in self.inner.observe(event):
            if observation.final:
                self.observation_callback(
                    {
                        "event_id": observation.event_id,
                        "modality": observation.modality,
                        "source_id": observation.source_id,
                        "revision": observation.revision,
                        "text": observation.text,
                        "backend": observation.backend,
                        "final": True,
                    }
                )
            yield observation

    async def aclose(self) -> None:
        await self.inner.aclose()


def _configured_perception_label(agent: Agent) -> str:
    configuration = agent.perception_configuration
    if configuration.mode == "text":
        return "configured/text-only"
    observed = agent.perception_warmup_backends
    labels = [f"audio: {observed.get('audio', 'unverified')}"]
    if configuration.vision_provider != "none":
        labels.append(f"image: {observed.get('image', 'unverified')}")
    return " · ".join(labels)


class DemoPerception:
    """Demo adapter with an explicit mock default and optional local audio."""

    def __init__(self, *, audio_backend=None, vision_backend=None):
        self._audio_backend = audio_backend
        self._vision_backend = vision_backend
        self.observation_callback = None
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

    def validate_media_source(self, event: Any) -> None:
        """Reject placeholder paths before a configured local backend sees them."""
        if (
            isinstance(event, AudioEvent)
            and self._audio_backend is not None
            and not Path(event.payload.path).is_file()
        ):
            raise ValueError("configured audio backend requires uploaded WAV bytes")
        if (
            isinstance(event, FrameEvent)
            and self._vision_backend is not None
            and not Path(event.payload.path).is_file()
        ):
            raise ValueError("configured vision backend requires uploaded PNG bytes")

    def _notify_observation(self, observation: Observation) -> None:
        callback = self.observation_callback
        if not callable(callback) or not observation.final:
            return
        callback(
            {
                "event_id": observation.event_id,
                "modality": observation.modality,
                "source_id": observation.source_id,
                "revision": observation.revision,
                "text": observation.text,
                "backend": observation.backend,
                "final": observation.final,
            }
        )

    async def observe(self, event):
        if self._closed:
            return
        if isinstance(event, TranscriptEvent):
            payload = event.payload
            observation = Observation(
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
            self._notify_observation(observation)
            yield observation
            return
        if isinstance(event, AudioEvent):
            if self._audio_backend is not None:
                async for observation in self._audio_backend.observe(event):
                    self._notify_observation(observation)
                    yield observation
                return
            payload = event.payload
            observation = Observation(
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
            self._notify_observation(observation)
            yield observation
            return
        if isinstance(event, FrameEvent):
            if self._vision_backend is not None:
                async for observation in self._vision_perception.observe(event):
                    self._notify_observation(observation)
                    yield observation
                return
            payload = event.payload
            observation = Observation(
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
            self._notify_observation(observation)
            yield observation
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


@app.get("/design-preview-dog.png")
async def design_preview_dog() -> FileResponse:
    return FileResponse(ROOT / "design-preview-dog.png", media_type="image/png")


@app.get("/recorder-worklet.js")
async def recorder_worklet() -> FileResponse:
    return FileResponse(ROOT / "recorder-worklet.js", media_type="application/javascript")


@app.get("/live-voice.js")
async def live_voice_script() -> FileResponse:
    return FileResponse(ROOT / "live-voice.js", media_type="application/javascript")


@app.get("/attachment-history.js")
async def attachment_history_script() -> FileResponse:
    return FileResponse(ROOT / "attachment-history.js", media_type="application/javascript")


class _SessionMediaBudget:
    """Monotonic per-session admission budget for decoded upload bytes."""

    def __init__(self, limit: int = MAX_SESSION_UPLOAD_BYTES):
        self.limit = limit
        self.used = 0
        self._lock = threading.Lock()

    def reserve(self, size: int) -> None:
        with self._lock:
            if self.used + size > self.limit:
                raise ValueError("session media exceeds the 16 MiB aggregate limit")
            self.used += size


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
        raise


def _source_id(payload: dict[str, Any], key: str) -> str:
    """Return a generated identity for omitted IDs and reject blank identities."""
    if key not in payload:
        return str(uuid.uuid4())
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"browser {key} must be a non-empty string")
    if len(value) > MAX_BROWSER_SOURCE_ID_CHARS:
        raise ValueError(
            f"browser {key} exceeds the {MAX_BROWSER_SOURCE_ID_CHARS}-character limit"
        )
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
    if len(value) > MAX_BROWSER_TEXT_CHARS:
        raise ValueError(
            f"browser text exceeds the {MAX_BROWSER_TEXT_CHARS}-character limit"
        )
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
    if len(value) > MAX_BROWSER_SOURCE_ID_CHARS:
        raise ValueError(
            f"browser {key} exceeds the {MAX_BROWSER_SOURCE_ID_CHARS}-character limit"
        )
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
    if kind == "speech_status":
        status = payload.get("status", "pending")
        if status not in {"pending", "failed"}:
            raise ValueError("browser speech status must be pending or failed")
        return SpeechStatusEvent(
            session_id=session_id,
            timestamp=timestamp,
            sequence=sequence,
            payload=SpeechStatus(
                utterance_id=_source_id(payload, "utterance_id"),
                revision=_revision(payload),
                status=status,
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


async def _receive_browser_message(websocket: WebSocket) -> dict[str, Any]:
    """Decode one bounded browser frame without parsing oversized JSON."""
    receive = getattr(websocket, "receive", None)
    if not callable(receive):
        # Keep lightweight in-process peer doubles compatible with the route tests.
        receive_json = getattr(websocket, "receive_json", None)
        if not callable(receive_json):
            raise RuntimeError("WebSocket does not support receiving browser events")
        parsed = await receive_json()
        if not isinstance(parsed, dict):
            raise ValueError("browser event must be a JSON object")
        return parsed
    message = await receive()
    if message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect(message["code"], message.get("reason"))
    raw = message.get("text")
    if raw is None:
        raw = message.get("bytes")
    if isinstance(raw, str):
        size = len(raw.encode("utf-8"))
    elif isinstance(raw, bytes):
        size = len(raw)
    else:
        raise ValueError("browser event must be a JSON text or bytes frame")
    if size > MAX_BROWSER_MESSAGE_BYTES:
        raise ValueError(
            f"browser event exceeds the {MAX_BROWSER_MESSAGE_BYTES}-byte limit"
        )
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("browser event must be valid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError("browser event must be a JSON object")
    return parsed


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
    perception = None
    agent = None
    mode = None
    try:
        mode = _demo_agent_mode()
        if mode == "configured":
            agent = await build_configured_agent(
                root=Path(os.environ.get("ACCESSFLOW_DEMO_ASSETS_ROOT", ROOT.parent)),
                authorization=MockOnlyAuthorization(),
                executor=FakeTools(),
            )
            perception = agent.perception
            perception_label = _configured_perception_label(agent)
            reasoner_label = agent.reasoner.backend.name
            manifests = _mock_external_tools()
        else:
            perception = DemoPerception.from_environment()
            reasoner_factory = getattr(DemoReasoner, "from_environment", None)
            reasoner = reasoner_factory() if callable(reasoner_factory) else DemoReasoner()
            agent = Agent(
                perception,
                FinalFlagPolicy(),
                reasoner,
                FakeTools(),
                MockOnlyAuthorization(),
            )
            perception_label = perception.backend_label
            reasoner_label = getattr(reasoner, "backend_name", "demo/unknown-reasoner")
            manifests = []
    except Exception as error:
        message = (
            str(error) if isinstance(error, ValueError) and mode == "mock"
            else "Configured agent setup failed. Check local model, provider and service settings."
        )
        await outgoing.put(
            {"kind": "demo_error", "payload": {"backend": "demo/config", "message": message}}
        )
        await outgoing.put(None)
        await asyncio.gather(sender, return_exceptions=True)
        if perception is not None:
            await perception.aclose()
        await websocket.close(code=1008)
        return
    await outgoing.put(
        {
            "kind": "demo_status",
            "session_id": session_id,
            "payload": {
                "agent_mode": mode,
                "tool_environment": "mock",
                "live_preview_available": (
                    mode == "configured" and agent.perception_configuration.mode == "process"
                ),
                "perception_backend": perception_label,
                "reasoner_backend": reasoner_label,
            },
        }
    )

    def enqueue_output(event: Any) -> None:
        try:
            outgoing.put_nowait(event)
        except asyncio.QueueFull as error:
            raise RuntimeError("demo output queue is full") from error

    def observation_callback(payload: dict[str, Any]) -> None:
        enqueue_output(
            {"kind": "demo_observation", "session_id": session_id, "payload": payload}
        )
    if mode == "configured":
        perception = _ObservedConfiguredPerception(
            perception, observation_callback, perception_label
        )
        agent.perception = perception
    else:
        perception.observation_callback = observation_callback
    agent_task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id=session_id, payload=Start(tools=manifests)))

    with tempfile.TemporaryDirectory(prefix="accessflow-demo-") as media_dir:
        media_root = Path(media_dir)
        media_budget = _SessionMediaBudget()
        materialization_tasks: set[asyncio.Task[Any]] = set()
        browser_messages: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=1
        )
        preview_tasks: dict[str, asyncio.Task[None]] = {}
        preview_revisions: dict[str, int] = {}
        preview_available = mode == "configured" and agent.perception_configuration.mode == "process"

        async def process_preview(event: AudioEvent) -> None:
            source_id = event.payload.utterance_id
            revision = event.payload.revision
            try:
                observations = [
                    item async for item in perception.inner.observe(event)
                    if item.event_id == event.event_id and item.source_id == source_id
                    and item.revision == revision and item.modality == "audio" and item.final
                ]
                if len(observations) != 1 or not observations[0].text.strip():
                    raise RuntimeError("preview ASR did not return one usable observation")
                if preview_revisions.get(source_id) != revision:
                    return
                enqueue_output({
                    "kind": "demo_preview", "session_id": session_id,
                    "source_id": source_id, "revision": revision,
                    "text": observations[0].text[:2048], "backend": observations[0].backend,
                })
            except asyncio.CancelledError:
                raise
            except Exception:
                if preview_revisions.get(source_id) == revision:
                    enqueue_output({
                        "kind": "demo_preview", "session_id": session_id,
                        "source_id": source_id, "revision": revision,
                        "error": "A speech preview could not be decoded; keep speaking or try again.",
                    })
            finally:
                if preview_tasks.get(source_id) is asyncio.current_task():
                    preview_tasks.pop(source_id, None)

        async def receive_inputs():
            while True:
                try:
                    message = await _receive_browser_message(websocket)
                except ValueError as error:
                    enqueue_output(
                        {
                            "kind": "demo_error",
                            "payload": {
                                "backend": "demo/input",
                                "message": str(error),
                            },
                        }
                    )
                    continue
                # Keep socket reads independent from media writes so a closed
                # browser can be noticed while an upload is still materializing.
                await browser_messages.put(message)

        async def process_inputs():
            while True:
                message = await browser_messages.get()
                if isinstance(message, dict) and message.get("kind") == "audio_preview":
                    if not preview_available:
                        enqueue_output({
                            "kind": "demo_error",
                            "payload": {
                                "backend": "demo/input",
                                "message": "Live speech preview needs configured process ASR.",
                            },
                        })
                        continue
                    try:
                        preview_message = {**message, "kind": "audio"}
                        event = await _materialize_event(
                            session_id, preview_message, media_root,
                            materialization_tasks, media_budget,
                        )
                        source_id = event.payload.utterance_id
                        revision = event.payload.revision
                        if source_id not in preview_revisions and len(preview_revisions) >= MAX_PREVIEW_SOURCES:
                            raise ValueError("Too many speech previews in this session")
                        if revision <= preview_revisions.get(source_id, -1):
                            continue
                        old = preview_tasks.get(source_id)
                        if old is not None:
                            old.cancel()
                            await asyncio.gather(old, return_exceptions=True)
                        preview_revisions[source_id] = revision
                        preview_tasks[source_id] = asyncio.create_task(process_preview(event))
                    except (TypeError, ValueError) as error:
                        enqueue_output({
                            "kind": "demo_error",
                            "payload": {"backend": "demo/input", "message": str(error)},
                        })
                    continue
                try:
                    event = await _materialize_event(
                        session_id,
                        message,
                        media_root,
                        materialization_tasks,
                        media_budget,
                    )
                    perception.validate_media_source(event)
                except (TypeError, ValueError) as error:
                    enqueue_output(
                        {
                            "kind": "demo_error",
                            "payload": {"backend": "demo/input", "message": str(error)},
                        }
                    )
                    continue
                if isinstance(event, AudioEvent):
                    old = preview_tasks.get(event.payload.utterance_id)
                    if old is not None:
                        old.cancel()
                        await asyncio.gather(old, return_exceptions=True)
                    if event.payload.utterance_id in preview_revisions:
                        preview_revisions[event.payload.utterance_id] = max(
                            preview_revisions[event.payload.utterance_id], event.payload.revision
                        )
                if isinstance(event, AudioEvent):
                    source_id = event.payload.utterance_id
                elif isinstance(event, SpeechStatusEvent):
                    source_id = event.payload.utterance_id
                elif isinstance(event, FrameEvent):
                    source_id = event.payload.frame_id
                else:
                    source_id = None
                try:
                    incoming.put_nowait(event)
                except asyncio.QueueFull as error:
                    raise RuntimeError("agent input queue is full") from error
                if source_id is not None:
                    # This receipt enters the output queue before the agent can run
                    # perception, so an early failure can still name its accepted input.
                    enqueue_output(
                        {
                            "kind": "demo_status",
                            "session_id": session_id,
                            "accepted_event_id": event.event_id,
                            "accepted_revision": getattr(event.payload, "revision", 0),
                            "payload": {"media_received": event.kind, "source_id": source_id},
                        }
                    )

        receiver = asyncio.create_task(receive_inputs())
        processor = asyncio.create_task(process_inputs())

        async def cleanup_session() -> None:
            for task in (receiver, processor):
                if not task.done():
                    task.cancel()
            await asyncio.gather(receiver, processor, return_exceptions=True)
            for task in preview_tasks.values():
                task.cancel()
            if preview_tasks:
                await asyncio.gather(*tuple(preview_tasks.values()), return_exceptions=True)
                preview_tasks.clear()

            # Close the controller before waiting for any upload file writes.
            # Those writes are bounded in size, but can still take time; leaving
            # the agent live while they drain would let pending work continue
            # after the browser has ended the session.
            agent_cancelled = False
            if agent.running and not agent_task.done():
                try:
                    incoming.put_nowait(EndEvent(session_id=session_id))
                except asyncio.QueueFull:
                    agent_task.cancel()
                    agent_cancelled = True
            if not agent_cancelled and not agent_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(agent_task), timeout=1)
                except (asyncio.TimeoutError, RuntimeError):
                    agent_task.cancel()
            await asyncio.gather(agent_task, return_exceptions=True)
            if not sender.done():
                try:
                    outgoing.put_nowait(None)
                except asyncio.QueueFull:
                    pass
                try:
                    await asyncio.wait_for(asyncio.shield(sender), timeout=1)
                except (asyncio.TimeoutError, RuntimeError):
                    sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)

            if materialization_tasks:
                materializers = tuple(materialization_tasks)
                _, pending_materializers = await asyncio.wait(
                    materializers,
                    timeout=1,
                )
                for task in pending_materializers:
                    task.cancel()
                await asyncio.gather(*materializers, return_exceptions=True)
                materialization_tasks.clear()
            await perception.aclose()

        try:
            done, _ = await asyncio.wait(
                {sender, receiver, processor, agent_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in done:
                if not task.cancelled() and task.exception():
                    raise task.exception()
        except (WebSocketDisconnect, RuntimeError, ValueError):
            pass
        except asyncio.CancelledError:
            # WebSocket servers can cancel the handler immediately after a peer
            # closes. Treat that as session end and finish bounded cleanup below.
            pass
        finally:
            cleanup_task = asyncio.create_task(cleanup_session())
            current_task = asyncio.current_task()
            while not cleanup_task.done():
                try:
                    await asyncio.shield(cleanup_task)
                except asyncio.CancelledError:
                    # A repeated ASGI cancellation must not abandon native workers.
                    if current_task is not None:
                        current_task.uncancel()
            await cleanup_task


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=False)
