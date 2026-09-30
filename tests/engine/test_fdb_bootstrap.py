"""Offline setup safety checks; subprocess stand-ins do not prove installation."""

import os
from types import SimpleNamespace
import subprocess

import pytest

from scripts import bootstrap_fdb as setup
from scripts import reproduce_fdb as supervisor


def arguments(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "uv.lock").touch()
    fdb = tmp_path / "v3"
    fdb.mkdir()
    scorer = tmp_path / "scorer-python"
    scorer.touch()
    private = tmp_path / "private.env"
    private.write_text("GROQ_API_KEY=do-not-log-or-copy\n")
    monkeypatch.setattr(setup, "ROOT", root)
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv-command")
    return SimpleNamespace(fdb_root=fdb, scorer_python=scorer, env_file=private,
                           output=tmp_path / "evidence", agent_env=root / ".venv-fdb",
                           reuse_scorer=True, scorer_lock=None, mode="doctor",
                           exact_match=False, overwrite_results=False)


def test_frozen_agent_install_then_configuration_and_evaluation_without_secret_copy(tmp_path, monkeypatch):
    args = arguments(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda command, **kw: calls.append((command, kw)))
    setup.bootstrap(args)
    assert len(calls) == 2
    install, run = calls
    assert install[0][:2] == ["uv-command", "sync"]
    assert "--frozen" in install[0] and "--no-dev" in install[0]
    assert install[1]["env"]["UV_PROJECT_ENVIRONMENT"] == str(args.agent_env)
    assert "--env-file" in run[0] and str(args.env_file) in run[0]
    assert run[0][0].startswith(str(args.agent_env))
    assert run[0][-2:] == ["--mode", "doctor"]
    assert "do-not-log-or-copy" not in str(calls)
    assert not args.output.exists()
    assert args.env_file.read_text() == "GROQ_API_KEY=do-not-log-or-copy\n"


def test_scorer_install_requires_hashed_lock_in_separate_environment(tmp_path, monkeypatch):
    args = arguments(tmp_path, monkeypatch)
    args.reuse_scorer = False
    args.scorer_lock = tmp_path / "requirements.lock"
    args.scorer_lock.write_text("host-tested-lock")
    args.mode = "reproduce"
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda command, **kw: calls.append(command))
    setup.bootstrap(args)
    assert len(calls) == 3
    assert calls[1] == ["uv-command", "pip", "install", "--python", str(args.scorer_python),
                        "--require-hashes", "--requirements", str(args.scorer_lock)]
    assert calls[2][-1] == "reproduce"


@pytest.mark.parametrize("bad_path", ["root", "parent", "valuable-folder", "private-inside", "evidence-inside"])
def test_managed_install_cannot_overwrite_repository_credentials_or_evidence(tmp_path, monkeypatch, bad_path):
    args = arguments(tmp_path, monkeypatch)
    if bad_path == "root":
        args.agent_env = setup.ROOT
    elif bad_path == "parent":
        args.agent_env = tmp_path
    elif bad_path == "valuable-folder":
        args.agent_env.mkdir()
        (args.agent_env / "valuable.txt").write_text("preserve")
    elif bad_path == "private-inside":
        args.env_file = args.agent_env / "private.env"
    else:
        args.output = args.agent_env / "evidence"
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError):
        setup.bootstrap(args)
    assert calls == []


def test_failed_install_never_starts_a_voice_or_judge_run(tmp_path, monkeypatch):
    args = arguments(tmp_path, monkeypatch)
    calls = []

    def fail(command, **kw):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(setup.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        setup.bootstrap(args)
    assert len(calls) == 1


def test_existing_evidence_is_preserved_before_any_install(tmp_path, monkeypatch):
    args = arguments(tmp_path, monkeypatch)
    args.output.mkdir()
    retained = args.output / "old.json"
    retained.write_text("keep")
    with pytest.raises(ValueError, match="existing evidence"):
        setup.bootstrap(args)
    assert retained.read_text() == "keep"


def test_explicit_config_is_literal_and_process_environment_wins(tmp_path, monkeypatch):
    pytest.importorskip("dotenv")
    args = arguments(tmp_path, monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "environment-value")
    args.env_file.write_text("GROQ_API_KEY=file-value\nLIVEKIT_API_SECRET=literal-${GROQ_API_KEY}\nFDB_TOOL_LOG=wrong-path\n")
    (args.fdb_root / ".env.local").write_text("LIVEKIT_API_SECRET=lower-precedence\nFDB_GROQ_MODEL=model-from-clone\n")
    env = supervisor.configured_environment(args.fdb_root, args.env_file)
    assert env["GROQ_API_KEY"] == "environment-value"
    assert env["LIVEKIT_API_SECRET"] == "literal-${GROQ_API_KEY}"
    assert env["FDB_GROQ_MODEL"] == os.environ.get("FDB_GROQ_MODEL", "model-from-clone")
    assert env["FDB_TOOL_LOG"] != "wrong-path"


def test_explicit_missing_config_does_not_silently_use_another_file(tmp_path, monkeypatch):
    pytest.importorskip("dotenv")
    args = arguments(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="configuration"):
        supervisor.configured_environment(args.fdb_root, tmp_path / "missing.env")
