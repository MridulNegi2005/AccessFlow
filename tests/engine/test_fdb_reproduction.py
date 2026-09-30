"""Offline packaging checks, never evidence of actual official model performance."""

import json
import subprocess
from types import SimpleNamespace
import wave

import pytest

from scripts import reproduce_fdb as fdb


def test_cli_preserves_scorer_virtual_environment_entrypoint(tmp_path, monkeypatch):
    scorer = tmp_path / "scorer-venv" / "bin" / "python"
    base = tmp_path / "base-python"
    base.touch()
    scorer.parent.mkdir(parents=True)
    try:
        scorer.symlink_to(base)
    except OSError:
        pytest.skip("Host cannot create executable symlinks")
    captured = []
    monkeypatch.setattr(fdb, "configured_environment", lambda *args: {})
    monkeypatch.setattr(fdb, "run_pipeline", lambda args, env:
                        captured.append(args.scorer_python) or {"status": "test"})
    assert fdb.main(["--fdb-root", str(tmp_path), "--scorer-python", str(scorer),
                     "--output", str(tmp_path / "evidence")]) == 0
    assert captured == [str(scorer.absolute())]
    assert captured[0] != str(base)


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


@pytest.mark.parametrize("rate,width,channels", [(16000, 2, 1), (48000, 4, 1), (48000, 4, 2), (22050, 3, 2)])
def test_original_pcm_formats_pass_without_resampling_or_modifying_files(tmp_path, rate, width, channels):
    audio = audio_tree(tmp_path)
    with wave.open(str(audio), "wb") as stream:
        stream.setparams((channels, width, rate, 0, "NONE", "not compressed"))
        stream.writeframes(b"\x00" * width * channels * 10)
    before = audio.read_bytes()
    assert fdb.recordings(tmp_path, expected=1) == [audio]
    assert fdb.recording_format(audio) == {"sample_rate_hz": rate, "channels": channels,
                                           "sample_width_bytes": width, "frames": 10}
    assert audio.read_bytes() == before


def test_empty_and_truncated_pcm_are_still_rejected(tmp_path):
    audio = audio_tree(tmp_path)
    with wave.open(str(audio), "wb") as stream:
        stream.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
    with pytest.raises(ValueError, match="nonempty"):
        fdb.recordings(tmp_path, expected=1)
    audio = audio.parent / "input.wav"
    audio.write_bytes(b"not a WAV")
    with pytest.raises(ValueError, match="header"):
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


def test_auditor_wraps_only_scoring_and_preserves_official_cli_arguments(tmp_path):
    original = fdb.commands(tmp_path, "scorer-python", tmp_path)
    audited = fdb.audited_commands(original, tmp_path)
    assert audited[0] == original[0]
    for raw, wrapped in zip(original[1:], audited[1:], strict=True):
        assert wrapped[0] == raw[0]
        assert wrapped[1].endswith("fdb_judge_audit.py")
        assert wrapped[wrapped.index("--script") + 1] == raw[1]
        assert wrapped[wrapped.index("--") + 1:] == raw[2:]
    diagnostic = fdb.audited_commands(original, tmp_path, semantic=False)
    assert diagnostic[1:3] == original[1:3]
    assert diagnostic[3][1].endswith("fdb_judge_audit.py")


def write_audits(tmp_path, statuses):
    for name, states in zip(("evaluate_tool_calls", "evaluate_pass_rate", "analyze_tool_latency"), statuses, strict=True):
        rows = [{"model": "gpt-4o", "status": state} for state in states]
        (tmp_path / f"{name}_judge_audit.json").write_text(json.dumps({"version": 1,
            "observed_requests": len(rows), "failed_requests": sum(state != "valid_response" for state in states),
            "requests": rows}))


@pytest.mark.parametrize("failure", ["request_error", "invalid_response"])
def test_swallowed_judge_failure_is_not_verified_even_with_three_complete_reports(tmp_path, failure):
    write_audits(tmp_path, [["valid_response"], [failure], ["valid_response"]])
    assert fdb.judge_evidence(tmp_path)["status"] == "unverified_failures"


def test_zero_and_partial_judge_observation_are_reported_honestly(tmp_path):
    write_audits(tmp_path, [[], [], []])
    assert fdb.judge_evidence(tmp_path)["status"] == "no_requests_observed"
    write_audits(tmp_path, [["valid_response"], [], ["valid_response"]])
    assert fdb.judge_evidence(tmp_path)["status"] == "partially_observed"
    write_audits(tmp_path, [["valid_response"], ["valid_response"], ["valid_response"]])
    assert fdb.judge_evidence(tmp_path)["status"] == "observed_valid_requests"


def test_forged_judge_counts_cannot_hide_request_failures(tmp_path):
    write_audits(tmp_path, [["request_error"], [], []])
    path = tmp_path / "evaluate_tool_calls_judge_audit.json"
    row = json.loads(path.read_text())
    row["failed_requests"] = 0
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="Inconsistent"):
        fdb.judge_evidence(tmp_path)


@pytest.mark.parametrize("state", ["valid_response", "request_error", None])
def test_pipeline_cannot_be_green_after_scorers_silently_swallow_judge_errors(tmp_path, monkeypatch, state):
    audio = audio_tree(tmp_path)
    (audio.parent / "result_accessflow.json").write_text('{"status":"completed"}')
    args = SimpleNamespace(fdb_root=tmp_path, scorer_python="scorer", output=tmp_path / "run",
                           mode="score", exact_match=False)
    monkeypatch.setattr(fdb, "git_output", lambda *args: "a-commit")
    monkeypatch.setattr(fdb, "preflight", lambda *args, **kwargs: {"input_count": 1})
    monkeypatch.setattr(fdb, "recordings", lambda *args: [audio])

    def upstream_success(command, **kwargs):
        for name in ("tool_accuracy.json", "strict_pass_rate.json"):
            (args.output / name).write_text('{"total_scenarios":1}')
        (args.output / "latency.json").write_text('{}')
        write_audits(args.output, [[state] if state else []] * 3)
        return SimpleNamespace(returncode=0, stdout="synthetic package freeze")

    monkeypatch.setattr(fdb.subprocess, "run", upstream_success)
    if state == "request_error":
        with pytest.raises(ValueError, match="fallback scores"):
            fdb.run_pipeline(args, {})
        manifest = json.loads((args.output / "manifest.json").read_text())
        assert manifest["status"] == "failed"
        assert manifest["judge_verification"]["status"] == "unverified_failures"
    else:
        manifest = fdb.run_pipeline(args, {})
        expected = "scored_with_recorded_outcomes" if state else "scored_with_incomplete_judge_observation"
        assert manifest["status"] == expected


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
    audio = audio_tree(tmp_path)
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
