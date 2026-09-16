"""R2: continuation state and write intent belong to the active request, not the
whole session. See docs/reviews/CLAUDE_REVIEW_2026-09-15.md, "R2 -- Make
continuation state belong to the current request."
"""
import asyncio

from accessflow.adapters.models import ModelReasoner
from accessflow.contracts import (
    PlanProposal, ProposedCall, SessionView, Snapshot, ToolCall, ToolManifest, ToolResult,
)
from accessflow.fakes import FakeTools
from test_safety import end, manifest, proposal, start, transcript, wait_for


def _call(request_id, status, effect="write", call_id="c", operation_id="op", tool="reserve"):
    return ToolCall(call_id=call_id, operation_id=operation_id, tool=tool, arguments={},
                    dependencies={}, effect=effect, status=status, request_id=request_id)


# --- Unit level: ModelReasoner.write_outstanding / plan() scoping -----------------

def test_write_outstanding_reproduction_is_scoped_to_the_active_request():
    # Reviewer's direct reproduction: write_pending=True plus one OLD successful
    # write used to yield write_outstanding=False regardless of which request the
    # write belonged to. It must now depend on whether that write belongs to the
    # view's active_request_id.
    old_write = _call(request_id="request-a", status="success")
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[],
                       calls=[old_write], write_pending=True, active_request_id="request-b")
    assert ModelReasoner.write_outstanding(view) is True

    same_request_view = view.model_copy(update={"active_request_id": "request-a"})
    assert ModelReasoner.write_outstanding(same_request_view) is False


def test_write_outstanding_unscoped_default_matches_prior_behaviour():
    # Callers that never populate request_id/active_request_id (hand-built fixtures,
    # existing test doubles) keep the original whole-session-looking behaviour,
    # since both fields default to "".
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[],
                       calls=[_call(request_id="", status="success")], write_pending=True)
    assert ModelReasoner.write_outstanding(view) is False


def test_write_outstanding_unknown_status_still_counts_as_outstanding_for_active_request():
    old_resolved = _call(request_id="request-a", status="success", call_id="c1", operation_id="op1")
    current_unknown = _call(request_id="request-b", status="unknown", call_id="c2", operation_id="op2")
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[],
                       calls=[old_resolved, current_unknown], write_pending=True,
                       active_request_id="request-b")
    assert ModelReasoner.write_outstanding(view) is False


async def test_pending_write_continuation_not_suppressed_by_an_older_resolved_request():
    seen = {}

    class Backend:
        async def generate(self, system, data, schema):
            seen["data"], seen["schema"] = data, schema
            return PlanProposal(clarification="Which day?").model_dump()

    write = ToolManifest(name="file_visit_request", description="Book visit", effect="write",
                         parameters={"type": "object"})
    old_write = _call(request_id="old-request", status="success", tool=write.name)
    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[],
                       calls=[old_write], write_pending=True, active_request_id="new-request")
    await ModelReasoner(Backend()).plan(view, [write])
    assert seen["data"]["required_next_step"]["kind"] == "complete_requested_write"
    assert seen["schema"]["properties"]["response"]["type"] == "null"


# --- Engine integration: multiple requests in one session -------------------------

READ = ToolManifest(name="check_availability", description="Check availability", effect="read",
                    parameters={"type": "object", "properties": {"day": {"type": "string"}},
                                "required": ["day"], "additionalProperties": False})


async def test_completed_request_does_not_disable_a_later_read_then_write_request():
    class Planner:
        def __init__(self):
            self.friday_turns = 0

        async def plan(self, view, manifests):
            text = view.observations[-1].text if view.observations else ""
            if "Wednesday" in text:
                return proposal("Wednesday")
            self.friday_turns += 1
            if self.friday_turns == 1:
                return PlanProposal(intent="service", slot_updates={"day": "Friday"},
                                    request_complete=True, write_requested=True,
                                    calls=[ProposedCall(tool="check_availability",
                                                        arguments={"day": "Friday"}, dependencies=["day"])])
            return PlanProposal(request_complete=True, write_requested=True,
                                calls=[ProposedCall(tool="arbitrary_service",
                                                    arguments={"day": "Friday"}, dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[READ, manifest()])
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        a_final = await wait_for(oq, lambda e: e.kind == "final")
        assert a_final.payload["basis"] == "confirmed_tool_effect"

        await iq.put(transcript("Book Friday", utterance="request-b"))
        b_final = await wait_for(oq, lambda e: e.kind == "final" and e.payload.get("caused_by_event_id"))
        assert b_final.payload["basis"] == "confirmed_tool_effect"
        writes = [c for c in agent.ledger.values() if c.effect == "write"]
        assert len(writes) == 2
        assert writes[0].request_id != writes[1].request_id
        assert len(agent.executor.effects) == 2
    finally:
        await end(iq, task)


async def test_information_only_follow_up_after_a_completed_write_is_not_finalized():
    # Documents the existing, INHERITED whole-session behaviour noted by the
    # reviewer: the "prose-only final" guard in _apply refuses to answer once any
    # write call exists anywhere in the ledger, regardless of request. This is not
    # part of the R2 fix (fixing it is out of scope here); this test exists so a
    # future change to that guard is a deliberate, visible decision.
    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return proposal("Wednesday")
            return PlanProposal(response="Our hours are nine to five.", request_complete=True)

    agent, iq, oq, task = await start([], reasoner=Planner())
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(transcript("What are your hours", utterance="request-b"))
        ack = await wait_for(oq, lambda e: e.kind == "acknowledge" and "text" in e.payload)
        assert ack.payload["text"] == "I'll check that."
        # No further output arrives for this informational follow-up: the whole-
        # session write check silently drops it instead of answering.
        try:
            async with asyncio.timeout(0.5):
                stray = await oq.get()
                assert False, f"unexpected output: {stray.kind} {stray.payload}"
        except asyncio.TimeoutError:
            pass
    finally:
        await end(iq, task)


async def test_explicit_cancellation_of_the_second_request_prevents_its_write():
    gate = asyncio.Event()

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return proposal("Wednesday")
            text = view.observations[-1].text
            if "cancel" in text.lower():
                return PlanProposal(request_complete=True, write_requested=False, response="Cancelled.")
            return PlanProposal(intent="service", slot_updates={"day": "Friday"},
                                request_complete=True, write_requested=True,
                                calls=[ProposedCall(tool="arbitrary_service",
                                                    arguments={"day": "Friday"}, dependencies=["day"])])

    gate.set()
    executor = FakeTools(gate=gate)
    agent, iq, oq, task = await start([], reasoner=Planner(), tools=executor)
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        await wait_for(oq, lambda e: e.kind == "final")

        gate.clear()
        await iq.put(transcript("Book Friday", utterance="request-b"))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(transcript("Actually cancel that", utterance="request-b", revision=1))
        cancel = await wait_for(oq, lambda e: e.kind == "cancel_call")
        assert cancel.payload["reason"] == "new_evidence"
        # The engine confirms cancellation itself (a synthetic "cancelled" result
        # for a not-yet-committed write) without waiting for the still-gated
        # executor call, which is exactly what must not be allowed to commit.
        async with asyncio.timeout(2):
            while agent.ledger[cancel.payload["call_id"]].status == "cancelled":
                await asyncio.sleep(0)
        assert agent.ledger[cancel.payload["call_id"]].status == "failed"
        assert len(agent.executor.effects) == 1  # Only request A's Wednesday booking.
    finally:
        gate.set()
        await end(iq, task)


async def test_two_intentional_identical_bookings_each_commit_independently():
    agent, iq, oq, task = await start([], reasoner=_RepeatSameDayPlanner())
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        first = await wait_for(oq, lambda e: e.kind == "final")
        assert first.payload["basis"] == "confirmed_tool_effect"

        await iq.put(transcript("Book Wednesday again", utterance="request-b"))
        second = await wait_for(oq, lambda e: e.kind == "final" and e.payload["call_id"] != first.payload["call_id"])
        assert second.payload["basis"] == "confirmed_tool_effect"
        assert second.payload["operation_id"] != first.payload["operation_id"]
        writes = [c for c in agent.ledger.values() if c.effect == "write"]
        assert len(writes) == 2
        assert writes[0].request_id != writes[1].request_id
        assert len(agent.executor.effects) == 2
    finally:
        await end(iq, task)


class _RepeatSameDayPlanner:
    async def plan(self, view, manifests):
        return proposal("Wednesday")


async def test_correction_to_the_second_request_does_not_touch_the_first():
    gate = asyncio.Event()

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return proposal("Wednesday")
            day = "Saturday" if "Saturday" in view.observations[-1].text else "Friday"
            return proposal(day)

    gate.set()
    executor = FakeTools(gate=gate)
    agent, iq, oq, task = await start([], reasoner=Planner(), tools=executor)
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        await wait_for(oq, lambda e: e.kind == "final")

        gate.clear()
        await iq.put(transcript("Book Friday", utterance="request-b"))
        first_call = await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(transcript("Actually Saturday", utterance="request-b", revision=1))
        cancel = await wait_for(oq, lambda e: e.kind == "cancel_call")
        assert cancel.payload["call_id"] == first_call.payload["call_id"]
        # Cancellation is set synchronously; the ledger reflects it immediately,
        # before the executor's own (still gated) confirmation arrives.
        assert agent.ledger[first_call.payload["call_id"]].status == "cancelled"
        # Let the executor's own cancel() land before releasing the gate, so the
        # still-blocked Friday execute() call sees it and does not race a commit.
        async with asyncio.timeout(2):
            while first_call.payload["call_id"] not in executor.cancelled:
                await asyncio.sleep(0)
        gate.set()
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.state.slots["day"].value == "Saturday"
        assert len(agent.executor.effects) == 2  # request A's Wednesday + request B's Saturday
    finally:
        gate.set()
        await end(iq, task)


async def test_unknown_outcome_on_the_second_request_is_reconciled_independently_of_the_first():
    status = ToolManifest(name="inspect_transaction", description="Check operation outcome", effect="read",
                          parameters={"type": "object", "properties": {"operation_id": {"type": "string"}},
                                      "required": ["operation_id"]})
    write = manifest()
    write.status_tool = "inspect_transaction"

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return proposal("Wednesday")
            unknown = [c for c in view.calls if c.effect == "write" and c.status == "unknown"]
            if unknown:
                return PlanProposal(calls=[ProposedCall(tool="inspect_transaction",
                                    arguments={"operation_id": unknown[0].operation_id},
                                    dependencies=["operation_id"])])
            return proposal("Friday")

    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            if call.effect == "write" and call.arguments.get("day") == "Friday":
                self.operation = call.operation_id
                return ToolResult(call_id=call.call_id, status="unknown")
            if call.effect == "read":
                return ToolResult(call_id=call.call_id, status="success",
                                  result={"operation_id": self.operation, "outcome": "committed"})
            return await super().execute(call)

    executor = Executor()
    agent, iq, oq, task = await start([], reasoner=Planner(), tools=executor, manifests=[write, status])
    try:
        await iq.put(transcript("Book Wednesday", utterance="request-a"))
        a_final = await wait_for(oq, lambda e: e.kind == "final")
        assert a_final.payload["basis"] == "confirmed_tool_effect"
        a_write = next(c for c in agent.ledger.values() if c.effect == "write")

        await iq.put(transcript("Book Friday", utterance="request-b"))
        b_final = await wait_for(oq, lambda e: e.kind == "final" and e.payload["basis"] == "reconciled_tool_effect")
        b_write = next(c for c in agent.ledger.values()
                       if c.effect == "write" and c.call_id != a_write.call_id)
        assert b_final.payload["operation_id"] == b_write.operation_id
        assert b_write.request_id != a_write.request_id
        assert a_write.status == "success"  # Untouched by B's reconciliation.
        assert b_write.status == "success"
    finally:
        await end(iq, task)


async def test_dropped_write_flag_across_continuation_does_not_finalize_without_effect():
    # Direct regression for Problem B: a plan produced from a tool result for the
    # SAME request drops write_requested. Before the fix, this silently erased
    # recognised intent and let a later prose-only proposal claim completion with
    # no effect ever dispatched. After the fix, intent survives the continuation
    # and the controller refuses the false completion instead.
    read_two = ToolManifest(name="confirm_details", description="Confirm details", effect="read",
                            parameters={"type": "object", "properties": {"day": {"type": "string"}},
                                        "required": ["day"], "additionalProperties": False})

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    request_complete=True, write_requested=True,
                                    calls=[ProposedCall(tool="check_availability",
                                                        arguments={"day": "Wednesday"}, dependencies=["day"])])
            if self.n == 2:
                # Tool-result-triggered replan for the SAME request drops the flag.
                return PlanProposal(request_complete=True, write_requested=False,
                                    calls=[ProposedCall(tool="confirm_details",
                                                        arguments={"day": "Wednesday"}, dependencies=["day"])])
            # Hallucinated prose completion; the write was never dispatched.
            return PlanProposal(request_complete=True, write_requested=False,
                                response="Everything looks good.")

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[READ, read_two, manifest()])
    try:
        await iq.put(transcript("Book Wednesday if available", utterance="request-a"))
        error = await wait_for(oq, lambda e: e.kind in {"error", "final"})
        assert error.kind == "error"
        assert error.payload["code"] == "write_owed_not_progressed"
        assert not agent.executor.effects
        assert not any(c.effect == "write" for c in agent.ledger.values())
    finally:
        await end(iq, task)
