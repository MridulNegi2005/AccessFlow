"""Real WebSocket route with an injected ASR failure; no microphone/model/network.

Run from the repository root using its Python environment.
"""
import base64
import json
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from demo import app as demo_app  # noqa: E402
from accessflow.perception import LocalPerception  # noqa: E402


def fail_asr(path):
    raise RuntimeError("Injected ASR failure")


def main():
    backend = demo_app.DemoPerception(audio_backend=LocalPerception(transcriber=fail_asr))
    raw = Path("tests/fixtures/audio/synthetic_tone.wav").read_bytes()
    with patch.object(demo_app.DemoPerception, "from_environment", return_value=backend):
        with patch.object(demo_app.DemoReasoner, "from_environment", return_value=demo_app.DemoReasoner()):
            with TestClient(demo_app.app).websocket_connect("/ws") as socket:
                events = [socket.receive_json()]
                socket.send_json({"kind": "audio", "payload": {
                    "utterance_id": "submitted-audio", "revision": 0,
                    "data_base64": base64.b64encode(raw).decode("ascii"),
                    "filename": "synthetic_tone.wav",
                }})
                while events[-1]["kind"] != "error":
                    events.append(socket.receive_json())
    assert not any(event["kind"] == "demo_observation" for event in events)
    assert events[-1]["payload"]["code"] == "backend_failure"
    assert events[-1]["payload"].get("caused_by_event_id")
    assert not any(event["payload"].get("event_id") for event in events[:-1])
    print(json.dumps({"mode": "actual_websocket_route_injected_asr_failure", "events": events}, indent=2))


if __name__ == "__main__":
    main()
