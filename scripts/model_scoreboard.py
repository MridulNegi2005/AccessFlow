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
import hashlib
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# `python scripts/model_scoreboard.py` (the invocation this module's own docstring and
# docs/evidence/*/README.md tell people to run) puts this file's own directory on
# sys.path, not the repo root, so `import scripts.evidence_bundle` fails unless the
# root is added first. `python -m scripts.model_scoreboard` and pytest (pythonpath=["."]
# in pyproject.toml) already have the root on sys.path; this is a no-op there.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_bundle import (INFRA_ADMISSION_FAILURE, LABEL_MEANINGS,  # noqa: E402
                                     QUALITY_EXCLUDED_LABELS, SCORED_FAIL_GENERATED_OUTPUT,
                                     SCORED_FAIL_OUTPUT_MISMATCH, SCORED_PASS,
                                     TIMEOUT_UNDETERMINED_CAUSE, UNDETERMINED_FAILURE, UNSCORED,
                                     classify_eligibility, load_frozen_times)

DIAG_LIMIT = 200

VERDICT_TEXT = {
    SCORED_PASS: "pass",
    SCORED_FAIL_OUTPUT_MISMATCH: "fail",
    SCORED_FAIL_GENERATED_OUTPUT: "fail (generated output rejected by provider)",
    TIMEOUT_UNDETERMINED_CAUSE: "fail (timeout, undetermined cause)",
    UNDETERMINED_FAILURE: "fail (undetermined cause)",
    INFRA_ADMISSION_FAILURE: "excluded (infra admission failure)",
    UNSCORED: "unscored",
}


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


def _parse_iso(value):
    if not value or not isinstance(value, str):
        return None
    text = value.split(" (", 1)[0]  # strip a trailing "(...)" annotation, if any
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def run_time(row, path, frozen_time=None):
    """Return (sort_epoch, source, display_string) for a run_metadata row.

    Ordering policy, in order:

    1. A recorded `run_ended_at`/`run_started_at` on the row itself. This is the
       only source treated as verified chronology.
    2. `frozen_time`, an ISO timestamp carried by a manifest.json sibling to the
       bundle this file lives in (see `evidence_bundle.load_frozen_times`). A
       committed trace file's own mtime is reset to checkout time by `git clone`/
       `git checkout`, so it cannot be trusted for a file that lives in git; the
       manifest freezes what the mtime was at bundle-build time instead, and that
       frozen value survives a checkout untouched. Still not a verified run
       chronology, so it is labelled the same way mtime is.
    3. The file's own current mtime, used only when neither of the above exists
       (e.g. scanning a local, non-bundled `artifacts/` directory directly).

    Ties in sort_epoch are broken by the caller sorting on (time_epoch, path); path
    order comes from `sorted(artifacts.rglob(...))`, so tied entries keep a stable,
    deterministic order rather than depending on filesystem iteration order.

    A timestamp of the wrong type (not a string) is treated as absent rather than
    raising.
    """
    for key in ("run_ended_at", "run_started_at"):
        parsed = _parse_iso(row.get(key))
        if parsed is not None:
            return parsed.timestamp(), "recorded", parsed.isoformat(timespec="seconds")
    frozen = _parse_iso(frozen_time)
    if frozen is not None:
        return (frozen.timestamp(), "manifest_frozen_mtime",
                frozen.isoformat(timespec="seconds") + " (bundle-frozen mtime, order unverified)")
    mtime = path.stat().st_mtime
    inferred = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc)
    return mtime, "mtime_inferred", inferred.isoformat(timespec="seconds") + " (mtime, order unverified)"


def collect_records(artifacts):
    """Scan `artifacts` for run_metadata rows.

    Returns (records, exclusions). Nothing is silently dropped: every skipped file
    or duplicate run lands in `exclusions` with a reason.

    Each record's `eligibility`/`eligibility_basis` come from
    `evidence_bundle.classify_eligibility`, computed fresh from that row's own
    content -- never read from a manifest. A sibling `manifest.json` (one directory
    up from `artifacts`, the layout `docs/evidence/*/traces` uses) is consulted only
    for `run_time`'s mtime fallback, joined by content hash, never by filename.
    """
    records, exclusions = [], []
    if not artifacts.exists():
        exclusions.append({"path": display_path(artifacts), "reason": "artifacts_directory_missing"})
        return records, exclusions
    frozen_times = load_frozen_times(artifacts.parent)
    seen_run_ids = {}
    for path in sorted(artifacts.rglob("*.jsonl")):
        rel = display_path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            exclusions.append({"path": rel, "reason": f"read_error: {exc}"})
            continue
        lines = text.splitlines()
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
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
        time_epoch, time_source, when = run_time(row, path, frozen_times.get(content_hash))
        evidence = row.get("reasoner_evidence") or {}
        latencies = [r["elapsed_seconds"] for r in evidence.get("requests", [])
                     if r.get("outcome") == "success"]
        codes = {r.get("status_code") for r in evidence.get("requests", []) if r.get("status_code")}
        eligibility, eligibility_basis = classify_eligibility(row)
        records.append({
            "path": rel,
            "content_sha256": content_hash,
            "run_id": run_id,
            "model": row.get("backend") or "unknown",
            "scenario": row.get("scenario") or "unknown",
            "status": row.get("completion_status"),
            "oracle": (row.get("task_oracle") or {}).get("passed"),
            "eligibility": eligibility,
            "eligibility_basis": eligibility_basis,
            "ablated": bool(row.get("disabled_components")),
            "latencies": latencies,
            "http_errors": sorted(codes),
            "time_epoch": time_epoch,
            "time_source": time_source,
            "when": when,
        })
    return records, exclusions


def is_quality_scored(record):
    """True if this run belongs in the model-output quality denominator.

    A run leaves this denominator only on positive evidence it never reached the
    model (`INFRA_ADMISSION_FAILURE`) or never received a verdict at all
    (`UNSCORED`, oracle is None). Every other outcome, including an undetermined
    failure, stays in -- see `evidence_bundle.QUALITY_EXCLUDED_LABELS`.
    """
    return record["oracle"] is not None and record["eligibility"] not in QUALITY_EXCLUDED_LABELS


def summarize(records):
    by_model = defaultdict(lambda: {"runs": 0, "completed": 0, "passed": 0, "scored": 0,
                                    "infra_excluded": 0, "eligibility_counts": defaultdict(int),
                                    "latencies": [], "scenarios": set(), "http": set(),
                                    "first": None, "last": None})
    for record in records:
        if record["ablated"]:
            continue
        bucket = by_model[record["model"]]
        bucket["runs"] += 1
        bucket["completed"] += record["status"] == "completed"
        bucket["eligibility_counts"][record["eligibility"]] += 1
        if record["eligibility"] == "infra_admission_failure":
            bucket["infra_excluded"] += 1
        if is_quality_scored(record):
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
    lines = ["| Model | Runs | Completed | Oracle passed (quality) | Excluded (infra) | Unscored | "
             "Mean request (successful) | Slowest (successful) | Scenarios | HTTP errors | Last run |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for model, bucket in sorted(by_model.items(), key=lambda item: -item[1]["runs"]):
        mean = f"{statistics.mean(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        slowest = f"{max(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        scored = f"{bucket['passed']}/{bucket['scored']}" if bucket["scored"] else "unscored"
        unscored = bucket["runs"] - bucket["scored"] - bucket["infra_excluded"]
        http = ", ".join(str(code) for code in sorted(bucket["http"])) or "none"
        last = bucket["last"][1] if bucket["last"] else "-"
        lines.append(f"| `{model}` | {bucket['runs']} | {bucket['completed']}/{bucket['runs']} | "
                     f"{scored} | {bucket['infra_excluded']} | {unscored} | {mean} | {slowest} | "
                     f"{len(bucket['scenarios'])} | {http} | {last} |")
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
            scored = [e for e in entries if is_quality_scored(e)]
            unscored = [e for e in entries if e["oracle"] is None]
            infra_excluded = [e for e in entries if e["oracle"] is not None and not is_quality_scored(e)]
            if not entries:
                row.append("-")
            elif not scored:
                parts = []
                if unscored:
                    parts.append(f"unscored ({len(unscored)})")
                if infra_excluded:
                    parts.append(f"excluded ({len(infra_excluded)})")
                row.append(", ".join(parts))
            else:
                passed = sum(1 for e in scored if e["oracle"])
                cell = f"{passed}/{len(scored)}"
                extra = []
                if unscored:
                    extra.append(f"+{len(unscored)} unscored")
                if infra_excluded:
                    extra.append(f"+{len(infra_excluded)} excluded")
                if extra:
                    cell += f" ({', '.join(extra)})"
                row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def per_model(records):
    """One section per model, one row per scenario it has run.

    The latest column matters more than the totals. Scores span several days, and
    controller changes moved results independently of the model, so an old failure
    still counts against a model that was never retested. "Latest" is selected by
    recorded run timestamp; where no run recorded a timestamp, a bundle-frozen or
    live file mtime is used instead (see `run_time`), and the row is tagged
    `[order unverified]` rather than asserting a chronology the evidence does not
    support. The verdict text itself comes from the run's eligibility label
    (`VERDICT_TEXT`), not a raw pass/fail flag, so an infra-blocked run reads as
    "excluded", not "fail".
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
            entries = sorted(grouped[model][scenario], key=lambda r: (r["time_epoch"], r["path"]))
            latencies = [value for entry in entries for value in entry["latencies"]]
            scored = [entry for entry in entries if is_quality_scored(entry)]
            passed = sum(1 for entry in scored if entry["oracle"])
            done = sum(1 for entry in entries if entry["status"] == "completed")
            latest = entries[-1]
            verdict = VERDICT_TEXT.get(latest["eligibility"], latest["eligibility"] or "unscored")
            if latest["time_source"] != "recorded":
                verdict = f"{verdict} [order unverified]"
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


def eligibility_section(records):
    """Global (all-model) eligibility breakdown, so the two denominators used
    throughout this report -- attempted-run reliability and model-output quality
    -- are always visible and reconcile against each other by construction.
    """
    counts = defaultdict(int)
    for record in records:
        if record["ablated"]:
            continue
        counts[record["eligibility"]] += 1
    attempted = sum(counts.values())
    quality_excluded = sum(n for label, n in counts.items() if label in QUALITY_EXCLUDED_LABELS)
    quality_total = attempted - quality_excluded
    quality_passed = counts.get(SCORED_PASS, 0)
    lines = [
        f"{attempted} non-ablated run(s) attempted. Every one is counted in "
        f"**attempted-run reliability** below, whatever its outcome.",
        f"{quality_total} of those {attempted} count toward **model-output quality** "
        f"({quality_passed}/{quality_total} passed); {quality_excluded} are excluded because the "
        f"evidence shows the request was blocked before the model could respond, or no verdict "
        f"was ever recorded.",
        "",
        "| Label | Count | In quality denominator | Meaning |",
        "|---|---|---|---|",
    ]
    for label in sorted(counts):
        in_quality = "no" if label in QUALITY_EXCLUDED_LABELS else "yes"
        meaning = LABEL_MEANINGS.get(label, "")
        lines.append(f"| `{label}` | {counts[label]} | {in_quality} | {meaning} |")
    assert sum(counts.values()) == attempted  # every attempted run has exactly one label
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default=str(ROOT / "artifacts"))
    parser.add_argument("--write")
    args = parser.parse_args()
    records, exclusions = collect_records(Path(args.artifacts))
    inferred = sum(1 for r in records if r["time_source"] != "recorded")
    notes = (
        f"Generated from {len(records)} recorded runs in `{args.artifacts}`.\n"
        f"Regenerate with `python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md`.\n\n"
        f"Two denominators are reported and must not be confused. **Attempted-run reliability** "
        f"(`Runs`, `Completed`) counts every dispatched run regardless of outcome. **Model-output "
        f"quality** (`Oracle passed (quality)`) counts only runs the evidence does not clear the "
        f"model of: a confirmed pre-generation infrastructure block (`Excluded (infra)`) is left "
        f"out, everything else -- including undetermined failures and timeouts -- stays in as a "
        f"failure. Runs with no oracle verdict at all are `Unscored`, excluded from quality for a "
        f"different reason (no verdict exists to count). See `## Eligibility classification` for "
        f"the per-label rule.\n\n"
        f"`Mean request`/`Slowest` cover only requests marked successful. They are not end-to-end "
        f"scenario latency and do not include timed-out or failed requests.\n\n"
        f"{inferred} of {len(records)} run(s) have no recorded run timestamp and fall back to a "
        f"bundle-frozen or live file mtime for ordering; those are marked `(..., order unverified)` "
        f"wherever shown, and a `Latest` verdict built from one is tagged `[order unverified]`.\n\n"
        f"## Excluded evidence\n\n{exclusions_section(exclusions)}\n\n"
    )
    body = (f"{notes}"
            f"## Eligibility classification\n\n{eligibility_section(records)}\n\n"
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
