from pathlib import Path

from accessflow.evaluation.replay import commit_revision, replay


async def test_replay_without_git_executable(monkeypatch, tmp_path):
    monkeypatch.delenv("ACCESSFLOW_COMMIT", raising=False)
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr("accessflow.evaluation.replay.subprocess.run", missing_git)
    scenario = Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json"
    trace = tmp_path / "trace.jsonl"
    result = await replay(scenario, trace)
    assert result["mock_effects"] == 1
    assert '"commit": null' in trace.read_text()


def test_packaged_commit_can_be_supplied(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_COMMIT", "test-build-revision")
    assert commit_revision() == "test-build-revision"
