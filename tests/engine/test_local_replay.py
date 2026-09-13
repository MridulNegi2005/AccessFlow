import json
from pathlib import Path

from accessflow.evaluation.replay import replay
from accessflow.evaluation.suite import run_suite
from accessflow.perception import LocalPerception
from accessflow.turn_policy import HeuristicTurnPolicy


ROOT = Path(__file__).resolve().parents[2]


async def test_local_components_are_fresh_per_case_and_record_actual_adapter_backends(tmp_path):
    perceptions, policies = [], []

    def perception_factory():
        perception = LocalPerception()
        perceptions.append(perception)
        return perception

    def policy_factory():
        policy = HeuristicTurnPolicy()
        policies.append(policy)
        return policy

    result = await run_suite((ROOT / "scenarios/dev").glob("*.json"), tmp_path,
                             perception_factory=perception_factory, turn_policy_factory=policy_factory)
    assert result["counts"]["passed"] == 4
    assert len({id(component) for component in perceptions}) == 4
    assert len({id(component) for component in policies}) == 4
    for case in result["cases"]:
        metadata = case["metrics"]["run_metadata"]
        assert metadata["perception"].endswith("LocalPerception")
        assert metadata["config"]["turn_policy"].endswith("HeuristicTurnPolicy")
        assert metadata["perception_backends_observed"] == ["local/text-pass-through"]
        assert metadata["backend"] == "offline-fake"


async def test_raw_wav_replay_fails_honestly_without_configured_asr(tmp_path):
    raw = json.loads((ROOT / "scenarios/dev/text_correction.json").read_text())
    final_event = raw["events"][-1]
    final_event.update(kind="audio", payload={"path": str(ROOT / "tests/fixtures/audio/synthetic_tone.wav"),
                                            "utterance_id": "raw-audio", "revision": 0})
    raw["events"] = [raw["events"][0], final_event]
    raw["proposals"] = [raw["proposals"][-1]]
    path = tmp_path / "audio.json"
    path.write_text(json.dumps(raw))
    trace = tmp_path / "trace.jsonl"
    result = await replay(path, trace, perception=LocalPerception(), turn_policy=HeuristicTurnPolicy())
    assert result["completion_status"] == "backend_failure"
    assert result["task_oracle"]["passed"] is False
    metadata = json.loads(trace.read_text().splitlines()[0])
    assert metadata["perception_backends_observed"] == []
    assert result["mock_effects"] == 0
