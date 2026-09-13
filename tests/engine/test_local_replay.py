import asyncio
import json
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("fail_close", [False, True])
async def test_replay_closes_owned_perception_and_reports_cleanup_failures(tmp_path, fail_close):
    class ManagedPerception(LocalPerception):
        closed = False

        async def aclose(self):
            self.closed = True
            if fail_close:
                raise RuntimeError("private provider detail must not be recorded")

    perception = ManagedPerception()
    trace = tmp_path / "trace.jsonl"
    result = await replay(ROOT / "scenarios/dev/text_correction.json", trace,
                          perception=perception, turn_policy=HeuristicTurnPolicy())
    assert perception.closed
    metadata = json.loads(trace.read_text().splitlines()[0])
    assert metadata["perception_cleanup"] == ("failed" if fail_close else "closed")
    assert result["completion_status"] == ("perception_cleanup_error" if fail_close else "completed")
    if fail_close:
        assert result["task_oracle"]["passed"] is False
        assert "private provider detail" not in trace.read_text()


async def test_cancelled_replay_still_closes_perception(tmp_path):
    entered = asyncio.Event()

    class BlockingPerception(LocalPerception):
        closed = False

        async def observe(self, event):
            entered.set()
            await asyncio.Event().wait()
            async for observation in super().observe(event):
                yield observation

        async def aclose(self):
            self.closed = True

    perception = BlockingPerception()
    run = asyncio.create_task(replay(ROOT / "scenarios/dev/text_correction.json", tmp_path / "trace.jsonl",
                                      perception=perception))
    await asyncio.wait_for(entered.wait(), 2)
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(run, 3)
    assert perception.closed


async def test_raw_media_process_is_closed_after_replay(tmp_path):
    from accessflow.adapters.process_perception import ProcessPerception

    raw = json.loads((ROOT / "scenarios/dev/text_correction.json").read_text())
    final_event = raw["events"][-1]
    final_event.update(kind="audio", payload={"path": "test-only-fixture.wav",
                                            "utterance_id": "raw-audio", "revision": 0,
                                            "speech_start": 0, "speech_end": 1})
    raw["events"] = [raw["events"][0], final_event]
    raw["proposals"] = [raw["proposals"][-1]]
    path = tmp_path / "audio.json"
    path.write_text(json.dumps(raw))
    trace = tmp_path / "trace.jsonl"
    perception = ProcessPerception(model_path=tmp_path, worker_module="tests.engine.worker_fixture")
    result = await replay(path, trace, perception=perception, turn_policy=HeuristicTurnPolicy())
    assert result["task_oracle"]["passed"] is True
    assert not perception.child_alive
    metadata = json.loads(trace.read_text().splitlines()[0])
    assert metadata["perception_cleanup"] == "closed"
    assert metadata["perception_backends_observed"] == ["fixture/native"]


@pytest.mark.parametrize("interrupt", [False, True])
async def test_controller_stops_native_work_when_speech_is_superseded(tmp_path, interrupt):
    from accessflow.adapters.process_perception import ProcessPerception
    from accessflow.contracts import Audio, AudioEvent, Interrupt, InterruptEvent
    from test_component_integration import components
    from test_safety import proposal, wait_for

    ready = tmp_path / "native-entered"
    perception = ProcessPerception(model_path=tmp_path, worker_module="tests.engine.worker_fixture",
                                    worker_args=("--mode", "block", "--ready-file", str(ready)))
    async with perception:
        async with components([proposal()], perception) as (agent, iq, oq, _):
            await iq.put(AudioEvent(session_id="s", event_id="block", payload=Audio(
                path="test-only-fixture.wav", utterance_id="u", revision=0)))
            async with asyncio.timeout(5):
                while not ready.exists():
                    await asyncio.sleep(0.01)
            old_process = perception._process
            assert old_process.pid == int(ready.read_text())
            if interrupt:
                await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="speech")))
            await iq.put(AudioEvent(session_id="s", event_id="corrected", payload=Audio(
                path="test-only-fixture.wav", utterance_id="u", revision=1)))
            await wait_for(oq, lambda event: event.kind == "final")
            assert old_process.returncode is not None
            assert len(agent.executor.effects) == 1
