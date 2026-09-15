import datetime as dt
import json
import os
from pathlib import Path

from accessflow.evaluation.replay import replay
from scripts.model_scoreboard import collect_records, main, matrix, per_model, table, summarize

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "scenarios/dev/text_correction.json"


def write_trace(path, *, model="test/model", scenario="scenario-a", oracle=True,
                 status="completed", run_id=None, run_ended_at=None, ablated=False):
    metadata = {
        "type": "run_metadata",
        "backend": model,
        "scenario": scenario,
        "completion_status": status,
        "task_oracle": {"passed": oracle} if oracle is not None else None,
        "disabled_components": ["stale_result_guard"] if ablated else [],
        "reasoner_evidence": {"requests": [{"outcome": "success", "elapsed_seconds": 1.5,
                                             "status_code": 200}]},
    }
    if run_id is not None:
        metadata["run_id"] = run_id
    if run_ended_at is not None:
        metadata["run_ended_at"] = run_ended_at
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")


def set_mtime(path, when: dt.datetime):
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def test_recorded_timestamp_wins_over_reverse_lexical_filename_order(tmp_path):
    # "a-*" sorts before "z-*" lexically, but the run recorded inside "a-*" happened
    # later. The old code picked by filename tiebreak within a date; this must not.
    older = tmp_path / "z-older.jsonl"
    newer = tmp_path / "a-newer.jsonl"
    write_trace(older, oracle=False, run_id="run-old",
                run_ended_at="2026-09-14T08:00:00+00:00")
    write_trace(newer, oracle=True, run_id="run-new",
                run_ended_at="2026-09-14T20:00:00+00:00")
    # Both files share the same mtime day/order the old bug relied on.
    same_day = dt.datetime(2026, 9, 14, 12, 0, 0, tzinfo=dt.timezone.utc)
    set_mtime(older, same_day)
    set_mtime(newer, same_day)

    records, exclusions = collect_records(tmp_path)
    assert exclusions == []
    section = per_model(records)
    assert "scenario-a" in section
    # The newer (a-newer.jsonl) run passed; its verdict must be the reported Latest.
    row = [line for line in section.splitlines() if line.startswith("| scenario-a")][0]
    assert "| pass |" in row
    assert "2026-09-14T20:00:00+00:00" in row


def test_copied_file_with_changed_mtime_does_not_override_recorded_time(tmp_path):
    original = tmp_path / "original.jsonl"
    write_trace(original, oracle=False, run_id="run-1",
                run_ended_at="2026-09-01T00:00:00+00:00")
    set_mtime(original, dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc))

    copy_no_id = tmp_path / "copy_no_id.jsonl"
    # Simulate a historical trace with no run_id/timestamp: only mtime distinguishes it,
    # and a filesystem copy can make that mtime look newer than reality.
    write_trace(copy_no_id, oracle=True, scenario="scenario-b")
    set_mtime(copy_no_id, dt.datetime(2099, 1, 1, tzinfo=dt.timezone.utc))

    records, exclusions = collect_records(tmp_path)
    assert exclusions == []
    inferred = [r for r in records if r["scenario"] == "scenario-b"][0]
    assert inferred["time_source"] == "mtime_inferred"
    assert "order unverified" in inferred["when"]


def test_duplicate_run_id_is_deduplicated_and_reported(tmp_path):
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    write_trace(first, run_id="dup-1", oracle=True)
    write_trace(second, run_id="dup-1", oracle=True)

    records, exclusions = collect_records(tmp_path)
    assert len(records) == 1
    assert any("duplicate_run_id" in item["reason"] for item in exclusions)


def test_null_oracle_is_unscored_not_a_failure(tmp_path):
    trace = tmp_path / "unscored.jsonl"
    write_trace(trace, oracle=None, run_id="run-null")

    records, exclusions = collect_records(tmp_path)
    assert exclusions == []
    assert records[0]["oracle"] is None
    matrix_text = matrix(records, minimum=1)
    assert "unscored" in matrix_text
    table_text = table(summarize(records))
    assert "unscored" in table_text


def test_malformed_json_is_excluded_and_reported_not_swallowed(tmp_path):
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")
    bad = tmp_path / "bad.jsonl"
    bad.write_text("{not valid json\n", encoding="utf-8")

    records, exclusions = collect_records(tmp_path)
    assert len(records) == 1
    reasons = [item["reason"] for item in exclusions]
    assert any("malformed_json" in reason for reason in reasons)
    assert any(item["path"].endswith("bad.jsonl") for item in exclusions)


def test_non_object_json_lines_are_excluded_and_reported_not_crashed(tmp_path):
    # A syntactically valid JSON value that is not an object (array, null, bare
    # string) used to reach `candidate.get(...)` and raise AttributeError.
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")

    non_objects = {
        "array.jsonl": "[]\n",
        "null.jsonl": "null\n",
        "string.jsonl": '"just a string"\n',
    }
    for name, content in non_objects.items():
        (tmp_path / name).write_text(content, encoding="utf-8")

    records, exclusions = collect_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == "run-good"
    for name in non_objects:
        matches = [item for item in exclusions if item["path"].endswith(name)]
        assert any("invalid_record_type" in item["reason"] for item in matches), matches

    by_model = summarize(records)
    assert by_model["test/model"]["runs"] == 1
    assert by_model["test/model"]["passed"] == 1


def _write_metadata(path, **overrides):
    metadata = {
        "type": "run_metadata",
        "backend": "test/model",
        "scenario": "scenario-a",
        "completion_status": "completed",
        "task_oracle": {"passed": True},
        "disabled_components": [],
        "reasoner_evidence": {"requests": [{"outcome": "success", "elapsed_seconds": 1.0,
                                             "status_code": 200}]},
    }
    metadata.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata) + "\n", encoding="utf-8")


def test_wrong_type_timestamp_is_excluded_and_reported_not_crashed(tmp_path):
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")
    bad = tmp_path / "bad_timestamp.jsonl"
    _write_metadata(bad, run_id="run-bad-ts", run_ended_at=1234567890)

    records, exclusions = collect_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == "run-good"
    reasons = [item["reason"] for item in exclusions if item["path"].endswith("bad_timestamp.jsonl")]
    assert any("invalid_record_shape" in r and "run_ended_at" in r for r in reasons), reasons


def test_malformed_requests_list_is_excluded_and_reported_not_crashed(tmp_path):
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")
    bad = tmp_path / "bad_requests.jsonl"
    _write_metadata(bad, run_id="run-bad-requests", reasoner_evidence={"requests": "not-a-list"})

    records, exclusions = collect_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == "run-good"
    reasons = [item["reason"] for item in exclusions if item["path"].endswith("bad_requests.jsonl")]
    assert any("requests must be a list" in r for r in reasons), reasons


def test_malformed_request_entry_is_excluded_and_reported_not_crashed(tmp_path):
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")
    bad = tmp_path / "bad_request_entry.jsonl"
    _write_metadata(bad, run_id="run-bad-entry", reasoner_evidence={"requests": ["not-an-object"]})

    records, exclusions = collect_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == "run-good"
    reasons = [item["reason"] for item in exclusions if item["path"].endswith("bad_request_entry.jsonl")]
    assert any("requests[0] must be an object" in r for r in reasons), reasons


def test_reasoner_evidence_wrong_type_is_excluded_and_reported_not_crashed(tmp_path):
    good = tmp_path / "good.jsonl"
    write_trace(good, run_id="run-good")
    bad = tmp_path / "bad_evidence.jsonl"
    _write_metadata(bad, run_id="run-bad-evidence", reasoner_evidence="oops-a-string")

    records, exclusions = collect_records(tmp_path)

    assert len(records) == 1
    assert records[0]["run_id"] == "run-good"
    reasons = [item["reason"] for item in exclusions if item["path"].endswith("bad_evidence.jsonl")]
    assert any("reasoner_evidence must be an object" in r for r in reasons), reasons


def test_exclusion_diagnostics_are_bounded(tmp_path):
    bad = tmp_path / "huge.jsonl"
    huge_payload = json.dumps(list(range(10_000)))
    bad.write_text(huge_payload + "\n", encoding="utf-8")

    _, exclusions = collect_records(tmp_path)

    assert len(exclusions) >= 1
    for item in exclusions:
        assert len(item["reason"]) < 1000


def test_artifacts_outside_repo_root_does_not_crash(tmp_path):
    outside = tmp_path / "external_artifacts"
    write_trace(outside / "trace.jsonl", run_id="run-outside")
    assert not str(outside).startswith(str(ROOT))

    records, exclusions = collect_records(outside)
    assert exclusions == []
    assert len(records) == 1
    assert records[0]["path"]  # relative_to(ROOT) would have raised ValueError here


def test_write_regenerates_report_without_touching_raw_traces(tmp_path, monkeypatch, capsys):
    artifacts = tmp_path / "artifacts"
    trace = artifacts / "run.jsonl"
    write_trace(trace, run_id="run-keep")
    before_bytes = trace.read_bytes()
    before_mtime = trace.stat().st_mtime

    report = tmp_path / "REPORT.md"
    report.write_text("# Header\n\n<!-- generated -->\nstale\n", encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["model_scoreboard.py", "--artifacts", str(artifacts),
                                     "--write", str(report)])
    main()

    assert trace.read_bytes() == before_bytes
    assert trace.stat().st_mtime == before_mtime
    written = report.read_text(encoding="utf-8")
    assert written.startswith("# Header")
    assert "run-keep" not in written  # raw run ids are not dumped verbatim into the report
    assert "<!-- generated -->" in written


async def test_replay_writes_run_id_and_utc_timestamps(tmp_path):
    trace = tmp_path / "trace.jsonl"
    await replay(SCENARIO, trace)
    metadata = json.loads(trace.read_text(encoding="utf-8").splitlines()[0])
    assert metadata["run_id"]
    started = dt.datetime.fromisoformat(metadata["run_started_at"])
    ended = dt.datetime.fromisoformat(metadata["run_ended_at"])
    assert started.tzinfo is not None and ended.tzinfo is not None
    assert ended >= started


async def test_two_replays_of_same_scenario_get_distinct_run_ids(tmp_path):
    trace_a = tmp_path / "a.jsonl"
    trace_b = tmp_path / "b.jsonl"
    await replay(SCENARIO, trace_a)
    await replay(SCENARIO, trace_b)
    meta_a = json.loads(trace_a.read_text(encoding="utf-8").splitlines()[0])
    meta_b = json.loads(trace_b.read_text(encoding="utf-8").splitlines()[0])
    assert meta_a["run_id"] != meta_b["run_id"]
