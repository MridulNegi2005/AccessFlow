import asyncio
import json

import pytest

import accessflow.evaluation.responsiveness as responsiveness


@pytest.mark.asyncio
async def test_each_probe_uses_actual_agent_and_keeps_blocked_workers_pending():
    records = []
    for index, scenario in enumerate(responsiveness._SCENARIOS, start=1):
        records.append(await responsiveness._run_one(index, scenario))

    assert [record["status"] for record in records] == ["passed"] * 4
    assert records[0]["gates"] == {"reasoner": "entered_pending"}
    assert records[1]["gates"] == {"reasoner": "entered_pending"}
    assert records[2]["gates"]["tool_at_cancel_emission"] == "entered_pending"
    assert records[2]["gates"]["cancellation_transport_at_cancel_emission"] == "not_entered"
    assert records[2]["gates"]["cancellation_transport_after_outputs"] == "entered_pending"
    assert records[3]["input_enqueue_to_final_s"] is not None
    assert records[2]["cancel_entry_to_emission_s"] is not None
    assert records[2]["input_enqueue_to_cancel_s"] >= 0
    assert records[2]["input_enqueue_to_ack_s"] >= 0


@pytest.mark.asyncio
async def test_run_responsiveness_writes_raw_jsonl_and_report_with_quantiles(tmp_path):
    report = await responsiveness.run_responsiveness(tmp_path, samples=2)

    assert report["counts"] == {"passed": 8, "failed": 0, "total": 8}
    assert report["samples_per_scenario"] == 2
    assert report["targets"]["acknowledgment_internal_300ms"]["expected_count"] == 8
    assert report["targets"]["cancellation_internal_50ms"]["expected_count"] == 2
    assert report["targets"]["acknowledgment_internal_300ms"]["failed_or_missing_count"] == 0
    assert report["targets"]["cancellation_internal_50ms"]["failed_or_missing_count"] == 0

    rows = [json.loads(line) for line in (tmp_path / "responsiveness.jsonl").read_text().splitlines()]
    assert rows[0]["schema_version"] == "responsiveness.v1"
    assert sum(row["type"] == "responsiveness_sample" for row in rows) == 8
    assert (tmp_path / "report.json").exists()
    assert report["limitation"].startswith("Synthetic offline orchestration evidence only")


@pytest.mark.asyncio
async def test_failed_samples_remain_in_target_denominator(tmp_path, monkeypatch):
    async def failed_probe(index, scenario):
        return {
            "type": "responsiveness_sample",
            "sample": index,
            "scenario": scenario,
            "session_id": f"failed-{index}-{scenario}",
            "status": "failed",
            "failure_type": "TimeoutError",
        }

    monkeypatch.setattr(responsiveness, "_run_one", failed_probe)
    report = await responsiveness.run_responsiveness(tmp_path, samples=2)

    assert report["counts"] == {"passed": 0, "failed": 8, "total": 8}
    assert report["targets"]["acknowledgment_internal_300ms"]["expected_count"] == 8
    assert report["targets"]["acknowledgment_internal_300ms"]["sample_count"] == 0
    assert report["targets"]["acknowledgment_internal_300ms"]["failed_or_missing_count"] == 8
    assert report["targets"]["acknowledgment_internal_300ms"]["pass_count"] == 0
    assert report["targets"]["acknowledgment_internal_300ms"]["pass_rate_over_expected"] == 0
    assert report["targets"]["cancellation_internal_50ms"]["expected_count"] == 2
    assert report["targets"]["cancellation_internal_50ms"]["failed_or_missing_count"] == 2


def test_samples_must_be_positive_integer(tmp_path):
    with pytest.raises(ValueError):
        asyncio.run(responsiveness.run_responsiveness(tmp_path, samples=0))
    with pytest.raises(ValueError):
        asyncio.run(responsiveness.run_responsiveness(tmp_path, samples=True))


def test_target_pass_requires_complete_samples_and_uses_strict_p95():
    records = [{"status": "passed", "latency_s": 0.010},
               {"status": "passed", "latency_s": 0.020},
               {"status": "passed", "latency_s": 0.030},
               {"status": "failed", "latency_s": 0.001}]

    result = responsiveness._metric(records, "latency_s", expected_count=4, target=0.03)

    assert result["sample_count"] == 3
    assert result["failed_or_missing_count"] == 1
    assert result["pass_count"] == 2
    assert result["target_passed"] is False
