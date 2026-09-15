"""Acceptance tests for R1: enforce the exact generated schema locally, defend final outputs.

See docs/reviews/CLAUDE_REVIEW_2026-09-15.md, "R1 -- Enforce the exact generated schema
locally, and defend final outputs". Each test below is written to fail against the
pre-fix code: the static PlanProposal model alone accepts these bad responses, and
engine.py's informational-final gate only checked whether any write call had ever
appeared in the ledger, never whether the current request's write was still owed.
"""
import asyncio
import json

import httpx
import jsonschema
import pytest

from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.contracts import (
    PlanProposal, ProposedCall, SessionView, Snapshot, ToolCall, ToolManifest, ToolResult,
)
from accessflow.fakes import FakeTools
from test_safety import end, manifest, proposal, start, transcript, wait_for


# --- 1. Hosted response returns a string when this request's schema requires null -------

async def test_hosted_string_response_rejected_when_schema_requires_null():
    write = ToolManifest(name="file_visit_request", description="Book a visit", effect="write",
                         parameters={"type": "object"})
    view = SessionView(
        session_id="s", state=Snapshot(), observations=[], results=[],
        calls=[ToolCall(call_id="r", operation_id="op", tool="inspect_availability", arguments={},
                        dependencies={}, effect="read", status="success")],
        write_pending=True)
    # Exactly the review's reproduction: a complete, otherwise-valid PlanProposal whose
    # only fault is the false completion claim in `response`.
    bad = PlanProposal(response="The service is booked.").model_dump(mode="json")

    def handler(request):
        return httpx.Response(200, json={"message": {"content": json.dumps(bad)}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(jsonschema.exceptions.ValidationError):
            await ModelReasoner(backend).plan(view, [write])
    evidence = backend.evidence()
    assert evidence["outcome_counts"] == {"success": 0, "failure": 1, "cancelled": 0}
    assert evidence["requests"][0]["outcome"] == "failure"


# --- 2. Unlisted tool name / write during unresolved outcome: schema boundary + controller

async def test_hosted_response_naming_unlisted_tool_rejected_at_schema_boundary():
    read = ToolManifest(name="inspect_v3", description="Inspect", effect="read", parameters={"type": "object"})
    bad = PlanProposal(calls=[ProposedCall(tool="invented_tool", arguments={})]).model_dump(mode="json")

    def handler(request):
        return httpx.Response(200, json={"message": {"content": json.dumps(bad)}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(jsonschema.exceptions.ValidationError):
            await ModelReasoner(backend).plan(
                SessionView(session_id="s", state=Snapshot(), observations=[], results=[]), [read])
    assert backend.evidence()["outcome_counts"]["success"] == 0


async def test_hosted_response_proposing_write_during_unresolved_outcome_rejected_at_schema_boundary():
    write = ToolManifest(name="reserve_v3", description="Reserve", effect="write",
                         parameters={"type": "object"}, status_tool="inspect_v3")
    read = ToolManifest(name="inspect_v3", description="Inspect", effect="read", parameters={"type": "object"})
    view = SessionView(
        session_id="s", state=Snapshot(), observations=[], results=[],
        calls=[ToolCall(call_id="c", operation_id="op", tool=write.name, arguments={},
                        dependencies={}, effect="write", status="unknown")])
    bad = PlanProposal(calls=[ProposedCall(tool=write.name, arguments={})]).model_dump(mode="json")

    def handler(request):
        return httpx.Response(200, json={"message": {"content": json.dumps(bad)}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        backend = JsonBackend(client=client)
        with pytest.raises(jsonschema.exceptions.ValidationError):
            await ModelReasoner(backend).plan(view, [read, write])
    assert backend.evidence()["outcome_counts"]["success"] == 0


async def test_controller_still_blocks_unresolved_outcome_write_if_reasoner_bypasses_schema():
    """Defense in depth: even a reasoner double that skips schema checking entirely
    (ScriptedReasoner returns raw PlanProposal objects) is still stopped by the
    controller's own unresolved-outcome guard in engine.py."""
    write = manifest(name="reserve_v9")

    class Planner:
        async def plan(self, view, manifests):
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"}, request_complete=True,
                                write_requested=True,
                                calls=[ProposedCall(tool="reserve_v9", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[write],
                                      tools=FakeTools(outcome="unknown"))
    try:
        await iq.put(transcript("Book Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "write_outcome_unknown")
        clarify = await wait_for(oq, lambda e: e.kind == "clarify")
        assert "unresolved outcome" in clarify.payload["text"]
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)


# --- 3. Read-then-prose while a requested write is outstanding --------------------------

async def test_read_then_prose_does_not_falsely_complete_an_outstanding_write():
    read_tool = manifest(effect="read", name="availability_check")
    write_tool = manifest(effect="write", name="file_visit_request")

    class Planner:
        def __init__(self):
            self.calls = 0

        async def plan(self, view, manifests):
            self.calls += 1
            if not view.results:
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    request_complete=True, write_requested=True,
                                    calls=[ProposedCall(tool="availability_check", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            # A model that treats a completed read as though it finished the write.
            return PlanProposal(response="The service is booked.")

    planner = Planner()
    agent, iq, oq, task = await start([], reasoner=planner, manifests=[read_tool, write_tool])
    try:
        await iq.put(transcript("Check availability and book Wednesday"))
        for _ in range(2):
            await wait_for(oq, lambda e: e.payload.get("code") == "write_owed_not_progressed")
        for _ in range(30):
            await asyncio.sleep(0)
        # Bounded: exactly one retry was granted (initial read plan + two prose attempts).
        assert planner.calls == 3
        assert not any(c.tool == "file_visit_request" for c in agent.ledger.values())
        assert not agent.executor.effects
    finally:
        await end(iq, task)


# --- 4. Legitimate information-only requests still answer normally (regression) ---------

async def test_information_only_request_still_answers_normally():
    agent, iq, oq, task = await start([PlanProposal(response="Here is general information.",
                                                     request_complete=True)])
    try:
        await iq.put(transcript("What are your hours?"))
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["basis"] == "informational"
        assert final.payload["text"] == "Here is general information."
        assert not agent.executor.calls
    finally:
        await end(iq, task)


# --- 5. Confirmed and reconciled writes still emit their controller finals (regression) -

async def test_confirmed_write_still_emits_final():
    agent, iq, oq, task = await start([proposal(name="unfamiliar_99")], manifests=[manifest(name="unfamiliar_99")])
    try:
        await iq.put(transcript())
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


async def test_reconciled_write_still_emits_final():
    write = manifest()
    write.status_tool = "inspect_transaction"
    status = ToolManifest(name="inspect_transaction", description="Check operation outcome", effect="read",
                          parameters={"type": "object", "properties": {"operation_id": {"type": "string"}},
                                      "required": ["operation_id"]})

    class Planner:
        async def plan(self, view, manifests):
            unknown = [c for c in view.calls if c.effect == "write" and c.status == "unknown"]
            if unknown:
                return PlanProposal(calls=[ProposedCall(tool="inspect_transaction",
                                    arguments={"operation_id": unknown[0].operation_id})])
            return proposal()

    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            if call.effect == "write":
                self.operation = call.operation_id
                return ToolResult(call_id=call.call_id, status="unknown")
            return ToolResult(call_id=call.call_id, status="success",
                              result={"operation_id": self.operation, "outcome": "committed"})

    executor = Executor()
    agent, iq, oq, task = await start([], tools=executor, manifests=[write, status], reasoner=Planner())
    try:
        await iq.put(transcript())
        result = await wait_for(oq, lambda e: e.kind == "final")
        assert result.payload["basis"] == "reconciled_tool_effect"
    finally:
        await end(iq, task)
