import asyncio

import pytest

from accessflow.contracts import (
    EndEvent, Interrupt, InterruptEvent, PlanProposal, ProposedCall, ResultEvent,
    Start, StartEvent, ToolManifest, ToolResult, Transcript, TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner


def manifest(effect="write", name="arbitrary_service", timeout=1):
    return ToolManifest(name=name, description="Test service", effect=effect, timeout_s=timeout,
                        parameters={"type": "object", "properties": {"day": {"type": "string"}},
                                    "required": ["day"], "additionalProperties": False})


def proposal(day="Wednesday", name="arbitrary_service"):
    return PlanProposal(intent="service", slot_updates={"day": day}, request_complete=True,
                        write_requested=True, calls=[ProposedCall(tool=name, arguments={"day": day},
                                                                 dependencies=["day"])])


def transcript(text="Book Wednesday", revision=0, final=True, utterance="u"):
    return TranscriptEvent(session_id="s", payload=Transcript(utterance_id=utterance, revision=revision,
                                                              text=text, final=final))


async def wait_for(output, predicate):
    async with asyncio.timeout(2):
        while True:
            event = await output.get()
            if predicate(event):
                return event


async def start(plans, tools=None, manifests=None, auth=True, reasoner=None, **kwargs):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    executor = tools if tools is not None else FakeTools()
    agent = Agent(FakePerception(), FinalFlagPolicy(), reasoner or ScriptedReasoner(plans), executor,
                  MockOnlyAuthorization() if auth else None, **kwargs)
    task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id="s", payload=Start(tools=manifests or [manifest()])))
    return agent, incoming, outgoing, task


async def end(incoming, task):
    await incoming.put(EndEvent(session_id="s"))
    await asyncio.wait_for(task, 2)


async def test_confirmed_dynamic_write_and_unchanged_slots():
    agent, iq, oq, task = await start([proposal(name="unfamiliar_42")], manifests=[manifest(name="unfamiliar_42")])
    try:
        await iq.put(transcript())
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert final.state.slots["day"].value == "Wednesday"
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


async def test_partial_never_writes_and_revisions_replace():
    reasoner = ScriptedReasoner([proposal("Tuesday"), proposal()])
    agent, iq, oq, task = await start([], reasoner=reasoner)
    try:
        await iq.put(transcript("Book Tues", final=False))
        for _ in range(30):
            await asyncio.sleep(0)
        assert not agent.executor.calls
        await iq.put(transcript("Book Wednesday", revision=1))
        await wait_for(oq, lambda e: e.kind == "final")
        assert agent.state.slots["day"].value == "Wednesday"
        assert len(reasoner.views[-1].observations) == 1
        await iq.put(transcript("Old Tuesday", revision=0))
        for _ in range(10):
            await asyncio.sleep(0)
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_authorization_defaults_to_deny():
    agent, iq, oq, task = await start([proposal()], auth=False)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert not agent.executor.calls
    finally:
        await end(iq, task)


async def test_cancel_before_commit_has_no_effect():
    gate = asyncio.Event()
    executor = FakeTools(gate=gate)
    agent, iq, oq, task = await start([proposal()], tools=executor)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt()))
        cancel = await wait_for(oq, lambda e: e.kind == "cancel_call")
        assert cancel.payload["reason"] == "interrupted"
        for _ in range(20):
            await asyncio.sleep(0)
        gate.set()
        for _ in range(20):
            await asyncio.sleep(0)
        assert not executor.effects
        assert agent.state.correction_pending
    finally:
        await end(iq, task)


async def test_committed_after_cancel_reported_not_rolled_back():
    gate = asyncio.Event()
    executor = FakeTools(gate=gate, ignore_cancel=True)
    agent, iq, oq, task = await start([proposal()], tools=executor)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt()))
        await wait_for(oq, lambda e: e.kind == "cancel_call")
        gate.set()
        event = await wait_for(oq, lambda e: e.payload.get("code") == "effect_committed_after_invalidation")
        assert event.kind == "error"
        assert len(executor.effects) == 1
    finally:
        await end(iq, task)


async def test_duplicate_result_cannot_duplicate_final_or_write():
    agent, iq, oq, task = await start([proposal()])
    try:
        await iq.put(transcript())
        final = await wait_for(oq, lambda e: e.kind == "final")
        call_id = final.payload["call_id"]
        for _ in range(2):
            await iq.put(ResultEvent(session_id="s", payload=ToolResult(call_id=call_id, status="success",
                                                                         committed=True)))
        for _ in range(10):
            await asyncio.sleep(0)
        assert oq.empty()
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)


async def test_intentional_repeat_is_a_distinct_operation():
    agent, iq, oq, task = await start([proposal(), proposal()])
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(transcript("Book another Wednesday appointment", utterance="u2"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 2
        assert agent.executor.calls[0].operation_id != agent.executor.calls[1].operation_id
    finally:
        await end(iq, task)


async def test_unknown_write_never_blindly_retried():
    agent, iq, oq, task = await start([proposal(), proposal()], tools=FakeTools(outcome="unknown"))
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.payload.get("code") == "write_outcome_unknown")
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert len(agent.executor.calls) == 1
        assert agent.state.status == "needs_reconciliation"
    finally:
        await end(iq, task)


async def test_changed_dependency_discards_late_read():
    gate = asyncio.Event()
    executor = FakeTools(gate=gate, ignore_cancel=True)
    agent, iq, oq, task = await start([proposal("Tuesday"), PlanProposal(slot_updates={"day": "Wednesday"})],
                                     tools=executor, manifests=[manifest(effect="read")])
    try:
        await iq.put(transcript("Check Tuesday"))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(transcript("Actually Wednesday", revision=1))
        await wait_for(oq, lambda e: e.kind == "cancel_call")
        gate.set()
        for _ in range(30):
            await asyncio.sleep(0)
        assert not agent.results
        assert list(agent.ledger.values())[0].status == "stale"
    finally:
        await end(iq, task)


async def test_slow_reasoner_does_not_block_interrupt():
    class Slow:
        async def plan(self, view, manifests):
            await asyncio.Event().wait()
    agent, iq, oq, task = await start([], reasoner=Slow())
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "acknowledge")
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        stopped = await wait_for(oq, lambda e: e.payload.get("stop_output"))
        assert stopped.state.status == "stopped"
    finally:
        await end(iq, task)


@pytest.mark.parametrize("bad_call", [ProposedCall(tool="absent", arguments={}),
                                       ProposedCall(tool="arbitrary_service", arguments={"day": 42})])
async def test_invalid_model_call_rejected(bad_call):
    agent, iq, oq, task = await start([PlanProposal(calls=[bad_call], request_complete=True, write_requested=True)])
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "error")
        assert not agent.executor.calls
    finally:
        await end(iq, task)
