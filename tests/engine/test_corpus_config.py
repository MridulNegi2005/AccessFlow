"""A17-2: replay() must accept an explicit corpus_root instead of relying only on the
process-global ACCESSFLOW_CORPUS_ROOT env var (see engine.Agent.__init__). Covers the
explicit-argument path, precedence over the env var, the env fallback still working,
isolation between two sequential replay() calls, early validation of a bad root, and
that recorded metadata never carries the absolute path.
"""

import sys
from pathlib import Path

import pytest

from accessflow import cli
from accessflow.engine import Agent
from accessflow.evaluation import replay as replay_module
from accessflow.evaluation.suite import run_suite

SCENARIO = Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json"


def capturing_agent(sink):
    """An Agent subclass that behaves exactly like the real thing but records every
    instance it builds, so a test can inspect what replay() actually constructed it
    with (_corpus_root, corpus_allowlist) without engine.py needing any test hook.
    """
    class CapturingAgent(Agent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            sink.append(self)
    return CapturingAgent


async def test_explicit_corpus_root_reaches_agent_with_no_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    root = tmp_path / "corpus_root"
    root.mkdir()
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl", corpus_root=str(root))
    assert captured[-1]._corpus_root == str(root)


async def test_explicit_corpus_root_overrides_different_env_var_value(tmp_path, monkeypatch):
    root = tmp_path / "explicit_root"
    root.mkdir()
    wrong = tmp_path / "wrong_root"
    wrong.mkdir()
    monkeypatch.setenv("ACCESSFLOW_CORPUS_ROOT", str(wrong))
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl", corpus_root=str(root))
    assert captured[-1]._corpus_root == str(root)
    assert captured[-1]._corpus_root != str(wrong)


async def test_env_var_fallback_still_honoured_without_explicit_argument(tmp_path, monkeypatch):
    root = tmp_path / "env_root"
    root.mkdir()
    monkeypatch.setenv("ACCESSFLOW_CORPUS_ROOT", str(root))
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl")
    assert captured[-1]._corpus_root == str(root)


async def test_second_run_without_explicit_root_does_not_inherit_first(tmp_path, monkeypatch):
    """Two sequential replay() calls in one process must not leak state between them:
    a root (and allowlist) configured for the first run must not survive into a second
    run that supplies neither an explicit argument nor the env var.
    """
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    root = tmp_path / "first_root"
    root.mkdir()
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))

    await replay_module.replay(SCENARIO, tmp_path / "trace1.jsonl", corpus_root=str(root))
    assert captured[0]._corpus_root == str(root)
    assert captured[0].corpus_allowlist == frozenset()

    await replay_module.replay(SCENARIO, tmp_path / "trace2.jsonl")
    assert captured[1] is not captured[0]
    assert captured[1]._corpus_root is None
    assert captured[1].corpus_allowlist == frozenset()


async def test_explicit_corpus_root_nonexistent_path_raises_clear_error(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="does-not-exist"):
        await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl", corpus_root=str(missing))


async def test_explicit_corpus_root_must_be_a_directory_not_a_file(tmp_path):
    not_a_dir = tmp_path / "just_a_file.txt"
    not_a_dir.write_text("not a corpus root", encoding="utf-8")
    with pytest.raises(ValueError):
        await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl", corpus_root=str(not_a_dir))


async def test_recorded_metadata_carries_configured_and_basename_not_absolute_path(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    root = tmp_path / "my_secret_home_dir_marker"
    root.mkdir()
    trace = tmp_path / "trace.jsonl"
    await replay_module.replay(SCENARIO, trace, corpus_root=str(root))
    metadata = replay_module.load_run_metadata(trace)
    config = metadata["config"]
    assert config["corpus_root_configured"] is True
    assert config["corpus_root_basename"] == root.name
    dumped = trace.read_text(encoding="utf-8")
    assert str(root) not in dumped
    assert str(root.resolve()) not in dumped


async def test_recorded_metadata_reflects_env_fallback_when_no_explicit_argument(tmp_path, monkeypatch):
    root = tmp_path / "env_marker_dir"
    root.mkdir()
    monkeypatch.setenv("ACCESSFLOW_CORPUS_ROOT", str(root))
    trace = tmp_path / "trace.jsonl"
    await replay_module.replay(SCENARIO, trace)
    metadata = replay_module.load_run_metadata(trace)
    config = metadata["config"]
    assert config["corpus_root_configured"] is True
    assert config["corpus_root_basename"] == root.name


async def test_no_corpus_root_anywhere_leaves_metadata_unconfigured(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    trace = tmp_path / "trace.jsonl"
    await replay_module.replay(SCENARIO, trace)
    metadata = replay_module.load_run_metadata(trace)
    config = metadata["config"]
    assert config["corpus_root_configured"] is False
    assert config["corpus_root_basename"] is None


# --- run_suite() threading (A17-2 continued: suite.py + cli.py) -------------------


async def test_run_suite_explicit_corpus_root_reaches_agent_of_each_scenario(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    root = tmp_path / "suite_corpus_root"
    root.mkdir()
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    await run_suite([SCENARIO, SCENARIO], tmp_path / "out", corpus_root=str(root))
    assert len(captured) == 2
    for agent in captured:
        assert agent._corpus_root == str(root)


async def test_run_suite_env_fallback_still_honoured_without_explicit_root(tmp_path, monkeypatch):
    root = tmp_path / "suite_env_root"
    root.mkdir()
    monkeypatch.setenv("ACCESSFLOW_CORPUS_ROOT", str(root))
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    await run_suite([SCENARIO], tmp_path / "out")
    assert captured[-1]._corpus_root == str(root)


async def test_run_suite_missing_corpus_root_raises_once_before_any_scenario_runs(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    missing = tmp_path / "does-not-exist"
    output_dir = tmp_path / "out"
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))
    with pytest.raises(ValueError, match="does-not-exist"):
        await run_suite([SCENARIO, SCENARIO], output_dir, corpus_root=str(missing))
    # No scenario reached replay()/Agent, and no trace or report file was written.
    assert captured == []
    assert not output_dir.exists()


async def test_run_suite_second_call_without_root_does_not_inherit_first(tmp_path, monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_CORPUS_ROOT", raising=False)
    root = tmp_path / "suite_first_root"
    root.mkdir()
    captured = []
    monkeypatch.setattr(replay_module, "Agent", capturing_agent(captured))

    await run_suite([SCENARIO], tmp_path / "out1", corpus_root=str(root))
    assert captured[0]._corpus_root == str(root)

    await run_suite([SCENARIO], tmp_path / "out2")
    assert captured[1] is not captured[0]
    assert captured[1]._corpus_root is None


def capturing_replay(sink):
    async def fake_replay(*args, **kwargs):
        sink.append(kwargs)
        return {"trace": str(args[1]), "backend": kwargs.get("backend", "offline-fake"), "events": 0,
                "mock_effects": 0, "completion_status": "completed", "task_oracle": {"passed": True}}
    return fake_replay


def capturing_run_suite(sink):
    async def fake_run_suite(*args, **kwargs):
        sink.append(kwargs)
        return {"report_version": "development-suite.v1", "backend": kwargs.get("backend", "offline-fake"),
                "scenario_count": 0, "counts": {"passed": 0, "failed": 0, "unscored": 0, "error": 0},
                "oracle_pass_rate_all_cases": None, "cases": [], "limitation": ""}
    return fake_run_suite


def test_cli_replay_subcommand_passes_explicit_corpus_root_through(tmp_path, monkeypatch):
    root = tmp_path / "cli_replay_root"
    root.mkdir()
    trace = tmp_path / "trace.jsonl"
    captured = []
    monkeypatch.setattr(cli, "replay", capturing_replay(captured))
    monkeypatch.setattr(sys, "argv", ["accessflow", "replay", str(SCENARIO), "--output", str(trace),
                                      "--corpus-root", str(root)])
    cli.main()
    assert len(captured) == 1
    assert captured[0]["corpus_root"] == str(root.resolve())


# --- Security review finding 3: corpus_root="" must not silently become the CWD ----
#
# Path("") and Path("   ") both coerce to Path(".") -- the process CWD -- whose
# is_dir() is True, so a falsy-but-not-None corpus_root previously sailed through the
# "must be an existing directory" check and silently became the corpus trust boundary.


@pytest.mark.parametrize("bad_root", ["", "   "])
async def test_replay_rejects_empty_or_blank_corpus_root_instead_of_using_cwd(tmp_path, bad_root):
    with pytest.raises(ValueError, match="existing directory"):
        await replay_module.replay(SCENARIO, tmp_path / "trace.jsonl", corpus_root=bad_root)


@pytest.mark.parametrize("bad_root", ["", "   "])
async def test_run_suite_rejects_empty_or_blank_corpus_root_instead_of_using_cwd(tmp_path, bad_root):
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="existing directory"):
        await run_suite([SCENARIO], output_dir, corpus_root=bad_root)
    assert not output_dir.exists()


def test_cli_suite_subcommand_passes_explicit_corpus_root_through(tmp_path, monkeypatch):
    root = tmp_path / "cli_suite_root"
    root.mkdir()
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()
    output_dir = tmp_path / "out"
    captured = []
    monkeypatch.setattr(cli, "run_suite", capturing_run_suite(captured))
    monkeypatch.setattr(sys, "argv", ["accessflow", "suite", str(scenario_dir), "--output-dir", str(output_dir),
                                      "--corpus-root", str(root)])
    cli.main()
    assert len(captured) == 1
    assert captured[0]["corpus_root"] == str(root.resolve())
