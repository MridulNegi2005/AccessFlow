"""Build the model comparison table from recorded traces.

Every number comes from a run_metadata row in artifacts/. Nothing is typed by hand,
so the table cannot drift from the evidence. Regenerate after any model run:

    python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md
"""
import argparse
import datetime as dt
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runs(artifacts):
    for path in sorted(artifacts.rglob("*.jsonl")):
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if row.get("type") != "run_metadata":
                        continue
                    evidence = row.get("reasoner_evidence") or {}
                    latencies = [r["elapsed_seconds"] for r in evidence.get("requests", [])
                                 if r.get("outcome") == "success"]
                    codes = {r.get("status_code") for r in evidence.get("requests", [])
                             if r.get("status_code")}
                    yield {
                        "path": path.relative_to(ROOT).as_posix(),
                        "model": row.get("backend") or "unknown",
                        "scenario": row.get("scenario") or "unknown",
                        "status": row.get("completion_status"),
                        "oracle": (row.get("task_oracle") or {}).get("passed"),
                        "ablated": bool(row.get("disabled_components")),
                        "latencies": latencies,
                        "http_errors": sorted(codes),
                        "when": dt.datetime.fromtimestamp(path.stat().st_mtime).date().isoformat(),
                    }
                    break
        except (OSError, json.JSONDecodeError):
            continue


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
        bucket["first"] = min(bucket["first"] or record["when"], record["when"])
        bucket["last"] = max(bucket["last"] or record["when"], record["when"])
    return by_model


def table(by_model):
    lines = ["| Model | Runs | Completed | Oracle passed | Mean request | Slowest | Scenarios | HTTP errors | Last run |",
             "|---|---|---|---|---|---|---|---|---|"]
    for model, bucket in sorted(by_model.items(), key=lambda item: -item[1]["runs"]):
        mean = f"{statistics.mean(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        slowest = f"{max(bucket['latencies']):.2f} s" if bucket["latencies"] else "-"
        scored = f"{bucket['passed']}/{bucket['scored']}" if bucket["scored"] else "unscored"
        http = ", ".join(str(code) for code in sorted(bucket["http"])) or "none"
        lines.append(f"| `{model}` | {bucket['runs']} | {bucket['completed']}/{bucket['runs']} | "
                     f"{scored} | {mean} | {slowest} | {len(bucket['scenarios'])} | {http} | {bucket['last']} |")
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
            cells[(record["model"], record["scenario"])].append(record["oracle"])
    lines = ["| Scenario | " + " | ".join(f"`{m.split('/')[-1]}`" for m in models) + " |",
             "|---" * (len(models) + 1) + "|"]
    for scenario in scenarios:
        row = [scenario]
        for model in models:
            results = cells.get((model, scenario), [])
            if not results:
                row.append("-")
            else:
                passed = sum(1 for r in results if r)
                row.append(f"{passed}/{len(results)}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default=str(ROOT / "artifacts"))
    parser.add_argument("--write")
    args = parser.parse_args()
    records = list(runs(Path(args.artifacts)))
    body = (f"Generated from {len(records)} recorded runs in `artifacts/`.\n"
            f"Regenerate with `python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md`.\n\n"
            f"## Totals by model\n\n{table(summarize(records))}\n\n"
            f"## Oracle results per scenario\n\n{matrix(records)}\n")
    if args.write:
        target = Path(args.write)
        header = target.read_text(encoding="utf-8").split("<!-- generated -->")[0] if target.exists() else ""
        target.write_text(header + "<!-- generated -->\n" + body, encoding="utf-8")
        print(f"wrote {target}")
    else:
        print(body)


if __name__ == "__main__":
    main()
