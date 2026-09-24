"""A completed harness/report is not proof of provider or factual success."""

import json
from types import SimpleNamespace

import pytest

from scripts import run_samsung_screen as screen
from scripts.run_samsung_check import write_report


def report(**updates):
    data = {"failure": None, "score": {"total": 100}, "model_evidence": {"requests": [
        {"outcome": "success", "prompt_tokens": 100}, {"outcome": "cancelled"},
        {"outcome": "rate_limited"}]}, "trace": [
            {"kind": "action", "action": "clarification_request", "payload": {"text": "Which one?"}},
            {"kind": "action", "action": "final_response", "t_ms": 5000, "payload": {"text": "Result"}}],
            "provenance": {"source_sha256": "stable"}}
    data.update(updates)
    return data


def test_score_does_not_hide_missing_usage_provider_failures_or_clarifications():
    row = screen.summarize(report())
    assert row["scorer_total"] == 100
    assert row["provider_outcomes"] == ["success", "cancelled", "rate_limited"]
    assert row["usage_missing_count"] == 2
    assert row["reported_input_tokens"] == 100
    assert row["clarifications"] == ["Which one?"]
    assert row["finals"] == [{"t_ms": 5000, "text": "Result"}]


@pytest.mark.parametrize("malformed", [{}, [], {"trace": None}, {"score": 100}])
def test_malformed_report_is_not_a_finished_attempt(malformed):
    with pytest.raises(ValueError):
        screen.summarize(malformed)


@pytest.mark.parametrize("score", [None, {}, {"total": True}, {"total": float("nan")}, {"total": 101}])
def test_missing_or_invalid_score_requires_explicit_failure(score):
    with pytest.raises(ValueError):
        screen.summarize(report(score=score))


def test_setup_failure_remains_reportable_without_model_or_score():
    row = screen.summarize(report(score=None, model_evidence=None, trace=[], failure="setup_timeout"))
    assert row["failure"] == "setup_timeout"
    assert row["scorer_total"] is None and row["finals"] == []


def test_substantive_text_latency_uses_latest_user_turn_not_filler_or_scenario_end():
    r = report(trace=[
        {"kind": "action", "action": "final_response", "t_ms": 50, "payload": {"text": "Old answer"}},
        {"kind": "event", "event_type": "interruption", "t_ms": 100, "payload": {"text": "Correction"}},
        {"kind": "action", "action": "filler_speech", "t_ms": 110, "payload": {"text": "Listening"}},
        {"kind": "event", "event_type": "scenario_end", "t_ms": 999, "payload": {}},
        {"kind": "action", "action": "clarification_request", "t_ms": 300, "payload": {"text": "Which one?"}},
    ])
    assert screen.summarize(r)["last_text_turn_to_response_ms"] == 200
    assert screen.summarize(report())["last_text_turn_to_response_ms"] is None


def test_harness_cancellation_events_are_not_lost_because_they_are_not_actions():
    events = [{"kind": "tool_cancelled", "call_id": "a", "t_ms": 200},
              {"kind": "cancel_noop", "call_id": "b", "t_ms": 300}]
    assert screen.summarize(report(trace=events))["cancellations"] == events


def configure(tmp_path, monkeypatch, scenarios=("a.json", "b.json")):
    monkeypatch.setenv("ACCESSFLOW_SAMSUNG_BACKEND", "groq")
    monkeypatch.setenv("ACCESSFLOW_GROQ_MODEL", "test-model")
    kit = tmp_path / "kit"
    (kit / "scenarios").mkdir(parents=True)
    for name in scenarios:
        (kit / "scenarios" / name).write_text("{}", encoding="utf-8")
    output = tmp_path / "reports"
    monkeypatch.setattr(screen.sys, "argv", ["screen", "--kit", str(kit), "--scenarios", *scenarios,
                                           "--output", str(output), "--cooldown", "0"])
    monkeypatch.setattr(screen, "source_evidence", lambda _: {"source_sha256": "stable"})
    monkeypatch.setattr(screen, "commit_revision", lambda: "test")
    return output


@pytest.mark.parametrize("missing", ["backend", "model", "unknown_backend"])
def test_screen_refuses_implicit_model_selection_before_creating_outputs(tmp_path, monkeypatch, missing):
    output = configure(tmp_path, monkeypatch)
    if missing == "unknown_backend":
        monkeypatch.setenv("ACCESSFLOW_SAMSUNG_BACKEND", "unknown")
    else:
        monkeypatch.delenv("ACCESSFLOW_SAMSUNG_BACKEND" if missing == "backend" else "ACCESSFLOW_GROQ_MODEL")
    with pytest.raises(SystemExit):
        screen.main()
    assert not output.exists()


def test_failed_child_is_retained_once_and_does_not_replace_later_report(tmp_path, monkeypatch):
    output = configure(tmp_path, monkeypatch)
    calls = []

    def child(command, **kwargs):
        calls.append(command)
        destination = command[command.index("--output") + 1]
        write_report(destination, report(failure="setup_timeout" if len(calls) == 1 else None))
        return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)

    monkeypatch.setattr(screen.subprocess, "run", child)
    with pytest.raises(SystemExit):
        screen.main()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert len(calls) == 2
    assert summary["attempts"][0]["failure"] == "setup_timeout"
    assert summary["attempts"][1]["failure"] is None
    assert (output / "attempt-01.json").exists() and (output / "attempt-02.json").exists()
    before = (output / "a.json").read_bytes()
    with pytest.raises(FileExistsError):
        screen.main()
    assert (output / "a.json").read_bytes() == before


def test_timeout_reason_survives_absent_report(tmp_path, monkeypatch):
    output = configure(tmp_path, monkeypatch, scenarios=("a.json",))

    def child(command, **kwargs):
        raise screen.subprocess.TimeoutExpired(command, 450)

    monkeypatch.setattr(screen.subprocess, "run", child)
    with pytest.raises(SystemExit):
        screen.main()
    row = json.loads((output / "attempt-01.json").read_text(encoding="utf-8"))
    assert row["runner_failure"] == "child_timeout"


def test_source_drift_during_last_child_cannot_be_labeled_consistent(tmp_path, monkeypatch):
    output = configure(tmp_path, monkeypatch, scenarios=("a.json",))
    current = ["stable"]
    monkeypatch.setattr(screen, "source_evidence", lambda _: {"source_sha256": current[0]})

    def child(command, **kwargs):
        write_report(command[command.index("--output") + 1], report())
        current[0] = "changed"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(screen.subprocess, "run", child)
    with pytest.raises(SystemExit):
        screen.main()
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["state"] == "source_changed"
    assert len(summary["attempts"]) == 1
