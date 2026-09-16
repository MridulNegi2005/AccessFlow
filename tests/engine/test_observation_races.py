import asyncio

import pytest

from accessflow.contracts import (
    EndEvent, Interrupt, InterruptEvent, Observation, PlanProposal, Start, StartEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


@pytest.mark.parametrize("scope", ["speech", "task"])
async def test_delayed_perception_cannot_restart_after_interrupt(scope):
    entered, release, returned, cancelled = (asyncio.Event() for _ in range(4))

    class Delayed:
        async def observe(self, event):
            entered.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                # Simulate a native callback that still returns after cancellation;
                # requesting cancellation does not replace the stale-result gate.
                cancelled.set()
                await release.wait()
            async for obs in FakePerception().observe(event):
                yield obs
            returned.set()

    executor = FakeTools()
    reasoner = ScriptedReasoner([proposal()])
    agent = Agent(Delayed(), FinalFlagPolicy(), reasoner, executor, MockOnlyAuthorization())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    try:
        await iq.put(StartEvent(session_id="s", payload=Start(tools=[manifest()])))
        await iq.put(transcript())
        await asyncio.wait_for(entered.wait(), 1)
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope=scope)))
        await wait_for(oq, lambda e: e.payload.get("stop_output"))
        await asyncio.wait_for(cancelled.wait(), 1)
        release.set()
        await asyncio.wait_for(returned.wait(), 1)
        # Drain the controller through a subsequent output barrier.
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope=scope)))
        await wait_for(oq, lambda e: e.payload.get("stop_output"))
        assert not executor.calls
        assert not reasoner.views
        assert not agent.latest_complete
    finally:
        release.set()
        await end(iq, task)


async def test_removed_partial_slot_does_not_survive_final_revision():
    seen = asyncio.Queue()

    class Planner:
        async def plan(self, view, manifests):
            seen.put_nowait(view)
            if not view.observations[-1].final:
                return PlanProposal(slot_updates={"day": "Tuesday", "device": "old-phone"},
                                    calls=[proposal("Tuesday").calls[0]])
            return PlanProposal(slot_updates={"day": "Wednesday"}, response="Which device?")

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[manifest(effect="read")],
                                     tools=FakeTools(gate=asyncio.Event()))
    try:
        await iq.put(transcript("Tuesday for the old phone", final=False))
        partial = await wait_for(oq, lambda e: e.kind == "tool_call")
        assert partial.state.slots["device"].value == "old-phone"
        await iq.put(transcript("Actually Wednesday; I have not picked a device", revision=1))
        event = await wait_for(oq, lambda e: e.kind == "final")
        assert "device" not in event.state.slots
        assert event.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_partial_replacement_restores_prior_confirmed_slot():
    class Planner:
        async def plan(self, view, manifests):
            text = view.observations[-1].text
            if text == "confirmed":
                return PlanProposal(slot_updates={"device": "phone"}, response="Noted")
            if text == "partial":
                return PlanProposal(slot_updates={"device": "tablet"}, calls=[
                    proposal(name="arbitrary_service").calls[0].model_copy(
                        update={"arguments": {"day": "any"}, "dependencies": ["device"]})])
            return PlanProposal(response="Noted")

    tool = manifest(effect="read")
    tool.parameters["properties"]["day"] = {"const": "any"}
    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[tool],
                                     tools=FakeTools(gate=asyncio.Event()))
    try:
        await iq.put(transcript("confirmed"))
        await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(transcript("partial", utterance="u2", final=False))
        partial = await wait_for(oq, lambda e: e.kind == "tool_call")
        assert partial.state.slots["device"].value == "tablet"
        await iq.put(transcript("never mind that tentative device", utterance="u2", revision=1))
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.state.slots["device"].value == "phone"
        assert final.state.slots["device"].confirmed
    finally:
        await end(iq, task)


async def test_reasoner_cannot_mutate_controller_observations_or_manifests():
    class MutatingPlanner:
        async def plan(self, view, manifests):
            view.observations[0].text = "mutated"
            manifests[0].effect = "read"
            return proposal()

    agent, iq, oq, task = await start([], reasoner=MutatingPlanner(), auth=False)
    try:
        await iq.put(transcript("Book Wednesday"))
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert list(agent.observations.values())[0].text == "Book Wednesday"
        assert agent.manifests["arbitrary_service"].effect == "write"
        assert not agent.executor.calls
    finally:
        await end(iq, task)


async def test_reusing_agent_clears_session_state():
    agent = Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner([PlanProposal(
        slot_updates={"device": "private device"}, response="Noted")]), FakeTools())
    for session in ["first", "second"]:
        iq, oq = asyncio.Queue(), asyncio.Queue()
        task = asyncio.create_task(agent.run(iq, oq))
        await iq.put(StartEvent(session_id=session, payload=Start()))
        if session == "first":
            await iq.put(transcript().model_copy(update={"session_id": session}))
            await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(EndEvent(session_id=session))
        await asyncio.wait_for(task, 1)
        if session == "second":
            assert not agent.state.slots
            assert not agent.observations
            assert not agent.ledger


async def test_observation_must_identify_actual_originating_event():
    class WrongOrigin:
        async def observe(self, event):
            yield Observation(event_id="made-up-origin", source_id=event.payload.utterance_id,
                              revision=event.payload.revision, modality="text", text="Book Wednesday",
                              final=True, backend="test")

    agent = Agent(WrongOrigin(), FinalFlagPolicy(), ScriptedReasoner([proposal()]),
                  FakeTools(), MockOnlyAuthorization())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    await iq.put(StartEvent(session_id="s", payload=Start(tools=[manifest()])))
    await iq.put(transcript())
    for _ in range(15):
        await asyncio.sleep(0)
    await end(iq, task)
    assert not agent.executor.calls
