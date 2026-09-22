"""Pure boundary translation for Samsung's Theme 5 streaming protocol.

The organizer kit and AccessFlow deliberately use different envelopes.  This
module keeps that difference at one boundary: it does not run an agent, load a
model, execute a tool, or read scenario files.  ``SamsungProtocol`` translates
one official input event into one or more internal events and one internal
``OutputEvent`` into an official action.

The kit's text chunks are *additive*.  AccessFlow's transcript revisions are
replacement hypotheses, so the translator keeps a small per-turn buffer and
emits the cumulative text at each revision.  Audio is intentionally rejected
until an owner supplies an MP3 decoder/assembly contract; treating an MP3 path
as a WAV path would make an apparently working evaluation dishonest.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..contracts import (
    Frame,
    FrameEvent,
    Interrupt,
    InterruptEvent,
    InputEvent,
    ResultEvent,
    Snapshot,
    Start,
    StartEvent,
    ToolManifest,
    ToolResult,
    Transcript,
    TranscriptEvent,
    OutputEvent,
)


class SamsungProtocolError(ValueError):
    """Raised when an official event or action cannot be safely translated."""


class MediaInputError(SamsungProtocolError):
    """Raised when an official media item cannot be safely admitted."""


class SamsungUnsupportedMediaError(MediaInputError):
    """Raised for official media whose decoder contract is not implemented."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SamsungProtocolError(f"{name} must be an object")
    return value


def _non_empty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SamsungProtocolError(f"{name} must be a non-empty string")
    return value


def _timestamp(raw: Mapping[str, Any]) -> float:
    value = raw.get("timestamp_ms", 0)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SamsungProtocolError("timestamp_ms must be a finite non-negative number")
    if not math.isfinite(float(value)) or value < 0:
        raise SamsungProtocolError("timestamp_ms must be a finite non-negative number")
    return float(value) / 1000.0


class SamsungProtocol:
    """Translate the official Samsung queue protocol at the process boundary.

    Parameters
    ----------
    media_root:
        The extracted kit root.  Official ``image_ref`` values are resolved
        beneath this directory and are never accepted as arbitrary filesystem
        paths.
    session_id:
        Internal session identifier.  The official envelope has no session ID,
        so the adapter supplies one consistently for the lifetime of a run.

    ``translate_input`` returns an empty list for ``scenario_end``.  The outer
    runtime owns the official tail window and must not inject an internal
    ``EndEvent`` before that window expires.
    """

    def __init__(self, media_root: str | Path, session_id: str = "samsung-session") -> None:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        self.media_root = Path(media_root).expanduser().resolve()
        self.session_id = session_id
        self._sequence = 0
        self._turn_number = 0
        self._interrupt_number = 0
        self._active_utterance: str | None = None
        self._text_buffer = ""
        self._text_revision = -1
        self._manifest_seen = False
        self._tools: dict[str, ToolManifest] = {}
        self._calls: dict[str, dict[str, str]] = {}
        self._spoken_fillers: set[str] = set()
        self._spoken_failures: set[tuple[str, str | None]] = set()
        self.diagnostics: list[dict[str, Any]] = []

    @property
    def tools(self) -> dict[str, ToolManifest]:
        """Return a copy of the translated manifest, excluding default results."""
        return {name: tool.model_copy(deep=True) for name, tool in self._tools.items()}

    def translate_input(self, raw: Mapping[str, Any]) -> list[InputEvent]:
        """Translate one official input envelope into internal event models."""
        event = _mapping(raw, "event")
        event_type = _non_empty_string(event.get("event_type"), "event_type")
        payload = _mapping(event.get("payload", {}), "payload")
        timestamp = _timestamp(event)

        if not self._manifest_seen and event_type != "tool_manifest":
            raise SamsungProtocolError("tool_manifest must be the first official event")
        if event_type == "tool_manifest":
            return [self._manifest_event(payload, timestamp)]
        if event_type == "user_speech_chunk":
            return [self._speech_event(payload, timestamp)]
        if event_type == "interruption":
            return self._interruption_events(payload, timestamp)
        if event_type == "tool_result":
            return [self._result_event(payload, timestamp)]
        if event_type == "video_frame":
            return [self._frame_event(payload, timestamp)]
        if event_type == "user_audio_chunk":
            self._reject_audio(payload)
        if event_type == "scenario_end":
            return []
        raise SamsungProtocolError(f"unsupported official event_type: {event_type!r}")

    def media_failure_events(self, raw: Mapping[str, Any]) -> list[InputEvent]:
        """Invalidate current speech intent after a media admission failure.

        The runtime can catch :class:`MediaInputError`, call this method, and
        enqueue the returned interrupt before asking the user for replacement
        input. No guessed transcript or fake image observation is created.
        """
        event = _mapping(raw, "event")
        event_type = _non_empty_string(event.get("event_type"), "event_type")
        if event_type not in {"user_audio_chunk", "video_frame"}:
            raise SamsungProtocolError("media_failure_events expects an audio or frame event")
        timestamp = _timestamp(event)
        self._active_utterance = None
        self._text_buffer = ""
        self._text_revision = -1
        return [InterruptEvent(session_id=self.session_id, sequence=self._next_sequence(),
                                timestamp=timestamp, payload=Interrupt(scope="speech"))]

    def translate_output(self, event: OutputEvent) -> dict[str, Any] | None:
        """Translate one internal output event into an official action.

        Internal diagnostics are not an official action kind. Errors are retained
        separately; known processing failures produce a bounded clarification,
        and other diagnostics return ``None``. Tool/backend prose is never echoed
        as a user-facing instruction. Repeated filler text is suppressed per session.
        """
        if not isinstance(event, OutputEvent):
            raise SamsungProtocolError("translate_output expects an OutputEvent")
        payload = dict(event.payload)
        kind = event.kind
        snapshot = self._snapshot(event.state)

        if kind == "error":
            self._diagnose({"kind": "error", **payload})
            code = payload.get("code")
            if code in {"backend_failure", "no_progress_exhausted"}:
                key = (code, payload.get("caused_by_event_id"))
                if key not in self._spoken_failures and len(self._spoken_failures) < 128:
                    self._spoken_failures.add(key)
                    # Do not repeat arbitrary backend/tool text or claim that a
                    # pending/unknown write had no effect. Diagnostics stay separate.
                    return {"action": "clarification_request", "payload": {"text":
                        "I couldn't finish processing the request. Any action already started "
                        "may still be pending; please check its status before trying again."},
                        "state_snapshot": snapshot}
            return None
        if kind == "acknowledge":
            text = self._spoken_text(payload, "acknowledge")
            if text is None:
                self._diagnose({"kind": "suppressed_acknowledge", "reason": "tool_evidence"})
                return None
            if text in self._spoken_fillers and not payload.get("stop_output"):
                self._diagnose({"kind": "suppressed_acknowledge", "reason": "repeated_filler"})
                return None
            if len(self._spoken_fillers) < 128:
                self._spoken_fillers.add(text)
            return {"action": "filler_speech", "payload": {"text": text},
                    "state_snapshot": snapshot}
        if kind == "clarify":
            text = self._spoken_text(payload, "clarify")
            return {"action": "clarification_request", "payload": {"text": text},
                    "state_snapshot": snapshot}
        if kind == "tool_call":
            return self._tool_call_output(payload, snapshot)
        if kind == "cancel_call":
            call_id = _non_empty_string(payload.get("call_id"), "cancel_call.call_id")
            if call_id not in self._calls:
                raise SamsungProtocolError(f"cannot cancel unknown call_id {call_id!r}")
            return {"action": "cancel_tool", "payload": {"call_id": call_id},
                    "state_snapshot": snapshot}
        if kind == "final":
            text = self._final_text(payload)
            return {"action": "final_response", "payload": {"text": text},
                    "state_snapshot": snapshot}
        raise SamsungProtocolError(f"unsupported internal output kind: {kind!r}")

    def resolve_media_ref(self, ref: Any, *, suffix: str) -> Path:
        """Resolve a kit-relative media reference while enforcing root containment."""
        value = _non_empty_string(ref, "media reference")
        if "\x00" in value:
            raise MediaInputError("media reference contains a NUL byte")
        candidate_ref = Path(value)
        if candidate_ref.is_absolute() or ":" in value:
            raise MediaInputError("media reference must be relative to the kit root")
        candidate = (self.media_root / candidate_ref).resolve()
        try:
            candidate.relative_to(self.media_root)
        except ValueError as exc:
            raise MediaInputError("media reference escapes the kit root") from exc
        if candidate.suffix.lower() != suffix.lower():
            raise MediaInputError(f"media reference must use {suffix} files")
        if not candidate.is_file():
            raise MediaInputError(f"media file does not exist: {value!r}")
        return candidate

    def _next_event(self, timestamp: float, kind: str, payload: Any) -> dict[str, Any]:
        self._sequence += 1
        return {"session_id": self.session_id, "sequence": self._sequence,
                "timestamp": timestamp, "kind": kind, "payload": payload}

    def _manifest_event(self, payload: Mapping[str, Any], timestamp: float) -> StartEvent:
        if self._manifest_seen:
            raise SamsungProtocolError("duplicate tool_manifest event")
        if payload.get("schema_version") != "1.0":
            raise SamsungProtocolError("unsupported tool manifest schema_version")
        raw_tools = _mapping(payload.get("tools"), "tool_manifest.tools")
        tools: list[ToolManifest] = []
        translated: dict[str, ToolManifest] = {}
        for name, raw_spec in raw_tools.items():
            tool_name = _non_empty_string(name, "tool name")
            spec = _mapping(raw_spec, f"tool {tool_name!r}")
            kind = spec.get("kind")
            if kind not in {"read_only", "state_modifying"}:
                raise SamsungProtocolError(f"tool {tool_name!r} has invalid kind")
            description = spec.get("description", "")
            if not isinstance(description, str):
                raise SamsungProtocolError(f"tool {tool_name!r} description must be a string")
            parameters = self._parameters(spec.get("args", {}), tool_name)
            manifest = ToolManifest(name=tool_name, description=description,
                                    effect="read" if kind == "read_only" else "write",
                                    parameters=parameters)
            if tool_name in translated:
                raise SamsungProtocolError(f"duplicate tool name {tool_name!r}")
            translated[tool_name] = manifest
            tools.append(manifest)
        self._manifest_seen = True
        self._tools = translated
        return StartEvent(session_id=self.session_id, sequence=self._next_sequence(),
                          timestamp=timestamp, payload=Start(tools=tools))

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _parameters(self, raw_args: Any, tool_name: str) -> dict[str, Any]:
        args = _mapping(raw_args, f"tool {tool_name!r}.args")
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, raw_schema in args.items():
            arg_name = _non_empty_string(name, f"tool {tool_name!r} argument name")
            schema = self._schema(raw_schema, f"argument {tool_name!r}.{arg_name}")
            if _mapping(raw_schema, "argument schema").get("required") is True:
                required.append(arg_name)
            properties[arg_name] = schema
        result: dict[str, Any] = {"type": "object", "properties": properties,
                                  "additionalProperties": False}
        if required:
            result["required"] = required
        return result

    def _schema(self, raw_schema: Any, name: str) -> dict[str, Any]:
        source = dict(_mapping(raw_schema, name))
        schema_type = source.get("type")
        if schema_type not in {"string", "number", "boolean", "array", "object"}:
            raise SamsungProtocolError(f"{name} has unsupported type")
        result: dict[str, Any] = {"type": schema_type}
        if "description" in source and isinstance(source["description"], str):
            result["description"] = source["description"]
        if "enum" in source:
            if not isinstance(source["enum"], list):
                raise SamsungProtocolError(f"{name}.enum must be a list")
            result["enum"] = list(source["enum"])
        if schema_type == "array":
            items = source.get("items")
            if isinstance(items, str):
                if items not in {"string", "number", "boolean", "object", "array"}:
                    raise SamsungProtocolError(f"{name}.items has unsupported type")
                result["items"] = {"type": items}
            elif items is not None:
                result["items"] = self._schema(items, f"{name}.items")
            else:
                result["items"] = {}
        if schema_type == "object":
            nested = source.get("properties", {})
            nested_parameters = self._parameters(nested, name)
            result["properties"] = nested_parameters["properties"]
            nested_required = nested_parameters.get("required")
            if nested_required:
                result["required"] = nested_required
            result["additionalProperties"] = bool(not nested)
        return result

    def _speech_event(self, payload: Mapping[str, Any], timestamp: float) -> TranscriptEvent:
        text = payload.get("text")
        if not isinstance(text, str):
            raise SamsungProtocolError("user_speech_chunk.text must be a string")
        end = payload.get("end_of_turn")
        if not isinstance(end, bool):
            raise SamsungProtocolError("user_speech_chunk.end_of_turn must be boolean")
        if self._active_utterance is None:
            self._turn_number += 1
            self._active_utterance = f"turn-{self._turn_number}"
            self._text_buffer = ""
            self._text_revision = -1
        self._text_buffer += text
        self._text_revision += 1
        result = TranscriptEvent(session_id=self.session_id, sequence=self._next_sequence(),
                                 timestamp=timestamp,
                                 payload=Transcript(utterance_id=self._active_utterance,
                                                    revision=self._text_revision,
                                                    text=self._text_buffer,
                                                    final=end))
        if end:
            self._active_utterance = None
            self._text_buffer = ""
            self._text_revision = -1
        return result

    def _interruption_events(self, payload: Mapping[str, Any], timestamp: float) -> list[InputEvent]:
        text = _non_empty_string(payload.get("text"), "interruption.text")
        self._interrupt_number += 1
        utterance = f"interrupt-{self._interrupt_number}"
        interrupt = InterruptEvent(session_id=self.session_id, sequence=self._next_sequence(),
                                   timestamp=timestamp, payload=Interrupt(scope="speech",
                                                                          utterance_id=utterance))
        correction = TranscriptEvent(session_id=self.session_id, sequence=self._next_sequence(),
                                     timestamp=timestamp,
                                     payload=Transcript(utterance_id=utterance, revision=0,
                                                        text=text, final=True))
        self._active_utterance = None
        self._text_buffer = ""
        self._text_revision = -1
        return [interrupt, correction]

    def _result_event(self, payload: Mapping[str, Any], timestamp: float) -> ResultEvent:
        call_id = _non_empty_string(payload.get("call_id"), "tool_result.call_id")
        api_name = _non_empty_string(payload.get("api_name"), "tool_result.api_name")
        call = self._calls.get(call_id)
        if call is None:
            raise SamsungProtocolError(f"tool_result references unknown call_id {call_id!r}")
        if call["api_name"] != api_name:
            raise SamsungProtocolError("tool_result api_name does not match its call_id")
        status = payload.get("status")
        if status not in {"success", "error"}:
            raise SamsungProtocolError("tool_result.status must be 'success' or 'error'")
        result = _mapping(payload.get("result", {}), "tool_result.result")
        result_copy = dict(result)
        if status == "success":
            internal_status = "success"
            error = None
        else:
            error = result_copy.get("error") or payload.get("error") or "tool_error"
            if not isinstance(error, str):
                error = str(error)
            # A timeout or an unfamiliar failure code does not prove that a
            # state-changing operation had no effect. Preserve that uncertainty
            # so the engine can reconcile through a declared status tool instead
            # of blindly retrying a write.
            definite_no_effect = {"invalid_args", "not_found", "duplicate_booking",
                                  "unknown_tool", "permission_denied", "cancelled"}
            internal_status = ("failed" if call["effect"] == "read" or error in definite_no_effect
                               else "unknown")
        committed = status == "success" and call["effect"] == "write"
        return ResultEvent(session_id=self.session_id, sequence=self._next_sequence(),
                           timestamp=timestamp,
                           payload=ToolResult(call_id=call_id, status=internal_status,
                                              result=result_copy, error=error,
                                              committed=committed))

    def _frame_event(self, payload: Mapping[str, Any], timestamp: float) -> FrameEvent:
        frame_id = _non_empty_string(payload.get("frame_id"), "video_frame.frame_id")
        path = self.resolve_media_ref(payload.get("image_ref"), suffix=".png")
        return FrameEvent(session_id=self.session_id, sequence=self._next_sequence(),
                          timestamp=timestamp, payload=Frame(path=str(path), frame_id=frame_id))

    @staticmethod
    def _reject_audio(payload: Mapping[str, Any]) -> None:
        ref = payload.get("audio_ref")
        suffix = Path(ref).suffix.lower() if isinstance(ref, str) else ""
        if suffix == ".mp3":
            raise SamsungUnsupportedMediaError(
                "Samsung official audio is MP3; no MP3 decoder/assembly contract is installed, "
                "so it cannot be translated as AccessFlow WAV audio"
            )
        raise SamsungUnsupportedMediaError("Samsung official audio translation is not implemented")

    def _tool_call_output(self, payload: Mapping[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        call_id = _non_empty_string(payload.get("call_id"), "tool_call.call_id")
        api_name = _non_empty_string(payload.get("tool"), "tool_call.tool")
        arguments = _mapping(payload.get("arguments"), "tool_call.arguments")
        manifest = self._tools.get(api_name)
        if manifest is None:
            raise SamsungProtocolError(f"tool_call references unmanifested tool {api_name!r}")
        effect = payload.get("effect")
        if effect != manifest.effect:
            raise SamsungProtocolError("tool_call effect does not match its manifest")
        if call_id in self._calls:
            raise SamsungProtocolError(f"duplicate tool_call call_id {call_id!r}")
        self._calls[call_id] = {"api_name": api_name, "effect": manifest.effect}
        return {"action": "tool_call", "payload": {"call_id": call_id,
                "api_name": api_name, "args": dict(arguments)}, "state_snapshot": snapshot}

    @staticmethod
    def _spoken_text(payload: Mapping[str, Any], kind: str) -> str | None:
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text
        if kind == "acknowledge" and isinstance(payload.get("result"), Mapping):
            return None
        raise SamsungProtocolError(f"internal {kind} output requires non-empty text")

    @staticmethod
    def _final_text(payload: Mapping[str, Any]) -> str:
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            return text
        result = payload.get("result")
        if isinstance(result, Mapping):
            encoded = json.dumps(dict(result), ensure_ascii=False, sort_keys=True)
            return f"The requested action completed with result: {encoded}"
        raise SamsungProtocolError("internal final output requires text or a result object")

    @staticmethod
    def _snapshot(state: Snapshot) -> dict[str, Any]:
        if not isinstance(state, Snapshot):
            raise SamsungProtocolError("internal output state must be a Snapshot")
        return {"intent": state.intent,
                "slots": {name: slot.value for name, slot in state.slots.items()}}

    def _diagnose(self, item: dict[str, Any]) -> None:
        self.diagnostics.append(item)
        del self.diagnostics[:-128]
