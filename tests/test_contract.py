import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from accessflow.contracts import InputEvent, ToolManifest
from accessflow.fakes import FakePerception


def test_golden_roundtrip():
    raw = json.loads((Path(__file__).parent / "fixtures/transcript.json").read_text())
    event = TypeAdapter(InputEvent).validate_python(raw)
    assert TypeAdapter(InputEvent).validate_json(event.model_dump_json()) == event


def test_wrong_version_rejected():
    with pytest.raises(ValidationError):
        TypeAdapter(InputEvent).validate_python({"kind": "session_end", "session_id": "s",
                                                 "contract_version": "9", "payload": {}})


def test_manifest_schema_checked():
    with pytest.raises(Exception):
        ToolManifest(name="any_name", description="anything", effect="read", parameters={"type": "nonsense"})


async def test_perception_preserves_hypothesis_identity():
    event = TypeAdapter(InputEvent).validate_json((Path(__file__).parent / "fixtures/transcript.json").read_text())
    observations = [obs async for obs in FakePerception().observe(event)]
    assert len(observations) == 1
    obs = observations[0]
    assert (obs.source_id, obs.revision, obs.event_id) == ("utterance-1", 2, event.event_id)
    assert obs.text == event.payload.text
    assert obs.speech_end == 3.1


def test_transport_speech_status_roundtrip_has_no_transcript_or_timing():
    raw = {"kind": "speech_status", "session_id": "s",
           "payload": {"utterance_id": "audio-turn-1", "revision": 0, "status": "pending"}}
    event = TypeAdapter(InputEvent).validate_python(raw)
    assert TypeAdapter(InputEvent).validate_json(event.model_dump_json()) == event
    for extra in [{"text": "invented transcript"}, {"speech_end": 2.0}, {"final": True}]:
        with pytest.raises(ValidationError):
            TypeAdapter(InputEvent).validate_python({**raw, "payload": {**raw["payload"], **extra}})
