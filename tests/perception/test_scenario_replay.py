import base64
import json
from collections import Counter
from pathlib import Path

import pytest

from accessflow.contracts import Audio, AudioEvent, Frame, FrameEvent, Transcript, TranscriptEvent
from accessflow.perception.local import LocalPerception


def _manifest():
    root = Path(__file__).parents[2]
    manifest = json.loads(
        (root / "docs" / "feedback" / "SCENARIO_MATRIX.json").read_text(encoding="utf-8")
    )
    return root, manifest


class _ReplayAudio:
    backend_name = "fake/replay-asr"

    def __init__(self, scripts):
        self._scripts = scripts

    def __call__(self, path: Path) -> str:
        return self._scripts[path.name]


class _ReplayVision:
    backend_name = "fake/replay-vision"

    def __init__(self, captions):
        self._captions = captions

    def __call__(self, path: Path) -> str:
        return self._captions[path.name]


@pytest.mark.asyncio
async def test_entire_scenario_inventory_replays_through_local_perception(tmp_path: Path):
    root, manifest = _manifest()
    cases = manifest["cases"]
    audio_cases = [case for case in cases if case["modality"] == "audio"]
    image_cases = [case for case in cases if case["modality"] == "image"]
    audio_scripts = {
        Path(case["asset"]["fixture"]).name: case["reference_text"] for case in audio_cases
    }
    image_paths = {}
    image_captions = {}
    for case in image_cases:
        path = tmp_path / f"{case['id']}.png"
        path.write_bytes(base64.b64decode(case["asset"]["payload_base64"], validate=True))
        image_paths[case["id"]] = path
        image_captions[path.name] = case["visual_label"]

    perception = LocalPerception(
        transcriber=_ReplayAudio(audio_scripts),
        vision_provider=_ReplayVision(image_captions),
    )
    observations = []
    try:
        for sequence, case in enumerate(cases, start=1):
            event_id = f"replay-{case['id']}"
            if case["modality"] == "text":
                event = TranscriptEvent(
                    session_id="scenario-replay",
                    event_id=event_id,
                    timestamp=float(sequence),
                    sequence=sequence,
                    payload=Transcript(
                        utterance_id=case["id"],
                        revision=0,
                        text=case["stimulus"],
                        final=True,
                    ),
                )
            elif case["modality"] == "audio":
                event = AudioEvent(
                    session_id="scenario-replay",
                    event_id=event_id,
                    timestamp=float(sequence),
                    sequence=sequence,
                    payload=Audio(
                        path=str(root / case["asset"]["fixture"]),
                        utterance_id=case["id"],
                        revision=0,
                    ),
                )
            else:
                event = FrameEvent(
                    session_id="scenario-replay",
                    event_id=event_id,
                    timestamp=float(sequence),
                    sequence=sequence,
                    payload=Frame(path=str(image_paths[case["id"]]), frame_id=case["id"]),
                )
            observations.extend([observation async for observation in perception.observe(event)])
    finally:
        await perception.aclose()

    assert len(observations) == 60
    assert Counter(observation.modality for observation in observations) == {
        "text": 30,
        "audio": 18,
        "image": 12,
    }
    assert all(observation.final and observation.text for observation in observations)
    assert all(
        observation.event_id == f"replay-{case['id']}"
        and observation.source_id == case["id"]
        and observation.modality == case["modality"]
        for observation, case in zip(observations, cases)
    )
    assert {observation.backend for observation in observations} == {
        "local/text-pass-through",
        "local/injected-asr",
        "fake/replay-vision",
    }
