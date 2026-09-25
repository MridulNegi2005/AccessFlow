"""Read-only controller/policy reproduction; no real model or tools.

Run from repository root with its environment:
python docs/evidence/merged-2026-09-25/probe_stop.py
The assertions document the audited behavior, not desired acceptance criteria.
"""
import asyncio
import json

from accessflow.contracts import EndEvent, PlanProposal, Start, StartEvent, Transcript, TranscriptEvent
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, MockOnlyAuthorization
from accessflow.turn_policy import HeuristicTurnPolicy


async def probe(text):
    applied = asyncio.Event()
    calls = []

    class Reasoner:
        async def plan(self, view, manifests):
            calls.append(text)
            return PlanProposal(response="Synthetic planner response", request_complete=True)

    class ObservedAgent(Agent):
        async def _worker(self, message):
            await super()._worker(message)
            if message.kind == "observation" and self.state.status == "stopped":
                applied.set()

        async def _apply(self, plan, source=None):
            await super()._apply(plan, source)
            applied.set()

    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    agent = ObservedAgent(FakePerception(), HeuristicTurnPolicy(), Reasoner(),
                          FakeTools(), MockOnlyAuthorization(), partial_debounce_s=0)
    task = asyncio.create_task(agent.run(incoming, outgoing))
    try:
        await incoming.put(StartEvent(session_id="probe", payload=Start()))
        await incoming.put(TranscriptEvent(session_id="probe", event_id="speech", payload=Transcript(
            utterance_id="utterance", revision=0, text=text, final=True)))
        await asyncio.wait_for(applied.wait(), 5)
        events = []
        while not outgoing.empty():
            event = outgoing.get_nowait()
            events.append({"kind": event.kind, "stop_output": event.payload.get("stop_output", False)})
        return {"text": text, "planner_calls": len(calls), "state": agent.state.status,
                "outputs": events}
    finally:
        await incoming.put(EndEvent(session_id="probe"))
        await asyncio.wait_for(task, 5)


async def main():
    rows = [await probe(text) for text in ("Stop", "Cancel", "Stop speaking", "Cancel this task")]
    assert rows[0]["planner_calls"] == 1 and rows[1]["planner_calls"] == 1
    assert not any(event["stop_output"] for event in rows[2]["outputs"])
    assert rows[3]["state"] == "stopped" and rows[3]["planner_calls"] == 0
    print(json.dumps({"mode": "real_controller_policy_fake_perception_scripted_reasoning", "cases": rows}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
