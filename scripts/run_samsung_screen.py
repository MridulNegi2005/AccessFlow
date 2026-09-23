"""Sequential public development screen; never an official aggregate or hidden score.

Environment credentials/backend/model must already be configured. Each child uses
the existing recorded runner with unchanged scenario timing. Failures are retained,
never silently retried or replaced. The directory must not exist before the run.
"""

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from accessflow.evaluation.replay import commit_revision, source_evidence
from accessflow.adapters.models import DEFAULT_MODELS
from scripts.run_samsung_check import resolve_scenario, write_report


def summarize(report):
    required = {"failure", "score", "model_evidence", "trace", "provenance"}
    if not isinstance(report, dict) or not required <= report.keys():
        raise ValueError("Incomplete runner report")
    if (not isinstance(report["trace"], list)
            or not all(isinstance(e, dict) and isinstance(e.get("payload", {}), dict) for e in report["trace"])
            or not isinstance(report["provenance"], dict)
            or not isinstance(report["provenance"].get("source_sha256"), str)
            or (report["model_evidence"] is not None and not isinstance(report["model_evidence"], dict))
            or (report["score"] is not None and not isinstance(report["score"], dict))):
        raise ValueError("Invalid runner report shape")
    total = (report["score"] or {}).get("total")
    if (report["failure"] is not None and not isinstance(report["failure"], str)
            or (total is None and report["failure"] is None)
            or (total is not None and (type(total) not in {int, float}
                                      or not math.isfinite(total) or not 0 <= total <= 100))):
        raise ValueError("Invalid runner result")
    requests = (report.get("model_evidence") or {}).get("requests", [])
    if (not isinstance(requests, list) or not all(isinstance(r, dict) for r in requests)
            or any(r.get("prompt_tokens") is not None and
                   (type(r["prompt_tokens"]) is not int or r["prompt_tokens"] < 0) for r in requests)):
        raise ValueError("Invalid provider usage")
    trace = report.get("trace", [])
    ends = [e["t_ms"] for e in trace if isinstance(e.get("t_ms"), (int, float)) and e.get("kind") == "event"
            and (e.get("event_type") == "interruption" or
                 (e.get("event_type") == "user_speech_chunk" and e.get("payload", {}).get("end_of_turn") is True))]
    last_text_turn = max(ends) if ends else None
    replies = [e["t_ms"] for e in trace if isinstance(e.get("t_ms"), (int, float))
               and e.get("kind") == "action" and e.get("action") in {"final_response", "clarification_request"}
               and last_text_turn is not None and e["t_ms"] >= last_text_turn]
    return {
        "failure": report.get("failure"),
        "scorer_total": (report.get("score") or {}).get("total"),
        "provider_outcomes": [r.get("outcome") for r in requests],
        "reported_input_tokens": sum(r.get("prompt_tokens") or 0 for r in requests),
        "usage_missing_count": sum(r.get("prompt_tokens") is None for r in requests),
        "last_text_turn_to_response_ms": min(replies) - last_text_turn if replies else None,
        "finals": [{"t_ms": e.get("t_ms"), "text": e.get("payload", {}).get("text")}
                   for e in trace if e.get("kind") == "action" and e.get("action") == "final_response"],
        "tool_calls": [{"tool": e.get("api_name"), "call_id": e.get("call_id"), "args": e.get("args")}
                       for e in trace if e.get("kind") == "action" and e.get("action") == "tool_call"],
        "clarifications": [e.get("payload", {}).get("text") for e in trace
                           if e.get("kind") == "action" and e.get("action") == "clarification_request"],
        # Samsung records these directly instead of logging a cancel_tool action.
        "cancellations": [{"kind": e["kind"], "t_ms": e.get("t_ms"), "call_id": e.get("call_id")}
                          for e in trace if e.get("kind") in {"tool_cancelled", "cancel_noop"}],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cooldown", type=float, default=70)
    parser.add_argument("--tool-documentation", default="docs/TOOLS.md")
    args = parser.parse_args()
    backend = os.getenv("ACCESSFLOW_SAMSUNG_BACKEND")
    model_variable = DEFAULT_MODELS.get(backend, (None, None))[0]
    model = os.getenv(model_variable, "").strip() if model_variable else ""
    if not model:
        parser.error("Set ACCESSFLOW_SAMSUNG_BACKEND and explicit provider/model configuration before screening")
    if not math.isfinite(args.cooldown) or not 0 <= args.cooldown <= 300:
        parser.error("Cooldown must be between 0 and 300 seconds")
    if len(set(args.scenarios)) != len(args.scenarios):
        parser.error("Screen each scenario once; use a new directory for a separate repetition")
    kit = args.kit.resolve()
    try:
        paths = [resolve_scenario(kit, name=name)[0] for name in args.scenarios]
    except ValueError as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=False)
    provenance = source_evidence(__file__)
    plan = {"mode": "live/public-development/screen", "commit": commit_revision(),
            "requested_backend": backend, "requested_model": model,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "provenance": provenance,
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "scenarios": [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
            "cooldown_s": args.cooldown, "attempts": [], "state": "running",
            "limitation": "One attempt per exposed public scenario; no aggregate, median or hidden-set claim. "
                          "Cooldown is outside each scenario, not a guarantee against provider quotas."}
    write_report(args.output / "plan.json", plan)
    for index, path in enumerate(paths):
        if index:
            print(f"Cooldown before {path.name}", flush=True)
            until = time.monotonic() + args.cooldown
            while time.monotonic() < until:
                time.sleep(min(30, max(0, until - time.monotonic())))
        if source_evidence(__file__)["source_sha256"] != provenance["source_sha256"]:
            plan["state"] = "source_changed"
            break
        output = args.output / path.name
        command = [sys.executable, "-m", "scripts.run_samsung_check", "--kit", str(kit),
                   "--scenario", path.name, "--output", str(output),
                   "--tool-documentation", args.tool_documentation]
        attempt = {"scenario": path.name, "runner_exit": None}
        try:
            result = subprocess.run(command, capture_output=True, timeout=450)
            attempt["runner_exit"] = result.returncode
        except subprocess.TimeoutExpired:
            attempt["runner_failure"] = "child_timeout"
        except OSError:
            attempt["runner_failure"] = "child_launch_failed"
        consistent = source_evidence(__file__)["source_sha256"] == provenance["source_sha256"]
        if output.exists():
            try:
                report = json.loads(output.read_text(encoding="utf-8"))
                attempt.update(summarize(report))
                attempt["report_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
                consistent = consistent and report["provenance"]["source_sha256"] == provenance["source_sha256"]
            except (ValueError, KeyError, TypeError):
                attempt["runner_failure"] = "invalid_report"
        else:
            attempt.setdefault("runner_failure", "missing_report")
        attempt["source_consistent"] = consistent
        plan["attempts"].append(attempt)
        write_report(args.output / f"attempt-{index + 1:02d}.json", attempt)
        print(json.dumps({k: attempt.get(k) for k in ("scenario", "runner_exit", "failure", "scorer_total",
                                                    "runner_failure")}), flush=True)
        if not consistent:
            plan["state"] = "source_changed"
            break
    else:
        plan["state"] = "finished"
    write_report(args.output / "summary.json", plan)
    if plan["state"] != "finished" or any(a.get("runner_exit") != 0 or a.get("runner_failure")
                                           for a in plan["attempts"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
