import asyncio
import json
from pathlib import Path

from accessflow.contracts import PlanProposal
from accessflow.evaluation.replay import replay
from accessflow.evaluation.suite import run_suite


DEV = Path(__file__).resolve().parents[2] / "scenarios/dev"


async def test_development_suite_checks_effects_and_preserves_backend_identity(tmp_path):
    report = await run_suite(DEV.glob("*.json"), tmp_path)
    assert report["counts"] == {"passed": 4, "failed": 0, "unscored": 0, "error": 0}
    for case in report["cases"]:
        assert case["backend"] == "offline-fake"
        assert case["metrics"]["run_metadata"]["tools"] == "manifest-mock"
        assert case["metrics"]["committed_effect_outcomes"]["counts"]["committed"] == 1
    corrected = next(case for case in report["cases"] if case["scenario_file"] == "device_correction_during_write.json")
    rows = [json.loads(line) for line in Path(corrected["trace"]).read_text().splitlines()]
    cancellations = [row for row in rows if row.get("transport") == "executor_cancel"]
    assert len(cancellations) == 1
    assert cancellations[0]["event"]["payload"]["status"] == "cancelled"
    assert corrected["metrics"]["committed_effect_outcomes"]["counts"]["not_committed"] == 1


async def test_invalid_scenario_remains_in_suite_denominator(tmp_path):
    malformed = tmp_path / "invalid.json"
    malformed.write_text("not JSON")
    report = await run_suite([DEV / "text_correction.json", malformed], tmp_path / "results")
    assert report["scenario_count"] == 2
    assert report["counts"]["passed"] == 1
    assert report["counts"]["error"] == 1
    assert report["oracle_pass_rate_all_cases"] == 0.5


async def test_wrong_expected_effect_fails_a_completed_run(tmp_path):
    raw = json.loads((DEV / "text_correction.json").read_text())
    raw["expectation"]["effects"][0]["arguments"]["day"] = "Tuesday"
    source = tmp_path / "wrong-effect.json"
    source.write_text(json.dumps(raw))
    report = await run_suite([source], tmp_path / "results")
    assert report["cases"][0]["completion_status"] == "completed"
    assert report["counts"]["failed"] == 1
    assert report["oracle_pass_rate_all_cases"] == 0


async def test_live_provider_receives_no_fixture_steps_or_oracle(tmp_path):
    instances, views = [], []
    class Provider:
        async def plan(self, view, manifests):
            views.append(view.model_dump())
            return PlanProposal(response="Provider test double")
    def factory():
        instance = Provider()
        instances.append(instance)
        return instance
    report = await run_suite([DEV / "text_correction.json", DEV / "support_then_service.json"], tmp_path,
                             reasoner_factory=factory, backend="http-provider-double")
    assert len(instances) == 2 and instances[0] is not instances[1]
    assert views
    for view in views:
        assert not {"expectation", "proposals", "reasoning_steps", "expected_slots"}.intersection(view)
    assert report["counts"]["failed"] == 2  # fluent output alone cannot pass effect criteria


async def test_replay_waits_for_final_from_latest_input(tmp_path):
    raw = json.loads((DEV / "text_correction.json").read_text())
    raw["events"][1]["payload"].update(final=True, utterance_id="old")
    raw["events"][2]["payload"].update(final=True, utterance_id="new")
    del raw["proposals"]
    source = tmp_path / "two-turns.json"
    source.write_text(json.dumps(raw))
    class Provider:
        async def plan(self, view, manifests):
            latest = view.observations[-1]
            if latest.source_id == "new":
                await asyncio.sleep(0.08)
            return PlanProposal(response=latest.source_id)
    trace = tmp_path / "trace.jsonl"
    result = await replay(source, trace, reasoner=Provider(), backend="test-double")
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    finals = [r["event"] for r in rows if r.get("type") == "output" and r["event"]["kind"] == "final"]
    assert result["completion_status"] == "completed"
    assert [event["payload"]["text"] for event in finals] == ["old", "new"]


async def test_unknown_write_without_status_tool_is_not_retried(tmp_path):
    raw = json.loads((DEV / "lost_response_reconcile.json").read_text())
    raw["events"][0]["payload"]["tools"] = raw["events"][0]["payload"]["tools"][:1]
    raw["events"][0]["payload"]["tools"][0].pop("status_tool")
    raw["environment"].pop("query_receipt_v3")
    raw["reasoning_steps"] = raw["reasoning_steps"][:1]
    raw["terminal_output"] = {"kind": "clarify"}
    raw["expectation"] = {"require_final": False, "effects": raw["expectation"]["effects"],
                          "required_error_codes": ["write_outcome_unknown"]}
    source = tmp_path / "unknown-outcome.json"
    source.write_text(json.dumps(raw))
    report = await run_suite([source], tmp_path / "results")
    case = report["cases"][0]
    assert case["task_oracle"]["passed"] is True
    assert case["metrics"]["event_counts"]["output"]["tool_call"] == 1
    assert case["mock_effects"] == 1
    assert "final" not in case["metrics"]["event_counts"]["output"]
