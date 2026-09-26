import asyncio

from accessflow.clock import ManualClock
from accessflow.contracts import (
    Frame, FrameEvent, Observation, PlanProposal, Start, StartEvent, TurnDecision,
)
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


async def test_older_utterance_result_does_not_trigger_a_new_write():
    release, returned = asyncio.Event(), asyncio.Event()

    class Perception:
        async def observe(self, event):
            if event.payload.utterance_id == "old":
                await release.wait()
            async for obs in FakePerception().observe(event):
                yield obs
            if event.payload.utterance_id == "old":
                returned.set()

    reasoner = ScriptedReasoner([PlanProposal(response="Current request understood"), proposal()])
    tools = FakeTools()
    agent = Agent(Perception(), FinalFlagPolicy(), reasoner, tools, MockOnlyAuthorization())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    try:
        await iq.put(StartEvent(session_id="s", payload=Start(tools=[manifest()])))
        await iq.put(transcript("Old booking", utterance="old"))
        await iq.put(transcript("Only explain the warranty", utterance="new"))
        await wait_for(oq, lambda e: e.kind == "final")
        release.set()
        await asyncio.wait_for(returned.wait(), 1)
        await end(iq, task)
        assert len(reasoner.views) == 1
        assert not tools.calls
    finally:
        release.set()
        if not task.done():
            await end(iq, task)


async def test_policy_cannot_change_controller_observation():
    class Policy:
        def update(self, observation, view):
            observation.text = "mutated"
            return TurnDecision(kind="complete")

    agent = Agent(FakePerception(), Policy(), ScriptedReasoner([PlanProposal(response="Noted")]), FakeTools())
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    try:
        await iq.put(StartEvent(session_id="s", payload=Start()))
        await iq.put(transcript("original"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert agent.observations[("speech", "u")].text == "original"
    finally:
        await end(iq, task)


async def test_distinct_new_frame_preserves_older_provisional_image_read():
    class Perception:
        async def observe(self, event):
            if event.kind == "frame":
                yield Observation(event_id=event.event_id, source_id=event.payload.frame_id,
                                  modality="image", text=event.payload.frame_id, final=True, backend="fake-image")
            else:
                async for obs in FakePerception().observe(event):
                    yield obs

    class Planner:
        async def plan(self, view, manifests):
            frame = [o for o in view.observations if o.modality == "image"]
            if frame and frame[-1].text == "f1":
                return PlanProposal(slot_updates={"device": "tentative-old-frame"},
                                    calls=[proposal().calls[0].model_copy(
                                        update={"arguments": {"day": "any"}, "dependencies": ["device"]})])
            return PlanProposal()

    agent = Agent(Perception(), FinalFlagPolicy(), Planner(), FakeTools(gate=asyncio.Event()),
                  partial_debounce_s=0)
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq))
    try:
        tool = manifest(effect="read")
        tool.parameters["properties"]["day"] = {"const": "any"}
        await iq.put(StartEvent(session_id="s", payload=Start(tools=[tool])))
        # Vision has completed, but the user's request is still provisional.
        # Incomplete image streams no longer enter authoritative planning.
        await iq.put(transcript("Look up this device while I explain...", final=False))
        await iq.put(FrameEvent(session_id="s", payload=Frame(path="scripted-only.png", frame_id="f1")))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        assert not agent.state.slots["device"].confirmed
        await iq.put(FrameEvent(session_id="s", payload=Frame(path="scripted-only.png", frame_id="f2")))
        await wait_for(oq, lambda e: e.kind == "acknowledge"
                       and e.payload.get("image_received", {}).get("frame_id") == "f2")
        # A second attachment does not replace Image 1 or cancel an unrelated
        # reversible lookup already grounded on it. Its provisional status still
        # prevents this value from authorizing a state-changing call.
        assert agent.state.slots["device"].value == "tentative-old-frame"
        assert not agent.state.slots["device"].confirmed
        assert agent.state.slot_image_sources["device"].image_reference == "Image 1"
        assert len(agent.image_registry.view()) == 2
        assert any(call.status == "pending" for call in agent.ledger.values())
    finally:
        await end(iq, task)


async def test_new_explicit_request_after_failure_has_new_operation():
    tools = FakeTools(outcome="failed")
    agent, iq, oq, task = await start([proposal(), proposal()], tools=tools)
    try:
        await iq.put(transcript("Book Wednesday", utterance="first"))
        await wait_for(oq, lambda e: e.payload.get("code") == "tool_failed")
        await iq.put(transcript("Make a new Wednesday request", utterance="second"))
        await wait_for(oq, lambda e: e.payload.get("code") == "tool_failed")
        assert len(tools.calls) == 2
        assert tools.calls[0].operation_id != tools.calls[1].operation_id
    finally:
        await end(iq, task)


async def test_partial_requests_coalesce_but_final_does_not_wait_for_debounce():
    reasoner = ScriptedReasoner([proposal()])
    agent, iq, oq, task = await start([], reasoner=reasoner, partial_debounce_s=10)
    try:
        for revision in range(4):
            await iq.put(transcript(f"partial {revision}", revision=revision, final=False))
        await iq.put(transcript("Book Wednesday", revision=4))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(reasoner.views) == 1
        assert reasoner.views[0].observations[-1].revision == 4
    finally:
        await end(iq, task)


async def test_timeout_before_session_start_exits_without_invalid_envelope():
    clock = ManualClock()
    agent = Agent(FakePerception(), FinalFlagPolicy(), ScriptedReasoner(), scenario_timeout=1)
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq, clock))
    for _ in range(5):
        await asyncio.sleep(0)
    clock.advance(2)
    await asyncio.wait_for(task, 1)
    assert oq.empty()
    assert not agent.running
