from pathlib import Path

import pytest

from accessflow.adapters.samsung_protocol import (
    MediaInputError,
    SamsungProtocol,
    SamsungProtocolError,
    SamsungUnsupportedMediaError,
)
from accessflow.contracts import OutputEvent, Slot, Snapshot


def manifest_event():
    return {
        "timestamp_ms": 0,
        "event_type": "tool_manifest",
        "payload": {
            "schema_version": "1.0",
            "tools": {
                "lookup": {
                    "kind": "read_only",
                    "delay_range_ms": [100, 200],
                    "description": "Read something.",
                    "args": {
                        "query": {"type": "string", "required": True},
                        "embedding": {"type": "array", "items": "number", "required": False},
                    },
                    "default_result": {"secret": "must not enter the manifest"},
                },
                "write_ticket": {
                    "kind": "state_modifying",
                    "delay_range_ms": [100, 200],
                    "description": "Write something.",
                    "args": {"summary": {"type": "string", "required": True}},
                },
            },
        },
    }


def output(kind, payload, *, intent="support", slots=None):
    state = Snapshot(intent=intent, slots={
        name: Slot(value=value, confirmed=True) for name, value in (slots or {}).items()
    })
    return OutputEvent(session_id="s", sequence=1, kind=kind, payload=payload, state=state)


def test_manifest_translates_dynamic_tools_without_default_results(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    event = protocol.translate_input(manifest_event())[0]

    assert event.kind == "session_start"
    lookup = next(tool for tool in event.payload.tools if tool.name == "lookup")
    assert lookup.effect == "read"
    assert lookup.parameters["properties"]["embedding"] == {
        "type": "array", "items": {"type": "number"}
    }
    assert "secret" not in lookup.model_dump_json()


def test_text_chunks_become_replacement_revisions(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    first = protocol.translate_input({
        "timestamp_ms": 100, "event_type": "user_speech_chunk",
        "payload": {"text": "Book Tues", "end_of_turn": False},
    })[0]
    second = protocol.translate_input({
        "timestamp_ms": 300, "event_type": "user_speech_chunk",
        "payload": {"text": "day at five", "end_of_turn": True},
    })[0]

    assert (first.payload.utterance_id, first.payload.revision,
            first.payload.text, first.payload.final) == ("turn-1", 0, "Book Tues", False)
    assert (second.payload.utterance_id, second.payload.revision,
            second.payload.text, second.payload.final) == ("turn-1", 1, "Book Tuesday at five", True)
    assert first.timestamp == 0.1 and second.timestamp == 0.3


def test_interruption_emits_invalidation_then_correction_transcript(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    events = protocol.translate_input({
        "timestamp_ms": 900, "event_type": "interruption",
        "payload": {"text": "Wait, use Wednesday instead."},
    })

    assert [event.kind for event in events] == ["interrupt", "transcript"]
    assert events[0].payload.scope == "speech"
    assert events[0].payload.utterance_id == events[1].payload.utterance_id
    assert events[1].payload.text == "Wait, use Wednesday instead."
    assert events[1].payload.final is True


def test_frame_ref_is_root_contained_and_missing_media_is_explicit(tmp_path: Path):
    frame = tmp_path / "frames" / "f.png"
    frame.parent.mkdir()
    frame.write_bytes(b"png placeholder")
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())

    event = protocol.translate_input({
        "timestamp_ms": 100, "event_type": "video_frame",
        "payload": {"frame_id": "f-1", "image_ref": "frames/f.png", "device_hint": "GENERIC"},
    })[0]
    assert Path(event.payload.path) == frame.resolve()

    with pytest.raises(MediaInputError, match="escapes"):
        protocol.translate_input({
            "timestamp_ms": 200, "event_type": "video_frame",
            "payload": {"frame_id": "f-2", "image_ref": "../outside.png"},
        })
    with pytest.raises(MediaInputError, match="does not exist"):
        protocol.translate_input({
            "timestamp_ms": 300, "event_type": "video_frame",
            "payload": {"frame_id": "f-3", "image_ref": "frames/missing.png"},
        })


def test_mp3_is_not_mislabelled_as_internal_wav(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    raw = {
        "timestamp_ms": 100, "event_type": "user_audio_chunk",
        "payload": {"audio_ref": "audio/turn.mp3", "duration_ms": 900, "end_of_turn": True},
    }
    with pytest.raises(SamsungUnsupportedMediaError, match="MP3"):
        protocol.translate_input(raw)
    failed = protocol.media_failure_events(raw)
    assert len(failed) == 1 and failed[0].kind == "interrupt"


def test_result_requires_the_call_identity_and_preserves_write_uncertainty(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    protocol.translate_output(output("tool_call", {
        "call_id": "c-write", "tool": "write_ticket", "arguments": {"summary": "flicker"},
        "effect": "write",
    }))
    timeout = protocol.translate_input({
        "timestamp_ms": 2500, "event_type": "tool_result",
        "payload": {"call_id": "c-write", "api_name": "write_ticket", "status": "error",
                    "result": {"error": "timeout", "detail": "unknown outcome"}},
    })[0]
    assert timeout.payload.status == "unknown"
    assert timeout.payload.committed is False

    with pytest.raises(SamsungProtocolError, match="does not match"):
        protocol.translate_input({
            "timestamp_ms": 2600, "event_type": "tool_result",
            "payload": {"call_id": "c-write", "api_name": "lookup", "status": "success",
                        "result": {}},
        })


def test_output_maps_tool_calls_and_flattens_final_snapshot(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    action = protocol.translate_output(output("tool_call", {
        "call_id": "c-read", "tool": "lookup", "arguments": {"query": "ports"},
        "effect": "read",
    }, slots={"device_model": "GENERIC"}))
    assert action["action"] == "tool_call"
    assert action["payload"] == {
        "call_id": "c-read", "api_name": "lookup", "args": {"query": "ports"}
    }
    assert action["state_snapshot"] == {"intent": "support", "slots": {"device_model": "GENERIC"}}

    final = protocol.translate_output(output("final", {
        "result": {"ticket_id": "TK-0001"},
    }, slots={"ticket_id": "TK-0001"}))
    assert final["action"] == "final_response"
    assert "TK-0001" in final["payload"]["text"]
    assert final["state_snapshot"]["slots"] == {"ticket_id": "TK-0001"}


def test_read_evidence_ack_is_suppressed_and_errors_are_diagnostics(tmp_path: Path):
    protocol = SamsungProtocol(tmp_path, session_id="s")
    protocol.translate_input(manifest_event())
    assert protocol.translate_output(output("acknowledge", {"result": {"pages": []}})) is None
    assert protocol.diagnostics[-1]["kind"] == "suppressed_acknowledge"
    assert protocol.translate_output(output("error", {"code": "tool_failed"})) is None
    assert protocol.diagnostics[-1]["code"] == "tool_failed"

