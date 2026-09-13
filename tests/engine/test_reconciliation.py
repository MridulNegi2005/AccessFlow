import asyncio

from accessflow.contracts import PlanProposal, ProposedCall, ToolManifest, ToolResult
from accessflow.fakes import FakeTools
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
