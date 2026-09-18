"""Sequential, isolated scenario runs with failures retained in the denominator."""
import json
from pathlib import Path

from accessflow.evaluation.replay import metrics, replay


async def run_suite(paths, output_dir, reasoner_factory=None, backend="offline-fake", *,
                    perception_factory=None, turn_policy_factory=None, component_config=None,
                    inference_timeout=None, disabled=(), corpus_root=None):
    # Same precedence and validation as replay() (see evaluation/replay.py): an explicit
    # corpus_root wins over ACCESSFLOW_CORPUS_ROOT, and a bad root is rejected once, up
    # front, rather than letting every scenario in the loop fail separately with the
    # same error.
    if corpus_root is not None:
        corpus_root = Path(corpus_root)
        if not corpus_root.is_dir():
            raise ValueError(f"corpus_root must be an existing directory: {corpus_root}")
    paths = sorted(Path(path) for path in paths)
    if not paths:
        raise ValueError("No scenario JSON files supplied")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for index, path in enumerate(paths):
        trace = output / f"scenario-{index + 1:03d}.jsonl"
        record = {"scenario_file": path.name, "backend": backend, "disabled_components": sorted(disabled)}
        try:
            # A factory, not a shared stateful reasoner, is required across sessions.
            reasoner = reasoner_factory() if reasoner_factory is not None else None
            result = await replay(path, trace, reasoner=reasoner, backend=backend,
                                  inference_timeout=inference_timeout,
                                  perception=perception_factory() if perception_factory else None,
                                  turn_policy=turn_policy_factory() if turn_policy_factory else None,
                                  component_config=component_config, disabled=disabled,
                                  corpus_root=corpus_root)
            record.update(result)
            record["metrics"] = metrics(trace)
            if result["completion_status"] != "completed":
                record["status"] = "failed"
            else:
                record["status"] = "passed" if result["task_oracle"]["passed"] is True else (
                    "failed" if result["task_oracle"]["passed"] is False else "unscored")
        except Exception as exc:
            # Include malformed scenarios and setup failures, without persisting provider
            # headers or potentially credential-bearing exception representations.
            record.update(status="error", error_type=type(exc).__name__)
        records.append(record)
    counts = {key: sum(record["status"] == key for record in records)
              for key in ("passed", "failed", "unscored", "error")}
    fully_scored = counts["unscored"] == 0
    report = {"report_version": "development-suite.v1", "backend": backend, "scenario_count": len(records),
              "counts": counts,
              "oracle_pass_rate_all_cases": counts["passed"] / len(records) if fully_scored else None,
              "cases": records,
              "limitation": "Developer-authored scenario criteria and mock effects; not official-kit or held-out results."}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
