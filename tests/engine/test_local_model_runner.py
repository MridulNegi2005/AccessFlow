import asyncio
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from accessflow.contracts import Observation, PlanProposal, SessionView, Snapshot
ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "scenarios/dev/text_correction.json"
_RUNNER_SPEC = importlib.util.spec_from_file_location("local_model_runner", ROOT / "scripts/run_local_model_checks.py")
runner = importlib.util.module_from_spec(_RUNNER_SPEC)
assert _RUNNER_SPEC.loader is not None
_RUNNER_SPEC.loader.exec_module(runner)


class FakeBackend:
    name = "ollama/fake"

    def __init__(self):
        self.warmups = 0

    async def warmup(self):
        self.warmups += 1
        return {"ready": True}

    async def generate(self, system, data, schema, **kwargs):
        return PlanProposal(response="synthetic plan").model_dump(mode="json")

    def evidence(self):
        return {"backend": "fake", "request_count": self.warmups}


def args_for(scenarios, output):
    return SimpleNamespace(url="http://127.0.0.1:11435/", model="gemma3:4b",
                           scenarios=str(scenarios), output=str(output))


def mock_client_factory(handler):
    return lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30)


def copy_scenarios(directory, count=1):
    directory.mkdir()
    for index in range(count):
        (directory / f"case-{index}.json").write_text(SCENARIO.read_text(encoding="utf-8"), encoding="utf-8")


async def fake_replay(path, trace, *, reasoner, **kwargs):
    view = SessionView(
        session_id="synthetic",
        state=Snapshot(revision=7),
        observations=[Observation(event_id="obs-1", source_id="utterance-1", modality="text",
                                   text="synthetic", final=True, backend="fixture")],
        results=[],
    )
    await reasoner.plan(view, [])
    trace.write_text("synthetic trace\n", encoding="utf-8")
    return {"completion_status": "completed", "task_oracle": {"passed": False}}


@pytest.mark.asyncio
async def test_setup_failure_is_reported_with_not_run_count(tmp_path):
    scenarios = tmp_path / "scenarios"
    copy_scenarios(scenarios)
    output = tmp_path / "output"
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(503)

    result = await runner.run(args_for(scenarios, output), client_factory=mock_client_factory(handler),
                              backend_factory=FakeBackend, replay_fn=fake_replay)

    assert result is False
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "error"
    assert report["setup_failure"] == {"phase": "setup", "exception_type": "HTTPStatusError"}
    assert report["finished_count"] == 0
    assert report["not_run_count"] == 1
    assert report["counts"] == {"passed": 0, "failed": 0, "error": 0, "cancelled": 0, "not_run": 1}
    assert calls == ["/api/version"]


@pytest.mark.asyncio
async def test_cleanup_failure_aborts_and_marks_remaining_cases_not_run(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    copy_scenarios(scenarios, count=2)
    output = tmp_path / "output"
    calls = []
    replay_calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma3:4b", "digest": "sha256:test"}]})
        if request.url.path == "/api/ps":
            if calls.count(("GET", "/api/ps")) <= 2:
                return httpx.Response(200, json={"models": []})
            return httpx.Response(200, json={"models": [{"name": "other:1b"}]})
        raise AssertionError(request.url)

    async def replay_once(*args, **kwargs):
        replay_calls.append(args[0])
        return {"completion_status": "completed", "task_oracle": {"passed": True}}

    monkeypatch.setattr(runner, "metrics", lambda path: {"synthetic": True})
    result = await runner.run(args_for(scenarios, output), client_factory=mock_client_factory(handler),
                              backend_factory=FakeBackend, replay_fn=replay_once)

    assert result is False
    assert len(replay_calls) == 1
    assert ("POST", "/api/generate") not in calls
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["finished_count"] == 1
    assert report["not_run_count"] == 1
    assert report["counts"] == {"passed": 0, "failed": 0, "error": 1, "cancelled": 0, "not_run": 1}
    case = report["cases"][0]
    assert case["status"] == "error"
    assert case["cleanup_failure"]["phase"] == "cleanup"
    assert case["cleanup_failure"]["reason_code"] == "unexpected_loaded_model"
    assert case["model_cleanup_observation"]["before"] == ["other:1b"]


@pytest.mark.asyncio
async def test_nonempty_output_directory_is_refused(tmp_path):
    scenarios = tmp_path / "scenarios"
    copy_scenarios(scenarios)
    output = tmp_path / "output"
    output.mkdir()
    marker = output / "existing.json"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        await runner.run(args_for(scenarios, output),
                         client_factory=mock_client_factory(lambda request: pytest.fail("network called")),
                         backend_factory=FakeBackend, replay_fn=fake_replay)
    assert marker.read_text(encoding="utf-8") == "keep"


@pytest.mark.asyncio
async def test_failed_oracle_is_not_labeled_success_and_plans_are_recorded(tmp_path, monkeypatch):
    scenarios = tmp_path / "scenarios"
    copy_scenarios(scenarios)
    output = tmp_path / "output"

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "test"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma3:4b"}]})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        raise AssertionError(request.url)

    monkeypatch.setattr(runner, "metrics", lambda path: {"synthetic": True})
    result = await runner.run(args_for(scenarios, output), client_factory=mock_client_factory(handler),
                              backend_factory=FakeBackend, replay_fn=fake_replay)

    assert result is False
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    case = report["cases"][0]
    assert case["status"] == "failed"
    assert case["plans"] == [{
        "state_revision": 7,
        "observation_event_ids": ["obs-1"],
        "proposal": PlanProposal(response="synthetic plan").model_dump(mode="json"),
    }]
    assert report["counts"]["passed"] == 0


@pytest.mark.parametrize("phase", ["setup", "warmup"])
async def test_cancellation_preserves_phase_and_partial_report(tmp_path, phase):
    scenarios, output = tmp_path / "scenarios", tmp_path / "output"
    copy_scenarios(scenarios, count=2)
    entered = asyncio.Event()

    async def hold():
        entered.set()
        await asyncio.Event().wait()

    async def handler(request):
        if request.url.path == "/api/version":
            if phase == "setup":
                await hold()
            return httpx.Response(200, json={"version": "test"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma3:4b"}]})
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        raise AssertionError(request.url)

    class WaitingBackend(FakeBackend):
        async def warmup(self):
            await hold()

    task = asyncio.create_task(runner.run(args_for(scenarios, output),
        client_factory=mock_client_factory(handler), backend_factory=WaitingBackend))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    report = json.loads((output / "report.json").read_text())
    assert report["status"] == "cancelled"
    if phase == "setup":
        assert report["setup_failure"]["phase"] == "setup"
        assert report["not_run_count"] == 2
    else:
        assert report["cases"][0]["failure"]["phase"] == "warmup"
        assert report["cases"][0]["model_cleanup"] == "unloaded"
        assert report["counts"]["cancelled"] == 1
        assert report["not_run_count"] == 1
