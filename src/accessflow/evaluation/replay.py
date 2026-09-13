import asyncio
import json
import platform
import subprocess
import time
from pathlib import Path

from accessflow.contracts import EndEvent, PlanProposal
from accessflow.adapters.internal import parse_event
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner


async def replay(path, output, reasoner=None, backend="offline-fake"):
    scenario = json.loads(Path(path).read_text(encoding="utf-8"))
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    tools = FakeTools()
    agent = Agent(FakePerception(), FinalFlagPolicy(), reasoner or ScriptedReasoner(
                  [PlanProposal.model_validate(p) for p in scenario["proposals"]]), tools, MockOnlyAuthorization())
    runner = asyncio.create_task(agent.run(incoming, outgoing))
    events = []
    started = time.monotonic()

    async def collect():
        while True:
            event = await outgoing.get()
            events.append(event.model_dump(mode="json"))
            if event.kind == "final" or event.payload.get("code") == "backend_failure":
                return

    collector = asyncio.create_task(collect())
    try:
        for entry in scenario["events"]:
            await incoming.put(parse_event(entry))
            # Explicit test pacing, not an inferred speech/end-of-turn measurement.
            await asyncio.sleep(scenario.get("event_spacing_s", 0.01))
        await asyncio.wait_for(collector, 30)
    finally:
        await incoming.put(EndEvent(session_id=scenario["events"][0]["session_id"]))
        await runner
        collector.cancel()
        await asyncio.gather(collector, return_exceptions=True)
    git = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True)
    metadata = {"type": "run_metadata", "scenario": scenario["id"], "backend": backend,
                "tools": "fake", "perception": "text-pass-through", "commit": git.stdout.strip(),
                "python": platform.python_version(), "platform": platform.platform(),
                "runtime_s": time.monotonic() - started, "expected_slots": scenario.get("expected_slots", {})}
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(json.dumps(e) for e in [metadata, *events]) + "\n", encoding="utf-8")
    return {"trace": str(destination), "backend": backend, "events": len(events), "mock_effects": len(tools.effects)}


def metrics(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    meta, events = rows[0], rows[1:]
    finals = [e for e in events if e["kind"] == "final"]
    final_slots = finals[-1]["state"]["slots"] if finals else {}
    expected = meta.get("expected_slots", {})
    slot_accuracy = (sum(final_slots.get(k, {}).get("value") == v for k, v in expected.items()) / len(expected)
                     if expected else None)
    return {"scenario": meta["scenario"], "backend": meta["backend"], "tools": meta["tools"],
            "final_count": len(finals), "slot_accuracy": slot_accuracy,
            "tool_calls": sum(e["kind"] == "tool_call" for e in events),
            "cancellations": sum(e["kind"] == "cancel_call" for e in events),
            "errors": sum(e["kind"] == "error" for e in events), "runtime_s": meta["runtime_s"],
            "limitation": "Single internal replay; no speech latency, clinical benefit or official score measured."}
