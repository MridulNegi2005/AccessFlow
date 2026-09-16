import asyncio

from accessflow.contracts import PlanProposal, ProposedCall, Snapshot, ToolCall, ToolManifest, ToolResult
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


async def test_status_tool_confirms_unknown_without_repeating_write():
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
        assert sum(c.effect == "write" for c in executor.calls) == 1
    finally:
        await end(iq, task)


async def test_confirmed_no_effect_allows_bounded_retry_with_same_operation_id():
    write = manifest()
    write.status_tool = "inspect_transaction"
    write.parameters["properties"]["dedupe_key"] = {"type": "string"}
    write.idempotency_parameter = "dedupe_key"
    status = ToolManifest(name="inspect_transaction", description="Check operation outcome", effect="read",
                          parameters={"type": "object", "properties": {"operation_id": {"type": "string"}},
                                      "required": ["operation_id"]})

    class Planner:
        async def plan(self, view, manifests):
            unresolved = [c for c in view.calls if c.effect == "write" and c.status == "unknown"]
            if unresolved:
                return PlanProposal(calls=[ProposedCall(tool="inspect_transaction",
                                    arguments={"operation_id": unresolved[0].operation_id})])
            return proposal()

    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            if call.effect == "read":
                return ToolResult(call_id=call.call_id, status="success",
                                  result={**call.arguments, "outcome": "no_effect"})
            if sum(c.effect == "write" for c in self.calls) == 1:
                return ToolResult(call_id=call.call_id, status="unknown")
            return ToolResult(call_id=call.call_id, status="success", committed=True,
                              result={"mock": True})

    executor = Executor()
    agent, iq, oq, task = await start([], tools=executor, manifests=[write, status], reasoner=Planner())
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        writes = [c for c in executor.calls if c.effect == "write"]
        assert len(writes) == 2
        assert writes[0].call_id != writes[1].call_id
        assert writes[0].operation_id == writes[1].operation_id
        assert writes[0].arguments["dedupe_key"] == writes[1].arguments["dedupe_key"]
    finally:
        await end(iq, task)


async def test_unknown_write_timeout_with_manual_clock():
    from accessflow.clock import ManualClock
    from accessflow.contracts import Start, StartEvent
    from accessflow.engine import Agent
    from accessflow.fakes import FakePerception, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner

    clock = ManualClock()
    agent = Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner([proposal()]),
                  FakeTools(gate=asyncio.Event()), MockOnlyAuthorization())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq, clock))
    try:
        await iq.put(StartEvent(session_id="s", payload=Start(tools=[manifest(timeout=1)])))
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "tool_call")
        for _ in range(20):
            await asyncio.sleep(0)
        clock.advance(1.01)
        event = await wait_for(oq, lambda e: e.payload.get("code") == "write_outcome_unknown")
        assert event.state.status == "needs_reconciliation"
        assert not agent.executor.effects
    finally:
        await end(iq, task)


# --- R6: receipt/status-parameter namespace vs. conversational slots --------------
#
# A status tool's lookup parameter (e.g. "receipt") is ledger operation identity,
# not a conversational slot. The planner may legitimately list that parameter name
# in a call's `dependencies` to flag what the call depends on, even though no such
# slot exists in session.state.slots. See docs/reviews/CLAUDE_REVIEW_2026-09-15.md,
# "R6 -- Fix the reconciliation explanation and namespace handling".

def _agent_with_ledger(manifests, calls):
    agent = Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner([]), None, MockOnlyAuthorization())
    agent.manifests = {m.name: m for m in manifests}
    agent.state = Snapshot()
    agent.ledger = {c.call_id: c for c in calls}
    return agent


def _status_tool(name="check_receipt", parameter="receipt"):
    return ToolManifest(name=name, description="Check receipt", effect="read",
                        parameters={"type": "object", "properties": {parameter: {"type": "string"}},
                                    "required": [parameter]})


def test_receipt_named_dependency_for_the_matching_unresolved_write_is_accepted():
    write = manifest()
    write.status_tool = "check_receipt"
    status = _status_tool()
    unresolved = ToolCall(call_id="w1", operation_id="op-live", tool=write.name, arguments={},
                          dependencies={}, effect="write", status="unknown")
    agent = _agent_with_ledger([write, status], [unresolved])
    proposed = ProposedCall(tool=status.name, arguments={"receipt": "op-live"}, dependencies=["receipt"])
    assert agent._argument_dependency_error(proposed, status) is None


def test_stale_resolved_operation_identity_in_dependencies_is_still_rejected():
    # The operation is no longer unresolved (status "success", not "unknown" or
    # "cancelled"): it must not be accepted just because it once was.
    write = manifest()
    write.status_tool = "check_receipt"
    status = _status_tool()
    resolved = ToolCall(call_id="w1", operation_id="op-old", tool=write.name, arguments={},
                        dependencies={}, effect="write", status="success")
    agent = _agent_with_ledger([write, status], [resolved])
    proposed = ProposedCall(tool=status.name, arguments={"receipt": "op-old"}, dependencies=["receipt"])
    assert agent._argument_dependency_error(proposed, status) == "missing_dependency"


def test_unrelated_operation_identity_in_dependencies_is_still_rejected():
    write = manifest()
    write.status_tool = "check_receipt"
    status = _status_tool()
    unresolved = ToolCall(call_id="w1", operation_id="op-live", tool=write.name, arguments={},
                          dependencies={}, effect="write", status="unknown")
    agent = _agent_with_ledger([write, status], [unresolved])
    proposed = ProposedCall(tool=status.name, arguments={"receipt": "invented-id"}, dependencies=["receipt"])
    assert agent._argument_dependency_error(proposed, status) == "missing_dependency"


def test_operation_identity_for_a_different_status_tool_in_dependencies_is_rejected():
    # Genuinely unresolved, but this manifest is not ITS declared status tool: a
    # matching string is not enough, the manifest identity must match too.
    write = manifest()
    write.status_tool = "check_receipt"
    other_status = _status_tool(name="other_lookup")
    unresolved = ToolCall(call_id="w1", operation_id="op-live", tool=write.name, arguments={},
                          dependencies={}, effect="write", status="unknown")
    agent = _agent_with_ledger([write, other_status], [unresolved])
    proposed = ProposedCall(tool=other_status.name, arguments={"receipt": "op-live"}, dependencies=["receipt"])
    assert agent._argument_dependency_error(proposed, other_status) == "missing_dependency"


async def test_status_tool_confirms_unknown_when_planner_also_lists_the_status_parameter_as_a_dependency():
    # End-to-end reproduction of the reviewer's exact repro: {"dependencies":
    # ["receipt"], "guard_error": "missing_dependency"} must no longer occur.
    write = manifest()
    write.status_tool = "check_receipt"
    status = _status_tool()

    class Planner:
        async def plan(self, view, manifests):
            unknown = [c for c in view.calls if c.effect == "write" and c.status == "unknown"]
            if unknown:
                return PlanProposal(calls=[ProposedCall(tool="check_receipt",
                                    arguments={"receipt": unknown[0].operation_id},
                                    dependencies=["receipt"])])
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
    events = []
    try:
        await iq.put(transcript())
        result = await wait_for(oq, lambda e: events.append(e) or e.kind == "final")
        assert result.payload["basis"] == "reconciled_tool_effect"
        assert not any(e.payload.get("code") == "missing_dependency" for e in events)
        assert sum(c.effect == "write" for c in executor.calls) == 1
    finally:
        await end(iq, task)


def test_alias_cannot_borrow_a_ledger_dependency_to_skip_grounding():
    """An alias target is a slot name. A ledger dependency is a parameter name.

    Comparing the two let any other parameter alias onto the ledger name and skip
    grounding, so a value the user never supplied could reach the status tool.
    """
    write = manifest()
    write.status_tool = "check_receipt"
    status = ToolManifest(name="check_receipt", description="Check receipt", effect="read",
                          parameters={"type": "object",
                                      "properties": {"receipt": {"type": "string"},
                                                     "account": {"type": "string"}},
                                      "required": ["receipt"]})
    unresolved = ToolCall(call_id="w1", operation_id="op-live", tool=write.name, arguments={},
                          dependencies={}, effect="write", status="unknown")
    agent = _agent_with_ledger([write, status], [unresolved])

    grounded = ProposedCall(tool=status.name, arguments={"receipt": "op-live"},
                            dependencies=["receipt"])
    assert agent._argument_dependency_error(grounded, status) is None

    smuggled = ProposedCall(tool=status.name,
                            arguments={"receipt": "op-live", "account": "victim-42"},
                            dependencies=["receipt"], argument_slots={"account": "receipt"})
    assert agent._argument_dependency_error(smuggled, status) == "missing_dependency"
