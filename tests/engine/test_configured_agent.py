"""Common runtime configuration; all inference in these tests is explicitly fake."""

import asyncio
import json

import pytest

from accessflow.adapters import configured_agent as runtime
from accessflow.adapters.samsung import HarnessAuthorization, ParticipantAgent
from accessflow.contracts import Observation, PlanProposal


def native_environment(tmp_path, vision=False):
    (tmp_path / "asr").mkdir(exist_ok=True)
    (tmp_path / "warm.wav").write_bytes(b"fixture handled by fake perception")
    env = {"ACCESSFLOW_SAMSUNG_PERCEPTION": "process", "ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": "asr",
           "ACCESSFLOW_SAMSUNG_WARMUP_AUDIO": "warm.wav", "ACCESSFLOW_SAMSUNG_PERCEPTION_TIMEOUT_S": "17"}
    if vision:
        (tmp_path / "warm.png").write_bytes(b"fixture handled by fake perception")
        env.update({"ACCESSFLOW_SAMSUNG_VISION_PROVIDER": "ollama",
                    "ACCESSFLOW_SAMSUNG_VISION_MODEL": "declared-vision",
                    "ACCESSFLOW_SAMSUNG_VISION_URL": "http://127.0.0.1:11434",
                    "ACCESSFLOW_SAMSUNG_WARMUP_IMAGE": "warm.png"})
    return env


class Perception:
    instances = []
    fail_modality = None
    wrong_source = False

    def __init__(self, model_path, **kwargs):
        self.model_path, self.kwargs = model_path, kwargs
        self.closed = False
        self.events = []
        self.instances.append(self)

    async def observe(self, event):
        self.events.append(event)
        modality = "audio" if event.kind == "audio" else "image"
        if modality == self.fail_modality:
            raise RuntimeError("offline warmup failure")
        source = event.payload.utterance_id if modality == "audio" else event.payload.frame_id
        yield Observation(event_id=event.event_id, source_id="wrong" if self.wrong_source else source,
                          modality=modality, text="offline fixture", final=True,
                          backend="fake/" + modality)

    async def aclose(self):
        self.closed = True


class Backend:
    instances = []

    def __init__(self, name):
        self.name = name
        self.warmed = False
        self.instances.append(self)

    async def warmup(self):
        self.warmed = True


@pytest.fixture
def fake_runtime(monkeypatch):
    Perception.instances = []
    Backend.instances = []
    monkeypatch.setattr(Perception, "fail_modality", None)
    monkeypatch.setattr(Perception, "wrong_source", False)
    for key in runtime.PERCEPTION_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ACCESSFLOW_SAMSUNG_BACKEND", "groq")
    monkeypatch.setattr(runtime, "ProcessPerception", Perception)
    monkeypatch.setattr(runtime.models, "JsonBackend", Backend)


def test_text_configuration_rejects_ignored_native_settings(tmp_path):
    assert runtime.PerceptionConfig.from_environment(tmp_path, {}).mode == "text"
    with pytest.raises(ValueError, match="require"):
        runtime.PerceptionConfig.from_environment(tmp_path, {"ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": "ignored"})


@pytest.mark.parametrize("field,value", [("PERCEPTION", "fake"), ("PERCEPTION_TIMEOUT_S", "nan"),
    ("PERCEPTION_TIMEOUT_S", "0"), ("PERCEPTION_TIMEOUT_S", "111"), ("ASR_MODEL_PATH", "missing"),
    ("WARMUP_AUDIO", "missing.wav"), ("VISION_PROVIDER", "silent-fallback"),
    ("VISION_URL", "https://name:password@example.test"), ("VISION_URL", "https://example.test/path"),
    ("VISION_URL", "http://example.test:11434"), ("VISION_URL", "http://0.0.0.0:11434"),
    ("VISION_URL", "http://127.0.0.1:99999"), ("VISION_URL", "http://127.0.0.1:bad"),
    ("VISION_URL", "http://127.0.0.1:0"), ("VISION_URL", "http://@localhost:11434")])
def test_invalid_media_configuration_fails_before_model_work(tmp_path, field, value):
    env = native_environment(tmp_path, vision=True)
    env["ACCESSFLOW_SAMSUNG_" + field] = value
    with pytest.raises(ValueError):
        runtime.PerceptionConfig.from_environment(tmp_path, env)


async def test_samsung_setup_uses_shared_real_composition_and_warms_both_routes(tmp_path, monkeypatch, fake_runtime):
    for name, value in native_environment(tmp_path, vision=True).items():
        monkeypatch.setenv(name, value)
    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path)
    await participant.setup()
    try:
        agent = participant.agent
        perception = Perception.instances[-1]
        assert agent.perception is perception
        assert perception.model_path == (tmp_path / "asr").resolve()
        assert perception.kwargs["worker_args"] == ["--vision-provider", "ollama", "--vision-model",
                "declared-vision", "--vision-url", "http://127.0.0.1:11434", "--vision-timeout", "17.0"]
        assert agent.inference_timeout == perception.kwargs["observation_timeout_s"] == 17
        assert [e.kind for e in perception.events] == ["audio", "frame"]
        assert agent.perception_warmup_backends == {"audio": "fake/audio", "image": "fake/image"}
        assert agent.executor is None
        assert Backend.instances[-1].warmed
        assert agent.reasoner.backend is Backend.instances[-1]
        # A warm-up is setup evidence, never a user turn in the controller.
        assert participant.in_queue.empty() and participant.out_queue.empty()
        await participant.setup()
        assert len(perception.events) == 2
    finally:
        await participant.agent.perception.aclose()


@pytest.mark.parametrize("failure", ["audio", "image", "wrong_source"])
async def test_failed_warmup_closes_resources_and_never_silently_uses_text(tmp_path, monkeypatch, fake_runtime, failure):
    for name, value in native_environment(tmp_path, vision=True).items():
        monkeypatch.setenv(name, value)
    if failure == "wrong_source":
        monkeypatch.setattr(Perception, "wrong_source", True)
    else:
        monkeypatch.setattr(Perception, "fail_modality", failure)
    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path)
    with pytest.raises(RuntimeError):
        await participant.setup()
    assert Perception.instances[-1].closed
    assert participant.agent is None
    assert not Backend.instances
    with pytest.raises(RuntimeError, match="previously failed"):
        await participant.setup()
    assert len(Perception.instances) == 1


async def test_reasoner_setup_failure_also_closes_warmed_perception(tmp_path, monkeypatch, fake_runtime):
    for name, value in native_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    async def failed(self):
        raise RuntimeError("reasoner unavailable")

    monkeypatch.setattr(Backend, "warmup", failed)
    with pytest.raises(RuntimeError, match="reasoner unavailable"):
        await runtime.build_configured_agent(root=tmp_path, authorization=HarnessAuthorization())
    assert Perception.instances[-1].closed


async def test_configured_factory_can_be_used_by_demo_with_explicit_executor(tmp_path, fake_runtime):
    executor = object()
    agent = await runtime.build_configured_agent(root=tmp_path, executor=executor,
                    authorization=HarnessAuthorization(), prompt_profile="compact-v2", read_answer_mode="evidence")
    try:
        assert agent.executor is executor
        assert agent.reasoner.prompt_profile == "compact-v2"
        assert agent.read_answer_mode == "evidence"
        assert agent.perception_warmup_backends == {}
    finally:
        await agent.perception.aclose()


async def test_total_warmup_budget_closes_native_worker(tmp_path, monkeypatch, fake_runtime):
    for name, value in native_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    async def blocked(self):
        await asyncio.Event().wait()

    monkeypatch.setattr(Backend, "warmup", blocked)
    monkeypatch.setattr(runtime, "SETUP_TIMEOUT_S", 0.03)
    with pytest.raises(TimeoutError):
        await runtime.build_configured_agent(root=tmp_path, authorization=HarnessAuthorization())
    assert Perception.instances[-1].closed


async def test_official_frame_reaches_reasoner_through_configured_child(tmp_path, monkeypatch, fake_runtime):
    """Real process/controller/protocol; deliberately fake ASR, pixels and inference."""
    from accessflow.adapters.process_perception import ProcessPerception
    from tests.engine.test_samsung_runtime import action, event

    for name, value in native_environment(tmp_path, vision=True).items():
        monkeypatch.setenv(name, value)
    requests = []

    async def generate(self, system, data, schema, **kwargs):
        requests.append(data)
        proposal = PlanProposal(request_complete=True, response="Fixture image received.").model_dump(mode="json")
        if "_validator" in kwargs:
            kwargs["_validator"](proposal)
        return proposal

    def child(model_path, **kwargs):
        return ProcessPerception(model_path, observation_timeout_s=kwargs["observation_timeout_s"],
                                 worker_module="tests.engine.worker_fixture")

    monkeypatch.setattr(Backend, "generate", generate, raising=False)
    monkeypatch.setattr(runtime, "ProcessPerception", child)
    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path)
    await participant.setup()
    assert participant.agent.perception_warmup_backends == {"audio": "fixture/native", "image": "fixture/native"}
    task = asyncio.create_task(participant.run())
    try:
        await participant.in_queue.put(event("tool_manifest", {"schema_version": "1.0", "tools": {}}))
        await participant.in_queue.put(event("video_frame", {"image_ref": "warm.png", "frame_id": "current"}, 10))
        await participant.in_queue.put(event("user_speech_chunk", {"text": "Describe this image.", "end_of_turn": True}, 20))
        try:
            result = await action(participant.out_queue, "final_response")
        except TimeoutError:
            pytest.fail(f"No final: diagnostics={participant.diagnostics!r}; requests={requests!r}")
        assert result["payload"]["text"] == "Fixture image received."
        assert any("fixture image" in json.dumps(request) for request in requests)
        assert all("installation-warmup" not in json.dumps(request) for request in requests)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    assert not participant.tasks
