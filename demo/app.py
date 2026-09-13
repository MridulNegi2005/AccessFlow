"""Minimal browser demo backed by the real queue-based controller and labeled mocks."""

from __future__ import annotations

import asyncio
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

ROOT = Path(__file__).parent
app = FastAPI(title="AccessFlow mock demo")


class DemoPerception:
    """Explicitly labeled mock input adapter for the browser demo."""

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
            response=f"Mock agent received {latest.modality} input.",
            request_complete=True,
        )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


def event_from_message(session_id: str, message: dict[str, Any]):
    """Translate small browser messages into typed v0.1 input events."""
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
                path=payload.get("path", "browser-mock.wav"),
                utterance_id=payload.get("utterance_id", str(uuid.uuid4())),
                revision=payload.get("revision", 0),
            ),
        )
    if kind == "frame":
        return FrameEvent(
            session_id=session_id,
            payload=Frame(
                path=payload.get("path", "browser-mock.png"),
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
    agent = Agent(
        DemoPerception(),
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

    async def receive_inputs():
        while True:
            event = event_from_message(session_id, await websocket.receive_json())
            await incoming.put(event)

    sender = asyncio.create_task(send_outputs())
    receiver = asyncio.create_task(receive_inputs())
    try:
        done, pending = await asyncio.wait(
            {sender, receiver, agent_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            if not task.cancelled() and task.exception():
                raise task.exception()
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    except (WebSocketDisconnect, RuntimeError, ValueError):
        pass
    finally:
        if agent.running:
            await incoming.put(EndEvent(session_id=session_id))
        if not agent_task.done():
            agent_task.cancel()
        await asyncio.gather(agent_task, return_exceptions=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.app:app", host="127.0.0.1", port=8000, reload=False)