import asyncio
import importlib
import json
from pathlib import Path

import pytest

from accessflow.contracts import OutputEvent, Snapshot
from accessflow.evaluation.suite import run_suite


replay_module = importlib.import_module("accessflow.evaluation.replay")
SCENARIO = Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json"


@pytest.mark.parametrize("failure", ["crash", "early_exit", "shutdown_hang"])
async def test_runtime_failure_keeps_trace_and_fails_oracle(monkeypatch, tmp_path, failure):
    class BrokenAgent:
        partial_debounce_s = 0.08

        def __init__(self, *args):
            pass

        async def run(self, incoming, outgoing):
            await incoming.get()
            if failure == "crash":
                raise RuntimeError("sensitive provider details must not be logged")
            if failure == "early_exit":
                return
            while True:
                event = await incoming.get()
                if event.kind == "transcript" and event.payload.final:
                    await outgoing.put(OutputEvent(session_id=event.session_id, kind="final",
                        payload={"caused_by_event_id": event.event_id, "text": "attempted final"},
                        state=Snapshot()))
                if event.kind == "session_end":
                    await asyncio.Event().wait()

    monkeypatch.setattr(replay_module, "Agent", BrokenAgent)
    monkeypatch.setattr(replay_module, "SHUTDOWN_TIMEOUT_S", 0.02)
    trace = tmp_path / "failure.jsonl"
    result = await asyncio.wait_for(replay_module.replay(SCENARIO, trace), 2)
    expected = {"crash": "agent_error", "early_exit": "agent_stopped", "shutdown_hang": "shutdown_timeout"}
    assert result["completion_status"] == expected[failure]
    assert result["task_oracle"]["passed"] is False
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert rows[0]["completion_status"] == expected[failure]
    assert any(r.get("event", {}).get("kind") == "session_end" for r in rows)
    assert "sensitive provider details" not in trace.read_text()
    if failure == "crash":
        assert rows[0]["failure_type"] == "RuntimeError"
    if failure == "shutdown_hang":
        assert any(r.get("event", {}).get("kind") == "final" for r in rows)


async def test_failed_unlabeled_run_is_not_classified_as_merely_unscored(tmp_path):
    raw = json.loads(SCENARIO.read_text())
    raw.pop("expectation")
    raw.update(proposals=[{}, {}], event_spacing_s=0, completion_timeout_s=0.01)
    source = tmp_path / "timeout.json"
    source.write_text(json.dumps(raw))
    report = await run_suite([source], tmp_path / "results")
    assert report["counts"]["failed"] == 1
    assert report["counts"]["unscored"] == 0
    assert report["oracle_pass_rate_all_cases"] == 0


def test_replay_cli_returns_nonzero_and_preserves_failed_result(monkeypatch, tmp_path, capsys):
    from accessflow.cli import main

    raw = json.loads(SCENARIO.read_text())
    raw["expectation"]["effects"] = []  # A completed write violates this explicit criterion.
    source, trace = tmp_path / "wrong.json", tmp_path / "trace.jsonl"
    source.write_text(json.dumps(raw))
    monkeypatch.setattr("sys.argv", ["accessflow", "replay", str(source), "--output", str(trace)])
    with pytest.raises(SystemExit) as failure:
        main()
    assert failure.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["completion_status"] == "completed"
    assert result["task_oracle"]["passed"] is False
    assert trace.exists()
