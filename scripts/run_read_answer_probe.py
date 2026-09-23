"""Live developer-authored grounding probes, not Samsung or end-to-end scores.

Credentials/configuration must be supplied explicitly through the backend's normal
environment. This script never loads dotenv, executes tools or changes providers.
"""

import argparse
import asyncio
import datetime as dt
import hashlib
import time
from pathlib import Path

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.contracts import Observation, SessionView, Snapshot, ToolCall, ToolManifest, ToolResult
from accessflow.evaluation.replay import commit_revision, source_evidence
from accessflow.read_answer import render_answer
from scripts.run_samsung_check import write_report


PROBES = [
    {"name": "explicit_rate", "question": "What did the rate lookup return, including its billing basis?",
     "result": {"name": "Example rental", "amount_usd": 189, "billing_period": "per night"},
     "expected": ['Name: "Example rental"', 'Amount usd: 189', 'Billing period: "per night"']},
    {"name": "inventory_units", "question": "Tell me the item's mass, stock availability and handling fee.",
     "result": {"item": "Example sensor", "mass_kg": 2.5, "in_stock": False, "handling_fee_usd": 0},
     "expected": ['Mass kg: 2.5', 'In stock: false', 'Handling fee usd: 0']},
]


async def run(backend, profile):
    reasoner = ModelReasoner(backend, prompt_profile=profile, read_answer_mode="evidence")
    records = []
    for probe in PROBES:
        # Each probe has separate synthetic session state. The model sees no labels
        # or expected strings; they are local output checks after generation.
        view = SessionView(
            session_id=probe["name"], active_request_id="current", state=Snapshot(),
            observations=[Observation(event_id="e", source_id="u", modality="text", backend="synthetic-text",
                                      text=probe["question"], final=True)],
            results=[ToolResult(call_id="read-1", status="success", result=probe["result"])],
            calls=[ToolCall(call_id="read-1", operation_id="op-1", tool="catalog_lookup", arguments={},
                            effect="read", status="success", request_id="current", dependencies={})])
        tool = ToolManifest(name="catalog_lookup", description="Look up a catalog entry.", effect="read",
                            parameters={"type": "object", "properties": {}})
        record = {"probe": probe["name"], "input": view.model_dump(mode="json"), "passed": False}
        started = time.monotonic()
        try:
            plan = await asyncio.wait_for(reasoner.plan(view, [tool]), 30)
            record["proposal"] = plan.model_dump(mode="json")
            if plan.evidence_answer is None:
                record["failure"] = "no_evidence_answer"
            else:
                text, sources = render_answer(plan.evidence_answer, view)
                record.update(text=text, sources=sources,
                              checks={s: s in text for s in probe["expected"]})
                record["passed"] = all(record["checks"].values())
        except Exception as exc:
            record["failure"] = type(exc).__name__
        record["wall_s"] = time.monotonic() - started
        records.append(record)
    return {"probes": records, "model_evidence": reasoner.evidence(),
            "passed": all(record["passed"] for record in records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, choices=["groq", "ollama", "gemini"])
    parser.add_argument("--profile", default="compact-v2", choices=["full", "compact-v1", "compact-v2"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a fresh evidence path")
    provenance = source_evidence(__file__)
    report = asyncio.run(run(JsonBackend(args.backend), args.profile))
    report.update(mode="live/synthetic-read-answer/single-attempt", commit=commit_revision(),
                  created_at=dt.datetime.now(dt.timezone.utc).isoformat(), provenance=provenance,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limitation="Two exposed developer-authored read-only probes. Not end-to-end, held-out, "
                             "Samsung evaluation or universal factual/semantic verification.")
    write_report(args.output, report)
    print(f"Recorded {len(report['probes'])} probes; passed={report['passed']}; {args.output}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
