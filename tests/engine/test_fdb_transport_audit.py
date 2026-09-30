"""Actual child-process failures remain observable and credentials stay private."""
import json
import subprocess
import sys

import pytest

from scripts import fdb_transport_audit as audit


def test_actual_swallowed_child_failure_is_preserved_and_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_SECRET", "private-test-credential")
    child = tmp_path / "livekit_inference.py"
    child.write_text("import os,sys\nprint(os.environ['LIVEKIT_API_SECRET'],file=sys.stderr)\nraise SystemExit(7)\n")
    output = tmp_path / "audit.jsonl"
    observed = audit.observe_run(subprocess.run, output)
    with pytest.raises(subprocess.CalledProcessError) as caught:
        observed([sys.executable, str(child)], capture_output=True, text=True, check=True)
    assert caught.value.returncode == 7
    row = json.loads(output.read_text())
    assert row["status"] == "failed" and row["exit_code"] == 7
    assert "private-test-credential" not in output.read_text()
    assert "[REDACTED]" in row["stderr"]


def test_success_returns_original_result_and_does_not_store_user_audio_text(tmp_path):
    child = tmp_path / "livekit_inference.py"
    child.write_text("print('private-speech-content')\n")
    output = tmp_path / "audit.jsonl"
    result = audit.observe_run(subprocess.run, output)(
        [sys.executable, str(child)], capture_output=True, text=True, check=True)
    assert result.returncode == 0 and result.stdout.strip() == "private-speech-content"
    assert "private-speech-content" not in output.read_text()
    assert json.loads(output.read_text())["status"] == "finished"


def test_unrelated_child_calls_are_unchanged_and_unrecorded(tmp_path):
    output = tmp_path / "audit.jsonl"
    result = audit.observe_run(subprocess.run, output)([sys.executable, "-c", "print('ok')"],
                                                       capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "ok" and not output.exists()


def test_wrapper_executes_original_arguments_and_restores_global_runner(tmp_path):
    script = tmp_path / "batch.py"
    script.write_text("import sys\nassert sys.argv[1:]==['--provider','accessflow']\n")
    original = subprocess.run
    assert audit.main(["--script", str(script), "--output", str(tmp_path / "audit.jsonl"),
                       "--", "--provider", "accessflow"]) == 0
    assert subprocess.run is original
    with pytest.raises(SystemExit):
        audit.main(["--script", str(script), "--output", str(tmp_path / "audit.jsonl")])
