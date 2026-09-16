import asyncio

import pytest

from accessflow.contracts import PlanProposal, ProposedCall, ToolManifest
from test_safety import end, manifest, proposal, start, transcript, wait_for


@pytest.mark.parametrize("effect", ["read", "write"])
@pytest.mark.parametrize("bad_plan", ["empty", "unrelated", "contradictory"])
async def test_untracked_or_contradictory_arguments_never_dispatch(effect, bad_plan):
    plan = proposal()
    if bad_plan == "empty":
        plan.calls[0].dependencies = []
    elif bad_plan == "unrelated":
        plan.slot_updates = {"symptom": "flicker"}
        plan.calls[0].dependencies = ["symptom"]
    else:
        plan.calls[0].arguments["day"] = "Tuesday"
    agent, iq, oq, task = await start([plan], manifests=[manifest(effect=effect)])
    try:
        await iq.put(transcript())
        decision = await wait_for(oq, lambda e: e.kind in {"error", "tool_call"})
        assert decision.kind == "error"
        assert decision.payload["code"] in {"missing_dependency", "argument_dependency_mismatch"}
        assert not agent.ledger
        assert not agent.executor.calls
    finally:
        await end(iq, task)


@pytest.mark.parametrize("literal_schema", [{"const": "static"}, {"enum": ["static"]}])
async def test_manifest_fixed_literals_do_not_need_conversation_slots(literal_schema):
    tool = ToolManifest(name="catalog", description="Static catalog", effect="read",
                        parameters={"type": "object", "properties": {"category": literal_schema},
                                    "required": ["category"]})
    plan = PlanProposal(calls=[ProposedCall(tool=tool.name, arguments={"category": "static"})])
    agent, iq, oq, task = await start([plan], manifests=[tool])
    try:
        await iq.put(transcript("Show catalog"))
        await wait_for(oq, lambda e: e.payload.get("basis") == "tool_evidence")
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)


async def test_model_nonce_does_not_change_retry_operation_identity():
    # A read after a confirmed failed write triggers a replan of the same request.
    # A changed model-supplied nonce must not create a fresh write operation.
    from accessflow.contracts import ToolResult
    from accessflow.fakes import FakeTools

    tool = manifest()
    tool.parameters["properties"]["nonce"] = {"type": "string"}
    tool.idempotency_parameter = "nonce"
    read = ToolManifest(name="catalog", description="Static catalog", effect="read",
                        parameters={"type": "object", "properties": {}})
    failed = asyncio.Event()

    class Executor(FakeTools):
        async def execute(self, call):
            if call.effect == "read":
                await failed.wait()
                return await super().execute(call)
            if not any(c.effect == "write" for c in self.calls):
                self.calls.append(call)
                failed.set()
                return ToolResult(call_id=call.call_id, status="failed")
            return await super().execute(call)

    first, second = proposal(), proposal()
    first.calls[0].arguments["nonce"] = "model-nonce-one"
    first.calls.append(ProposedCall(tool=read.name, arguments={}))
    second.calls[0].arguments["nonce"] = "model-nonce-two"
    agent, iq, oq, task = await start([first, second], tools=Executor(), manifests=[tool, read])
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        writes = [c for c in agent.executor.calls if c.effect == "write"]
        assert len(writes) == 2
        assert writes[0].operation_id == writes[1].operation_id
        assert writes[0].arguments["nonce"] == writes[1].arguments["nonce"]
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("completed", [False, True])
async def test_alias_dependency_rejects_obsolete_read_after_correction(completed):
    from accessflow.fakes import FakeTools

    gate = asyncio.Event()
    if completed:
        gate.set()
    tool = ToolManifest(name="free_windows", description="Read available slots", effect="read",
                        parameters={"type": "object", "properties": {"visit_day": {"type": "string"}}})
    first = PlanProposal(slot_updates={"day": "Tuesday"}, calls=[ProposedCall(
        tool=tool.name, arguments={"visit_day": "Tuesday"},
        argument_slots={"visit_day": "day"}, dependencies=["day"])])

    class Planner:
        async def plan(self, view, manifests):
            if "Wednesday" in view.observations[-1].text:
                return PlanProposal(slot_updates={"day": "Wednesday"}, response="Correction saved")
            if view.results:
                return PlanProposal(response="Read completed")
            return first

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[tool],
                                     tools=FakeTools(gate=gate, ignore_cancel=True))
    try:
        await iq.put(transcript("Check Tuesday"))
        dispatched = await wait_for(oq, lambda e: e.kind == "tool_call")
        original = dispatched.payload["call_id"]
        if completed:
            await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(transcript("Actually Wednesday", revision=1))
        await wait_for(oq, lambda e: e.kind == "final" and e.payload.get("text") == "Correction saved")
        assert agent.ledger[original].status == ("stale" if completed else "cancelled")
        gate.set()
        for _ in range(30):
            await asyncio.sleep(0)
        assert agent.ledger[original].status == "stale"
        assert all(result.call_id != original for result in agent.results)
        assert len(agent.executor.calls) == 1
    finally:
        gate.set()
        await end(iq, task)


@pytest.mark.parametrize("value,slot_value", [(True, 1), ({"enabled": True}, {"enabled": 1})])
async def test_json_boolean_is_not_a_numeric_slot_value(value, slot_value):
    tool = ToolManifest(name="lookup", description="Lookup", effect="read",
                        parameters={"type": "object", "properties": {"key": {}}})
    plan = PlanProposal(slot_updates={"key": slot_value}, calls=[ProposedCall(
        tool=tool.name, arguments={"key": value}, dependencies=["key"])])
    agent, iq, oq, task = await start([plan], manifests=[tool])
    try:
        await iq.put(transcript("Lookup"))
        result = await wait_for(oq, lambda e: e.kind in {"error", "tool_call"})
        assert result.payload.get("code") == "argument_dependency_mismatch"
        assert not agent.ledger
    finally:
        await end(iq, task)


async def test_arbitrary_operation_string_is_not_exempt_from_dependencies():
    tool = ToolManifest(name="receipt", description="Read receipt", effect="read",
                        parameters={"type": "object", "properties": {"ref": {"type": "string"}}})
    plan = PlanProposal(calls=[ProposedCall(tool=tool.name, arguments={"ref": "invented-operation"})])
    agent, iq, oq, task = await start([plan], manifests=[tool])
    try:
        await iq.put(transcript("Check receipt"))
        result = await wait_for(oq, lambda e: e.kind in {"error", "tool_call"})
        assert result.payload.get("code") == "missing_dependency"
        assert not agent.ledger
    finally:
        await end(iq, task)
