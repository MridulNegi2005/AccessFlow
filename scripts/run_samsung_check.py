"""One recorded public Samsung development run; no model fallback or implicit dotenv.

Run as python -m scripts.run_samsung_check. The evaluator owns scenario answer
keys; the participant receives only events delivered by the supplied harness.
"""

import argparse
import asyncio
import datetime as dt
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

from accessflow.adapters.samsung import ParticipantAgent
from accessflow.evaluation.replay import commit_revision, source_evidence
from scripts.run_local_model_checks import DiagnosticReasoner


class RecordedParticipant(ParticipantAgent):
    async def setup(self):
        await super().setup()
        if not isinstance(self.agent.reasoner, DiagnosticReasoner):
            self.agent.reasoner = DiagnosticReasoner(self.agent.reasoner)


async def execute(harness, participants, *, setup_cap=300, wall_cap=120):
    """Enforce separate warm-up and scenario budgets, including failed setup."""
    started = time.monotonic()
    phase = "setup"
    failure = None
    trace = []
    try:
        await asyncio.wait_for(harness.prepare(), setup_cap)
        if not participants or participants[-1].agent is None:
            failure = "setup_failed"
        else:
            phase = "scenario"
            trace = await asyncio.wait_for(harness.run(), wall_cap)
    except TimeoutError:
        failure = f"{phase}_timeout"
    except Exception as exc:
        failure = f"{phase}_{type(exc).__name__}"
    # Preserve partial traces on timeout/failure; never replace the attempted run
    # with an empty successful-looking result. asyncio.run owns final task cleanup.
    if not trace:
        trace = list(getattr(harness, "trace", []))
    if failure is None and any(entry.get("kind") == "agent_crash" for entry in trace):
        failure = "agent_crash"
    participant = participants[-1] if participants else None
    agent = participant.agent if participant else None
    return {
        "failure": failure, "trace": trace, "wall_s": time.monotonic() - started,
        "model_evidence": agent.reasoner.evidence() if agent else None,
        "plans": agent.reasoner.plans if agent else [],
        "adapter_diagnostics": participant.diagnostics if participant else [],
    }


def write_report(path, report):
    """Keep configured credentials out of artifacts, including exception strings."""
    encoded = json.dumps(report, indent=2, ensure_ascii=False)
    for name, value in os.environ.items():
        if value and (name.endswith("_API_KEY") or name.startswith("SECRET_")):
            encoded = encoded.replace(value, "[REDACTED]")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--scenario", required=True, help="Filename inside the kit's scenarios directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    kit = args.kit.resolve()
    candidate = Path(args.scenario)
    if candidate.name != args.scenario or candidate.suffix != ".json":
        parser.error("--scenario must be a plain JSON filename")
    scenario_path = (kit / "scenarios" / candidate).resolve()
    if not scenario_path.is_relative_to(kit / "scenarios") or not scenario_path.is_file():
        parser.error("Scenario must exist within the selected kit")
    if args.output.exists():
        parser.error("Output already exists; choose a new path to retain earlier evidence")
    if not os.getenv("ACCESSFLOW_SAMSUNG_BACKEND"):
        parser.error("Set ACCESSFLOW_SAMSUNG_BACKEND explicitly, plus the chosen provider configuration")
    os.environ["ACCESSFLOW_SAMSUNG_MEDIA_ROOT"] = str(kit)
    sys.path.insert(0, str(kit))
    runner = importlib.import_module("harness.runner")
    scorer = importlib.import_module("harness.scorer")
    for module in (runner, scorer):
        if not Path(module.__file__).resolve().is_relative_to(kit):
            raise RuntimeError("Imported harness is not from the selected kit")
    # Never pass this dictionary or its annotations/answers to the participant.
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    participants = []

    def factory(incoming, outgoing):
        instance = RecordedParticipant(incoming, outgoing)
        participants.append(instance)
        return instance

    harness = runner.EvaluationHarness(scenario, factory, time_scale=1, verbose=False)
    provenance = source_evidence(scenario_path)
    report = asyncio.run(execute(harness, participants))
    report.update({
        "mode": "live/public-development/single-run", "commit": commit_revision(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "provenance": provenance,
        "scenario": candidate.name, "time_scale": 1, "tail_ms": 6000,
        "setup_cap_s": 300, "wall_cap_s": 120,
        "kit_sha256": {str(p.relative_to(kit)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted((kit / "harness").glob("*.py"))},
        "score": scorer.score_scenario(scenario, report["trace"]) if not report["failure"] else None,
        "limitation": "One public development attempt; mock external tools, no median or hidden-set claim.",
    })
    write_report(args.output, report)
    print(json.dumps({"report": str(args.output), "failure": report["failure"],
                      "total": report["score"]["total"] if report["score"] else None,
                      "wall_s": round(report["wall_s"], 2)}))
    if report["failure"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
