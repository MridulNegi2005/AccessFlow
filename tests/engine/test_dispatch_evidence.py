import asyncio

from accessflow.contracts import (Interrupt, InterruptEvent, PlanProposal, ProposedCall, Start,
                                  StartEvent)
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


async def test_repeating_a_completed_read_reports_the_stall_and_replans_once():
    class Looping:
        def __init__(self):
            self.views = []

        async def plan(self, view, manifests):
            self.views.append(view)
            # Always re-propose the same read, which the controller drops as already done.
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                calls=[ProposedCall(tool="arbitrary_service",
                                                    arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    planner = Looping()
    agent, iq, oq, task = await start([], reasoner=planner, manifests=[manifest(effect="read")],
                                      tools=FakeTools())
    try:
        await iq.put(transcript("Check Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "repeated_completed_call")
        # The retry is bounded, so the loop stops instead of replanning forever.
        assert agent.repeat_recoveries[agent.request_id] == 1
        async with asyncio.timeout(2):
            while not any(view.repeated_completed_call for view in planner.views):
                await asyncio.sleep(0.01)
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)
