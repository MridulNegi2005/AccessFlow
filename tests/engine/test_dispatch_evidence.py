import asyncio

from accessflow.contracts import Interrupt, InterruptEvent, PlanProposal, Start, StartEvent
from accessflow.engine import Agent
from accessflow.evaluation.mock_environment import MockEnvironment, WriteConfig
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


async def test_cancellation_before_local_executor_starts_prevents_dispatch():
    release, attempted = asyncio.Event(), asyncio.Event()
    class DelayedDispatch(Agent):
        async def _execute(self, call, timeout):
            await release.wait()
            await super()._execute(call, timeout)
            attempted.set()
    tool = manifest()
    executor = MockEnvironment([tool], {tool.name: WriteConfig()})
    agent = DelayedDispatch(FakePerception(), FinalFlagPolicy(), ScriptedReasoner([proposal()]),
                            executor, MockOnlyAuthorization())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    try:
        await iq.put(StartEvent(session_id="s", payload=Start(tools=[tool])))
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        await wait_for(oq, lambda e: e.payload.get("stop_output"))
        release.set()
        await asyncio.wait_for(attempted.wait(), 1)
        assert not executor.effects
    finally:
        release.set()
        await end(iq, task)


async def test_correction_expires_accepted_read_evidence_and_refetches():
    class Planner:
        async def plan(self, view, manifests):
            day = "Wednesday" if "Wednesday" in view.observations[-1].text else "Tuesday"
            if view.state.slots.get("day") and view.state.slots["day"].value == day and view.results:
                return PlanProposal(response="Read evidence is available")
            return proposal(day)
    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[manifest(effect="read")], tools=FakeTools())
    try:
        await iq.put(transcript("Check Tuesday"))
        await wait_for(oq, lambda e: e.kind == "final")
        original_call = next(iter(agent.ledger))
        await iq.put(transcript("Actually Wednesday", revision=1))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.calls) == 2
        assert agent.ledger[original_call].status == "stale"
        assert all(result.call_id != original_call for result in agent.results)
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)
