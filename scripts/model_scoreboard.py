"""Build the model comparison table from recorded traces.

Every number comes from a run_metadata row in artifacts/. Nothing is typed by hand,
so the table cannot drift from the evidence. Regenerate after any model run:

    python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md

Ordering and deduplication rely on `run_id`/`run_started_at`/`run_ended_at`, written
by replay.py from this point forward. Traces recorded before those fields existed
fall back to file mtime; that fallback is disclosed inline wherever it is used,
never presented as an authoritative timestamp.
"""
import argparse
import datetime as dt
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG_LIMIT = 200


def display_path(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _truncate(value):
    """Bound a diagnostic snippet so exclusion reasons cannot embed unbounded content."""
    text = repr(value)
    if len(text) <= DIAG_LIMIT:
        return text
    return text[:DIAG_LIMIT] + "...(truncated)"


def _record_shape_error(row):
    """Return a reason string if a run_metadata row's nested fields have the wrong
    type, else None. Missing fields are not an error here; only present-but-wrong-type
    fields are, since absence already has defined defaults elsewhere.
    """
    evidence = row.get("reasoner_evidence")
    if evidence is not None and not isinstance(evidence, dict):
        return f"reasoner_evidence must be an object, got {type(evidence).__name__}: {_truncate(evidence)}"
    if isinstance(evidence, dict):
        requests = evidence.get("requests")
        if requests is not None and not isinstance(requests, list):
            return (f"reasoner_evidence.requests must be a list, got "
                    f"{type(requests).__name__}: {_truncate(requests)}")
        if isinstance(requests, list):
            for index, entry in enumerate(requests):
                if not isinstance(entry, dict):
                    return (f"reasoner_evidence.requests[{index}] must be an object, got "
                            f"{type(entry).__name__}: {_truncate(entry)}")
    oracle = row.get("task_oracle")
    if oracle is not None and not isinstance(oracle, dict):
        return f"task_oracle must be an object, got {type(oracle).__name__}: {_truncate(oracle)}"
    for key in ("run_ended_at", "run_started_at"):
        value = row.get(key)
        if value is not None and not isinstance(value, str):
            return f"{key} must be a string, got {type(value).__name__}: {_truncate(value)}"
    return None


def run_time(row, path):
    """Return (sort_epoch, source, display_string) for a run_metadata row.

    Prefers the recorded end/start timestamp. Falls back to file mtime only when
    no recorded timestamp exists, and always labels that fallback in the display
    string so it is never mistaken for verified chronology. A timestamp of the
    wrong type (not a string) is treated as absent rather than raising.
    """
    for key in ("run_ended_at", "run_started_at"):
        value = row.get(key)
        if not value or not isinstance(value, str):
            continue
        try:
            parsed = dt.datetime.fromisoformat(value)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        parsed = parsed.astimezone(dt.timezone.utc)
        return parsed.timestamp(), "recorded", parsed.isoformat(timespec="seconds")
    mtime = path.stat().st_mtime
    inferred = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc)
    return mtime, "mtime_inferred", inferred.isoformat(timespec="seconds") + " (mtime, order unverified)"


def collect_records(artifacts):
    """Scan `artifacts` for run_metadata rows.

    Returns (records, exclusions). Nothing is silently dropped: every skipped file
    or duplicate run lands in `exclusions` with a reason.
    """
    records, exclusions = [], []
    if not artifacts.exists():
        exclusions.append({"path": display_path(artifacts), "reason": "artifacts_directory_missing"})
        return records, exclusions
    seen_run_ids = {}
    for path in sorted(artifacts.rglob("*.jsonl")):
        rel = display_path(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            exclusions.append({"path": rel, "reason": f"read_error: {exc}"})
            continue
        row = None
        for line in lines:
            if not line.strip():
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError as exc:
                exclusions.append({"path": rel, "reason": f"malformed_json: {exc}"})
                continue
            if not isinstance(candidate, dict):
                exclusions.append({"path": rel,
                                    "reason": f"invalid_record_type: expected a JSON object, got "
                                              f"{type(candidate).__name__}: {_truncate(candidate)}"})
                continue
            if candidate.get("type") == "run_metadata":
                row = candidate
                break
        if row is None:
            exclusions.append({"path": rel, "reason": "no_run_metadata_row"})
            continue
        shape_error = _record_shape_error(row)
        if shape_error is not None:
            exclusions.append({"path": rel, "reason": f"invalid_record_shape: {shape_error}"})
            continue
        run_id = row.get("run_id")
        if run_id is not None:
            if run_id in seen_run_ids:
                exclusions.append({"path": rel,
                                    "reason": f"duplicate_run_id: {run_id} (first seen at {seen_run_ids[run_id]})"})
                continue
            seen_run_ids[run_id] = rel
        time_epoch, time_source, when = run_time(row, path)
        evidence = row.get("reasoner_evidence") or {}
        latencies = [r["elapsed_seconds"] for r in evidence.get("requests", [])
                     if r.get("outcome") == "success"]
        codes = {r.get("status_code") for r in evidence.get("requests", []) if r.get("status_code")}
        records.append({
            "path": rel,
            "run_id": run_id,
            "model": row.get("backend") or "unknown",
            "scenario": row.get("scenario") or "unknown",
            "status": row.get("completion_status"),
            "oracle": (row.get("task_oracle") or {}).get("passed"),
            "ablated": bool(row.get("disabled_components")),
            "latencies": latencies,
            "http_errors": sorted(codes),
            "time_epoch": time_epoch,
            "time_source": time_source,
            "when": when,
        })
    return records, exclusions


def summarize(records):
    by_model = defaultdict(lambda: {"runs": 0, "completed": 0, "passed": 0, "scored": 0,
                                    "latencies": [], "scenarios": set(), "http": set(),
                                    "first": None, "last": None})
    for record in records:
        if record["ablated"]:
            continue
        bucket = by_model[record["model"]]
        bucket["runs"] += 1
        bucket["completed"] += record["status"] == "completed"
        if record["oracle"] is not None:
            bucket["scored"] += 1
            bucket["passed"] += bool(record["oracle"])
        bucket["latencies"] += record["latencies"]
        bucket["scenarios"].add(record["scenario"])
        bucket["http"].update(record["http_errors"])
        if bucket["first"] is None or record["time_epoch"] < bucket["first"][0]:
            bucket["first"] = (record["time_epoch"], record["when"])
        if bucket["last"] is None or record["time_epoch"] > bucket["last"][0]:
            bucket["last"] = (record["time_epoch"], record["when"])
    return by_model


def table(by_model):
    lines = ["| Model | Runs | Completed | Oracle passed | Unscored | Mean request (successful) | "
             "Slowest (successful) | Scenarios | HTTP errors | Last run |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for model, bucket in sorted(by_model.items(), key=lambda item: -item[1]["runs"]):
        mean = f"{statistics.mean(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        slowest = f"{max(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        scored = f"{bucket['passed']}/{bucket['scored']}" if bucket["scored"] else "unscored"
        unscored = bucket["runs"] - bucket["scored"]
        http = ", ".join(str(code) for code in sorted(bucket["http"])) or "none"
        last = bucket["last"][1] if bucket["last"] else "-"
        lines.append(f"| `{model}` | {bucket['runs']} | {bucket['completed']}/{bucket['runs']} | "
                     f"{scored} | {unscored} | {mean} | {slowest} | {len(bucket['scenarios'])} | "
                     f"{http} | {last} |")
    return "\n".join(lines)


def matrix(records, minimum=4):
    # Ablated runs are excluded. They carry a deliberate ablation marker that the oracle
    # counts as an unexpected error, so scoring them beside control runs is not a like
    # comparison. The ablation has its own document.
    records = [record for record in records if not record["ablated"]]
    counts = defaultdict(int)
    for record in records:
        counts[record["model"]] += 1
    models = sorted([m for m, n in counts.items() if n >= minimum])
    scenarios = sorted({r["scenario"] for r in records if counts[r["model"]] >= minimum})
    cells = defaultdict(list)
    for record in records:
        if counts[record["model"]] >= minimum:
            cells[(record["model"], record["scenario"])].append(record)
    lines = ["| Scenario | " + " | ".join(f"`{m.split('/')[-1]}`" for m in models) + " |",
             "|---" * (len(models) + 1) + "|"]
    for scenario in scenarios:
        row = [scenario]
        for model in models:
            entries = cells.get((model, scenario), [])
            scored = [e for e in entries if e["oracle"] is not None]
            unscored = len(entries) - len(scored)
            if not entries:
                row.append("-")
            elif not scored:
                row.append(f"unscored ({unscored})")
            else:
                passed = sum(1 for e in scored if e["oracle"])
                cell = f"{passed}/{len(scored)}"
                if unscored:
                    cell += f" (+{unscored} unscored)"
                row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def per_model(records):
    """One section per model, one row per scenario it has run.

    The latest column matters more than the totals. Scores span several days, and
    controller changes moved results independently of the model, so an old failure
    still counts against a model that was never retested. "Latest" is selected by
    recorded run timestamp; where no run recorded a timestamp, the file's mtime is
    used and the row says so explicitly.
    """
    grouped = defaultdict(lambda: defaultdict(list))
    for record in records:
        if not record["ablated"]:
            grouped[record["model"]][record["scenario"]].append(record)
    sections = []
    for model in sorted(grouped, key=lambda m: -sum(len(v) for v in grouped[m].values())):
        rows = ["| Scenario | Runs | Passed | Completed | Mean request (successful) | "
                "Slowest (successful) | Latest | Last run |",
                "|---|---|---|---|---|---|---|---|"]
        for scenario in sorted(grouped[model]):
            entries = sorted(grouped[model][scenario], key=lambda r: r["time_epoch"])
            latencies = [value for entry in entries for value in entry["latencies"]]
            scored = [entry for entry in entries if entry["oracle"] is not None]
            passed = sum(1 for entry in scored if entry["oracle"])
            done = sum(1 for entry in entries if entry["status"] == "completed")
            latest = entries[-1]
            verdict = {True: "pass", False: "fail", None: "unscored"}[latest["oracle"]]
            if latest["status"] != "completed":
                verdict = f"{verdict} ({latest['status']})"
            mean = f"{statistics.mean(latencies):.2f} s" if latencies else "-"
            slowest = f"{max(latencies):.2f} s" if latencies else "-"
            rows.append(f"| {scenario} | {len(entries)} | {passed}/{len(scored)} | "
                        f"{done}/{len(entries)} | {mean} | {slowest} | {verdict} | {latest['when']} |")
        sections.append(f"### `{model}`\n\n" + "\n".join(rows))
    return "\n\n".join(sections)


def exclusions_section(exclusions):
    if not exclusions:
        return "No files were excluded."
    lines = [f"- `{item['path']}`: {item['reason']}" for item in exclusions]
    return f"{len(exclusions)} file(s) excluded from this table:\n\n" + "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default=str(ROOT / "artifacts"))
    parser.add_argument("--write")
    args = parser.parse_args()
    records, exclusions = collect_records(Path(args.artifacts))
    inferred = sum(1 for r in records if r["time_source"] != "recorded")
    notes = (
        f"Generated from {len(records)} recorded runs in `artifacts/`.\n"
        f"Regenerate with `python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md`.\n\n"
        f"`Oracle passed` and per-scenario pass counts divide by scored runs only (null/unscored "
        f"oracles excluded from that denominator, counted separately as `Unscored`). `Completed` "
        f"divides by every attempted run regardless of scoring, so infrastructure failures do not "
        f"disappear from the record.\n\n"
        f"`Mean request`/`Slowest` cover only requests marked successful. They are not end-to-end "
        f"scenario latency and do not include timed-out or failed requests.\n\n"
        f"{inferred} of {len(records)} run(s) have no recorded run timestamp and fall back to file "
        f"mtime for ordering; those are marked `(mtime, order unverified)` wherever shown.\n\n"
        f"## Excluded evidence\n\n{exclusions_section(exclusions)}\n\n"
    )
    body = (f"{notes}"
            f"## Totals by model\n\n{table(summarize(records))}\n\n"
            f"## Oracle results per scenario\n\n{matrix(records)}\n\n"
            f"## Every model, every scenario\n\n{per_model(records)}\n")
    if args.write:
        target = Path(args.write)
        header = target.read_text(encoding="utf-8").split("<!-- generated -->")[0] if target.exists() else ""
        target.write_text(header + "<!-- generated -->\n" + body, encoding="utf-8")
        print(f"wrote {target}")
    else:
        print(body)


if __name__ == "__main__":
    main()
