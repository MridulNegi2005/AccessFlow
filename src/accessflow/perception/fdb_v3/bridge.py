"""One AccessFlow controller per LiveKit room, with turn-scoped replies."""

from __future__ import annotations

import asyncio
import textwrap
from uuid import uuid4

from accessflow.contracts import (
    End, EndEvent, Interrupt, InterruptEvent, SpeechStatus, SpeechStatusEvent,
    Start, StartEvent, Transcript, TranscriptEvent,
)

from .tools import manifests


def spoken_reply(output) -> str:
    """Render a controller terminal event for speech without inventing results."""
    # Output-only stop must be silent: the user asked us to stop speaking, so we
    # must not emit any spoken response.
    if output.kind == "acknowledge" and output.payload.get("output_only"):
        return ""
    if text := output.payload.get("text"):
        return str(text)
    if result := output.payload.get("result"):
        if isinstance(result, dict):
            details = ", ".join(f"{key.replace('_', ' ')}: {value}"
                                for key, value in result.items() if key != "status")
            return f"Done. {details}" if details else "Done."
    if output.kind == "error":
        return "I couldn't complete that request. Please try again."
    return "Done."


def tts_safe_text(text: str) -> str:
    """Keep each spoken sentence below Groq Orpheus's 200-character request cap."""
    if len(text) <= 190:
        return text
    segments = textwrap.wrap(text, width=180, break_long_words=True,
                             break_on_hyphens=False)
    return " ".join(segment if segment.endswith((".", "!", "?")) else segment + "."
                    for segment in segments)


def spoken_results(results: list[tuple[str, dict]]) -> str:
    """Summarize only confirmed mock outputs when parallel calls finish out of order."""
    def value_text(value) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, list):
            return ", ".join(value_text(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(f"{key.replace('_', ' ')} {value_text(item)}"
                             for key, item in value.items())
        return str(value)

    parts = []
    for tool, result in results:
        if tool == "set_navigation_destination" and "destination" in result:
            parts.append(f"Simulated destination changed to {value_text(result['destination'])}")
            continue
        if tool == "get_navigation_state" and "destination" in result:
            parts.append(f"The simulated destination is {value_text(result['destination'])}")
            continue
        if tool == "get_exchange_rate" and {"converted_amount", "rate"} <= result.keys():
            parts.append(f"Conversion: {value_text(result['converted_amount'])} at rate "
                         f"{value_text(result['rate'])}")
            continue
        if (tool == "modify_autopay" and result.get("autopay_enabled") is True
                and "source" in result):
            parts.append(f"Autopay now uses {value_text(result['source'])}")
            continue
        if (tool == "get_card_benefits" and "card_type" in result
                and isinstance(result.get("benefits"), list)):
            parts.append(f"{value_text(result['card_type'])} benefits: "
                         f"{value_text(result['benefits'])}")
            continue
        if tool == "book_flight" and {"booking_ref", "passenger"} <= result.keys():
            parts.append(f"Booked {value_text(result['booking_ref'])} for "
                         f"{value_text(result['passenger'])}")
            continue
        if (tool == "search_flights" and isinstance(result.get("flights"), list)
                and len(result["flights"]) == 1
                and isinstance(result["flights"][0], dict)
                and {"flight_id", "destination", "date"} <= result["flights"][0].keys()):
            flight = result["flights"][0]
            parts.append(f"Found flight {value_text(flight['flight_id'])} to "
                         f"{value_text(flight['destination'])} on {value_text(flight['date'])}")
            continue
        fields = ", ".join(f"{key.replace('_', ' ')} {value_text(value)}"
                           for key, value in result.items() if key != "status")
        parts.append(f"{tool.replace('_', ' ')}: {fields or 'completed'}")
    return ". ".join(parts) + ("." if parts else "")


class RoomBridge:
    def __init__(self, room_name: str, controller, *, tool_manifests=None):
        if not room_name:
            raise ValueError("A room name is required")
        self.room_name = room_name
        self.controller = controller
        self.tool_manifests = tool_manifests if tool_manifests is not None else manifests()
        self.session_id = str(uuid4())
        self.inputs: asyncio.Queue = asyncio.Queue()
        self.outputs: asyncio.Queue = asyncio.Queue()
        self._runner: asyncio.Task | None = None
        self._router: asyncio.Task | None = None
        self._utterance_id: str | None = None
        self._reply: asyncio.Future[str] | None = None
        self._reply_cause: str | None = None
        self.last_reply_kind: str | None = None

    async def start(self) -> None:
        if self._runner is not None:
            raise RuntimeError("Room already started")
        self._runner = asyncio.create_task(self.controller.run(self.inputs, self.outputs))
        self._router = asyncio.create_task(self._route_outputs())
        await self.inputs.put(StartEvent(session_id=self.session_id,
                                         payload=Start(tools=self.tool_manifests)))

    async def begin_speech(self) -> None:
        """Admit speech before STT settles so pending writes do not race it."""
        if self._runner is None:
            raise RuntimeError("Room not started")
        if self._utterance_id is not None:
            return
        if self._reply is not None and not self._reply.done():
            self._reply.cancel()
        self._utterance_id = str(uuid4())
        await self.inputs.put(InterruptEvent(session_id=self.session_id,
                                             payload=Interrupt(scope="output")))
        await self.inputs.put(SpeechStatusEvent(session_id=self.session_id,
                                                payload=SpeechStatus(
                                                    utterance_id=self._utterance_id,
                                                    revision=0, status="pending")))

    async def complete_turn(self, text: str, *, timeout: float = 90.0) -> str:
        if self._runner is None:
            raise RuntimeError("Room not started")
        if not text.strip():
            # A transport pending event was already admitted by begin_speech().
            # Close that speech source through the controller contract instead
            # of leaving the turn permanently in a pending state.
            await self.fail_speech()
            return ""
        utterance_id = self._utterance_id or str(uuid4())
        revision = 1 if self._utterance_id else 0
        self._utterance_id = None
        if self._reply is not None and not self._reply.done():
            self._reply.cancel()
        self._reply = asyncio.get_running_loop().create_future()
        self.last_reply_kind = None
        event = TranscriptEvent(session_id=self.session_id, payload=Transcript(
            utterance_id=utterance_id, revision=revision, text=text, final=True))
        self._reply_cause = event.event_id
        await self.inputs.put(event)
        reply = self._reply
        try:
            return await asyncio.wait_for(asyncio.shield(reply), timeout=timeout)
        except TimeoutError:
            # A timeout ends this adapter wait, not any effect that may already
            # have committed. Interrupt the unfinished speech request so the
            # controller drops stale plans and applies its normal write guards.
            if self._reply is reply and not reply.done():
                reply.cancel()
                await self.inputs.put(InterruptEvent(
                    session_id=self.session_id,
                    payload=Interrupt(scope="speech", utterance_id=utterance_id),
                ))
            raise

    async def fail_speech(self) -> None:
        if self._utterance_id is None:
            return
        utterance_id, self._utterance_id = self._utterance_id, None
        await self.inputs.put(SpeechStatusEvent(session_id=self.session_id,
                                                payload=SpeechStatus(
                                                    utterance_id=utterance_id,
                                                    revision=1, status="failed")))

    async def close(self) -> None:
        if self._runner is None:
            return
        if self._reply is not None and not self._reply.done():
            self._reply.cancel()
        await self.inputs.put(EndEvent(session_id=self.session_id, payload=End(reason="room_closed")))
        try:
            await asyncio.wait_for(self._runner, timeout=5)
        finally:
            if self._router is not None:
                self._router.cancel()
                await asyncio.gather(self._router, return_exceptions=True)
            self._runner = None
            self._router = None

    async def _route_outputs(self) -> None:
        while True:
            output = await self.outputs.get()
            future = self._reply
            if future is None or future.done():
                continue
            if output.payload.get("caused_by_event_id") != self._reply_cause:
                continue
            # Most controller errors are diagnostics before an automatic retry.
            # Speaking them as a terminal reply would hide the recovery result.
            terminal_error = output.kind == "error" and output.payload.get("code") in {
                "backend_failure", "no_progress_exhausted", "write_outcome_unknown",
            }
            # Control-terminal acknowledge events must also resolve the pending
            # reply.  The controller emits acknowledge (not final) for a
            # successful output-only stop and for explicit task cancellation.
            # - output_only=True  → output stop accepted; resolve silently ("")
            # - stop_output=True with text → task cancellation acknowledged
            # Nonterminal acknowledgments do not meet these terminal predicates;
            # the event-cause guard also rejects acknowledgments from other inputs.
            terminal_acknowledge = (
                output.kind == "acknowledge"
                and (
                    # output-only stop: stops output silently with no further event
                    output.payload.get("output_only") is True
                    # task cancel ack: "Stopped." text signals the task stop completed.
                    # Vague-stop also emits acknowledge with stop_output=True but WITHOUT
                    # text; it is followed by a clarify (not terminal yet).
                    or (output.payload.get("stop_output") is True
                        and output.payload.get("text") == "Stopped.")
                )
            )
            if output.kind in {"final", "clarify"} or terminal_error or terminal_acknowledge:
                self.last_reply_kind = output.kind
                future.set_result(spoken_reply(output))
