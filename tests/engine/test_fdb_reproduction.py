"""Offline packaging checks, never evidence of actual official model performance."""

import json
import subprocess
from types import SimpleNamespace
import wave

import pytest

from scripts import reproduce_fdb as fdb


def audio_tree(tmp_path):
    folder = tmp_path / ("generic_case_" + "a" * 24)
    folder.mkdir()
    audio = folder / "input.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\x00\x00" * 10)
    (folder / "metadata.json").write_text('{"expected_answer":"not loaded"}')
    return audio


def test_released_recording_layout_and_denominator_are_validated(tmp_path):
    audio = audio_tree(tmp_path)
    assert fdb.recordings(tmp_path, expected=1) == [audio]
    with pytest.raises(ValueError, match="100"):
        fdb.recordings(tmp_path)
    (audio.parent / "metadata.json").unlink()
    with pytest.raises(ValueError, match="missing"):
        fdb.recordings(tmp_path, expected=1)


def test_benchmark_cli_uses_pinned_scripts_real_audio_and_semantic_judge(tmp_path):
    plan = fdb.commands(tmp_path / "v3", "scorer python", tmp_path / "private run")
    assert "--root_dir" in plan[0]
    assert plan[0][-1].endswith("fdb_v3_data_released")
    assert all("--use-llm" in command for command in plan[1:3])
    assert plan[3][1].endswith("analyze_tool_latency.py")
    assert not any("--force" in command or "--asr-only" in command for command in plan)
    assert not any("--example" in command for command in plan)
    assert not any("--use-llm" in command for command in fdb.commands(tmp_path, "py", tmp_path, semantic=False))


def test_config_does_not_serialize_secrets_or_arbitrary_environment():
    env = {"GROQ_API_KEY": "secret-one", "OPENAI_API_KEY": "secret-two",
           "LIVEKIT_API_SECRET": "secret-three", "EXTRA_PRIVATE": "secret-four",
           "FDB_GROQ_MODEL": "a-model"}
    config = fdb.sanitized_config(env)
    assert config["FDB_GROQ_MODEL"] == "a-model"
    assert set(config) == set(fdb.CONFIG)
    assert "secret" not in json.dumps(config)


def test_retained_evidence_excludes_expected_answers_and_unrelated_rooms(tmp_path):
    audio = audio_tree(tmp_path)
    (audio.parent / "result_accessflow.json").write_text('{"room_name":"current","status":"completed"}')
    (audio.parent / "output_accessflow.wav").write_bytes(b"output bytes")
    telemetry = tmp_path / "telemetry.jsonl"
    telemetry.write_text('{"room":"current","call":{"tool":"generic"}}\n'
                         '{"room":"other","private":"unrelated"}\n')
    evidence = tmp_path / "private-evidence"
    retained = fdb.preserve_outputs([audio], evidence, telemetry)
    assert len(retained) == 3
    assert not list(evidence.rglob("metadata.json"))
    assert not list(evidence.rglob("input.wav"))
    assert "unrelated" not in (evidence / "room_tool_calls.jsonl").read_text()
    assert len((evidence / "room_tool_calls.jsonl").read_text().splitlines()) == 1


def test_zero_exit_batch_cannot_hide_missing_or_malformed_results(tmp_path):
    audio = audio_tree(tmp_path)
    result_path = audio.parent / "result_accessflow.json"
    assert fdb.verify_results([audio])["missing"] == [audio.parent.name]
    result_path.write_text("not JSON")
    assert fdb.verify_results([audio])["status_counts"] == {"malformed": 1}
    result_path.write_text('{"status":"failed"}')
    assert fdb.verify_results([audio])["status_counts"] == {"failed": 1}


@pytest.mark.parametrize("count", [0, 99, "100", True])
def test_official_reports_cannot_claim_full_score_from_partial_denominator(tmp_path, count):
    (tmp_path / "tool_accuracy.json").write_text(json.dumps({"total_scenarios": count}))
    with pytest.raises(ValueError, match="denominator"):
        fdb.verify_reports(tmp_path, 100)


def test_all_report_files_are_required(tmp_path):
    for name in ("tool_accuracy.json", "strict_pass_rate.json"):
        (tmp_path / name).write_text('{"total_scenarios":100}')
    with pytest.raises(ValueError, match="latency"):
        fdb.verify_reports(tmp_path, 100)
    (tmp_path / "latency.json").write_text('{}')
    fdb.verify_reports(tmp_path, 100)


def test_pipeline_records_failed_preflight_and_preserves_existing_evidence(tmp_path, monkeypatch):
    args = SimpleNamespace(fdb_root=tmp_path, scorer_python="scorer", output=tmp_path / "run",
                           mode="reproduce", exact_match=False)
    monkeypatch.setattr(fdb, "git_output", lambda *args: "some-commit")

    def absent(*args, **kwargs):
        raise ValueError("Missing private settings: LIVEKIT_API_SECRET")

    monkeypatch.setattr(fdb, "preflight", absent)
    with pytest.raises(ValueError, match="private"):
        fdb.run_pipeline(args, {"LIVEKIT_API_SECRET": "do-not-record"})
    manifest = json.loads((args.output / "manifest.json").read_text())
    assert manifest["status"] == "failed"
    assert manifest["failure"] == "Missing private settings: LIVEKIT_API_SECRET"
    assert "do-not-record" not in json.dumps(manifest)
    with pytest.raises(ValueError, match="prior evidence"):
        fdb.run_pipeline(args, {})


def test_preflight_is_not_reported_as_evaluation(tmp_path, monkeypatch):
    args = SimpleNamespace(fdb_root=tmp_path, scorer_python="scorer", output=tmp_path / "run",
                           mode="doctor", exact_match=False)
    monkeypatch.setattr(fdb, "git_output", lambda *args: "a-commit")
    monkeypatch.setattr(fdb, "preflight", lambda *args, **kwargs: {"input_count": 100})
    monkeypatch.setattr(fdb, "recordings", lambda *args: [])
    result = fdb.run_pipeline(args, {})
    assert result["status"] == "preflight_passed_not_evaluated"
    assert "results" not in result


def test_scoring_only_needs_no_voice_worker_credentials_or_nemo(tmp_path, monkeypatch):
    scorer = tmp_path / "scorer-python"
    scorer.touch()
    for name in fdb.REQUIRED:
        (tmp_path / name).write_text("reference-source")
    audio = tmp_path / "example.wav"
    audio.write_bytes(b"recording")
    monkeypatch.setattr(fdb, "git_output", lambda path, *args: fdb.PIN if args[0] == "rev-parse" else "")
    monkeypatch.setattr(fdb, "recordings", lambda *args: [audio])
    monkeypatch.setattr(fdb.shutil, "which", lambda *args: None)
    calls = []
    monkeypatch.setattr(fdb.subprocess, "run", lambda command, **kwargs: calls.append(command))
    result = fdb.preflight(tmp_path, str(scorer), {"OPENAI_API_KEY": "private"}, need_inference=False)
    assert result["input_count"] == 1
    assert len(calls) == 1
    assert "nemo" not in calls[0][-1]
    assert "livekit" not in calls[0][-1]


def test_old_output_wav_without_result_json_cannot_skip_real_inference(tmp_path, monkeypatch):
    args = SimpleNamespace(fdb_root=tmp_path, scorer_python="scorer", output=tmp_path / "run",
                           mode="reproduce", exact_match=False, overwrite_results=False)
    audio = audio_tree(tmp_path)
    (audio.parent / "output_accessflow.wav").write_bytes(b"old response")
    monkeypatch.setattr(fdb, "git_output", lambda *args: "a-commit")
    monkeypatch.setattr(fdb, "preflight", lambda *args, **kwargs: {"input_count": 1})
    monkeypatch.setattr(fdb, "recordings", lambda *args: [audio])
    with pytest.raises(ValueError, match="reused"):
        fdb.run_pipeline(args, {})
    manifest = json.loads((args.output / "manifest.json").read_text())
    assert manifest["status"] == "failed"


def test_worker_is_stopped_on_pipeline_failure(tmp_path, monkeypatch):
    args = SimpleNamespace(fdb_root=tmp_path, scorer_python="scorer", output=tmp_path / "run",
                           mode="reproduce", exact_match=False, overwrite_results=False,
                           registration_timeout=1)
    audio = audio_tree(tmp_path)
    worker = SimpleNamespace()
    stops = []
    monkeypatch.setattr(fdb, "git_output", lambda *args: "a-commit")
    monkeypatch.setattr(fdb, "preflight", lambda *args, **kwargs: {"input_count": 1})
    monkeypatch.setattr(fdb, "recordings", lambda *args: [audio])
    monkeypatch.setattr(fdb.subprocess, "Popen", lambda *args, **kw: worker)
    monkeypatch.setattr(fdb, "stop_worker", lambda value: stops.append(value))

    def failed(*args):
        raise TimeoutError("Worker registration not observed before timeout")

    monkeypatch.setattr(fdb, "wait_registered", failed)
    with pytest.raises(TimeoutError):
        fdb.run_pipeline(args, {})
    assert stops == [worker]
    assert json.loads((args.output / "manifest.json").read_text())["status"] == "failed"


def test_stop_worker_uses_terminate_then_bounded_kill_only_on_its_handle():
    actions = []

    class Worker:
        def poll(self):
            return None

        def terminate(self):
            actions.append("terminate")

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("own-worker", timeout)
            actions.append("wait")

        def kill(self):
            actions.append("kill")

    fdb.stop_worker(Worker())
    assert actions == ["terminate", "kill", "wait"]
