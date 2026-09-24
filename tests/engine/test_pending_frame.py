"""Controller readiness across independently scheduled speech and frame perception."""

import asyncio

import pytest

from accessflow.clock import ManualClock
from accessflow.contracts import (
    Audio, AudioEvent, Frame, FrameEvent, Observation, PlanProposal, ProposedCall,
    Start, StartEvent, TranscriptEvent, Interrupt, InterruptEvent,
)
from accessflow.engine import Agent, WorkerMessage
from accessflow.fakes import FakeTools, FinalFlagPolicy, MockOnlyAuthorization
from test_safety import end, manifest, wait_for, transcript


class GatedPerception:
    def __init__(self):
        self.started = asyncio.Queue()
        self.release = {}
        self.fail = set()
        self.empty = set()
        self.overrides = {}
        self.partial = set()

    async def observe(self, event):
        frame = isinstance(event, FrameEvent)
        source = event.payload.frame_id if frame else event.payload.utterance_id
        if frame:
            gate = self.release.setdefault(source, asyncio.Event())
            await self.started.put(source)
            if source in self.partial:
                yield Observation(event_id=event.event_id, source_id=source,
                                  modality="image", final=False, text="tentative Tuesday",
                                  backend="offline/partial-image")
            await gate.wait()
            if source in self.fail:
                raise RuntimeError("Frame unavailable")
            if source in self.empty:
                return
        observation = Observation(event_id=event.event_id, source_id=source,
                          modality="image" if frame else "audio", final=True,
                          text=f"image {source}" if frame else "Book Wednesday", backend="offline/gated")
        if isinstance(event, TranscriptEvent):
            observation = observation.model_copy(update={
                "modality": "text", "text": event.payload.text,
                "final": event.payload.final, "revision": event.payload.revision,
            })
        yield observation.model_copy(update=self.overrides.get(source, {}))


class RecordingAgent(Agent):
    async def _worker(self, message):
        await super()._worker(message)
        await self.processed.put(message)

    async def _apply(self, proposal, source=None):
        await super()._apply(proposal, source)
        await self.applied.put(source)


class Planner:
    def __init__(self, kind):
        self.kind = kind
        self.views = []

    async def plan(self, view, manifests):
        self.views.append(view)
        if self.kind == "write":
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                request_complete=True, write_requested=True,
                                calls=[ProposedCall(tool="reserve", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])
        if self.kind == "read" and not view.calls:
            return PlanProposal(request_complete=True, slot_updates={"day": "Wednesday"}, calls=[ProposedCall(
                tool="lookup", arguments={"day": "Wednesday"}, dependencies=["day"])])
        return PlanProposal(request_complete=True, response=" | ".join(o.text for o in view.observations))


async def setup(kind="final", clock=None):
    perception, planner, tools = GatedPerception(), Planner(kind), FakeTools()
    agent = RecordingAgent(perception, FinalFlagPolicy(), planner, tools,
                           MockOnlyAuthorization(), partial_debounce_s=0, frame_debounce_s=0)
    agent.applied = asyncio.Queue()
    agent.processed = asyncio.Queue()
    iq, oq = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(iq, oq, clock))
    await iq.put(StartEvent(session_id="s", payload=Start(tools=[manifest(name="reserve"),
                                                               manifest("read", "lookup")])))
    return agent, iq, oq, task


def frame(name="f1"):
    return FrameEvent(session_id="s", payload=Frame(frame_id=name, path="unused.png"))


async def speech_after_pending_frame(agent, iq, image):
    await iq.put(image)
    assert await asyncio.wait_for(agent.perception.started.get(), 2) == image.payload.frame_id
    await iq.put(AudioEvent(session_id="s", payload=Audio(utterance_id="u", path="unused.wav")))
    assert await asyncio.wait_for(agent.applied.get(), 2) == ("speech", "u")


@pytest.mark.parametrize("kind", ["final", "write", "read"])
async def test_current_image_delays_final_and_write_but_allows_read_prefetch(kind):
    agent, iq, oq, task = await setup(kind)
    image = frame()
    try:
        await speech_after_pending_frame(agent, iq, image)
        if kind == "read":
            # Wait for the read-result continuation too: it cannot bypass readiness.
            await asyncio.wait_for(agent.applied.get(), 2)
        seen = []
        while not oq.empty():
            seen.append(oq.get_nowait())
        assert not any(e.kind == "final" for e in seen), "An unfinished frame is part of this request"
        assert not any(c.effect == "write" for c in agent.ledger.values())
        assert any(c.effect == "read" for c in agent.ledger.values()) == (kind == "read")
        agent.perception.release["f1"].set()
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert {o.modality for o in agent.reasoner.views[-1].observations} == {"audio", "image"}
        assert final.payload["caused_by_event_id"] == image.event_id
        if kind == "write":
            assert len(agent.executor.effects) == 1
        else:
            assert "image f1" in final.payload["text"]
    finally:
        await end(iq, task)


@pytest.mark.parametrize("kind", ["final", "write"])
async def test_current_frame_failure_requires_new_input_before_resuming(kind):
    agent, iq, oq, task = await setup(kind)
    agent.perception.fail.add("f1")
    try:
        await speech_after_pending_frame(agent, iq, frame())
        while not oq.empty():
            oq.get_nowait()
        agent.perception.release["f1"].set()
        error = await wait_for(oq, lambda e: e.kind == "error")
        assert error.payload["code"] == "backend_failure"
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert not agent.latest_complete
        assert not agent.executor.effects
        assert not any(c.effect == "write" for c in agent.ledger.values())
        await iq.put(transcript("Book Wednesday without the image", revision=1))
        final = await wait_for(oq, lambda e: e.kind == "final")
        if kind == "write":
            assert len(agent.executor.effects) == 1
        else:
            assert final.payload["text"] == "Book Wednesday without the image"
    finally:
        await end(iq, task)


@pytest.mark.parametrize("mode", ["empty", "partial", "wrong_revision"])
async def test_frame_without_admissible_final_reports_failure_instead_of_hanging(mode):
    agent, iq, oq, task = await setup()
    if mode == "empty":
        agent.perception.empty.add("f1")
    else:
        agent.perception.overrides["f1"] = {"final": False} if mode == "partial" else {"revision": 1}
    try:
        await speech_after_pending_frame(agent, iq, frame())
        agent.perception.release["f1"].set()
        await wait_for(oq, lambda e: e.kind == "error" and e.payload["code"] == "backend_failure")
        assert agent.pending_frame_token is None
        assert ("image", "f1") not in agent.observations
        assert not agent.latest_complete
    finally:
        await end(iq, task)


async def processed(agent, wanted):
    async with asyncio.timeout(2):
        while await agent.processed.get() is not wanted:
            pass


@pytest.mark.parametrize("late_kind", ["observation", "frame_failure"])
async def test_replaced_frame_cannot_release_new_frame_gate(late_kind):
    agent, iq, oq, task = await setup("write")
    first, second = frame(), frame("f2")
    try:
        await speech_after_pending_frame(agent, iq, first)
        epoch = agent.perception_epoch
        await iq.put(second)
        assert await asyncio.wait_for(agent.perception.started.get(), 2) == "f2"
        token = agent.pending_frame_token
        value = (Observation(event_id=first.event_id, source_id="f1", modality="image",
                             text="obsolete image", final=True, backend="offline/late")
                 if late_kind == "observation" else "RuntimeError")
        late = WorkerMessage(late_kind, agent.generation, value, epoch,
                             source=("image", "f1"), perception_event_id=first.event_id)
        await agent.inbox.put(late)
        await processed(agent, late)
        assert agent.pending_frame_token == token
        assert not agent.executor.effects
        assert ("image", "f1") not in agent.observations
        agent.perception.release["f2"].set()
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("scope", ["speech", "task"])
async def test_interrupt_clears_frame_gate_and_rejects_late_failure(scope):
    agent, iq, oq, task = await setup()
    first = frame()
    try:
        await speech_after_pending_frame(agent, iq, first)
        epoch = agent.perception_epoch
        signal = InterruptEvent(session_id="s", payload=Interrupt(scope=scope))
        await iq.put(signal)
        await wait_for(oq, lambda e: e.kind == "acknowledge" and e.payload.get("stop_output"))
        assert agent.pending_frame_token is None
        late = WorkerMessage("frame_failure", agent.generation, "RuntimeError", epoch,
                             source=("image", "f1"), perception_event_id=first.event_id)
        await agent.inbox.put(late)
        await processed(agent, late)
        assert oq.empty()
        await iq.put(transcript("A fresh question", utterance="u2"))
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert "A fresh question" in final.payload["text"]
    finally:
        await end(iq, task)


async def test_completed_image_does_not_finish_partial_speech_or_authorize_write():
    agent, iq, oq, task = await setup("write")
    try:
        await iq.put(frame())
        await asyncio.wait_for(agent.perception.started.get(), 2)
        await iq.put(transcript("Book Wed...", final=False))
        await asyncio.wait_for(agent.applied.get(), 2)
        agent.perception.release["f1"].set()
        await asyncio.wait_for(agent.applied.get(), 2)
        assert agent.pending_frame_token is None
        assert not agent.speech_ready
        assert not agent.executor.effects
        assert not any(c.effect == "write" for c in agent.ledger.values())
        await iq.put(transcript(revision=1))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("outcome", ["failure", "interrupt"])
async def test_partial_frame_never_enters_planning_and_is_not_retained_after_loss(outcome):
    agent, iq, oq, task = await setup("write")
    agent.perception.partial.add("f1")
    agent.perception.fail.add("f1")
    image = frame()
    try:
        await speech_after_pending_frame(agent, iq, image)
        assert all(o.modality != "image" for v in agent.reasoner.views for o in v.observations)
        assert ("image", "f1") not in agent.observations
        if outcome == "failure":
            agent.perception.release["f1"].set()
            await wait_for(oq, lambda e: e.kind == "clarify")
        else:
            await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="speech")))
            await wait_for(oq, lambda e: e.kind == "acknowledge" and e.payload.get("stop_output"))
        assert not agent.executor.effects
        assert ("image", "f1") not in agent.observations
        late = WorkerMessage("observation", agent.generation,
                             Observation(event_id=image.event_id, source_id="f1", modality="image",
                                         text="late Tuesday", final=True, backend="offline/late"),
                             agent.perception_epoch)
        await agent.inbox.put(late)
        await processed(agent, late)
        assert ("image", "f1") not in agent.observations
        assert not agent.executor.effects
    finally:
        await end(iq, task)


async def test_successful_image_retry_resumes_retained_spoken_authority():
    agent, iq, oq, task = await setup("write")
    agent.perception.fail.add("f1")
    try:
        await speech_after_pending_frame(agent, iq, frame())
        agent.perception.release["f1"].set()
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert agent.speech_ready
        assert not agent.latest_complete
        await iq.put(frame("retry"))
        assert await asyncio.wait_for(agent.perception.started.get(), 2) == "retry"
        agent.perception.release["retry"].set()
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 1
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_late_read_result_cannot_finish_request_after_image_failure():
    agent, iq, oq, task = await setup("read")
    agent.executor.gate = asyncio.Event()
    agent.perception.fail.add("f1")
    try:
        await speech_after_pending_frame(agent, iq, frame())
        agent.perception.release["f1"].set()
        await wait_for(oq, lambda e: e.kind == "clarify")
        agent.executor.gate.set()
        await asyncio.wait_for(agent.applied.get(), 2)
        assert not agent.latest_complete
        assert not agent.last_request_finished
        remaining = []
        while not oq.empty():
            remaining.append(oq.get_nowait())
        assert remaining
        assert all(e.kind == "acknowledge" and e.payload.get("basis") == "tool_evidence"
                   for e in remaining)
        await iq.put(transcript("Continue without the image", revision=1))
        await wait_for(oq, lambda e: e.kind == "final")
    finally:
        agent.executor.gate.set()
        await end(iq, task)


async def test_frame_timeout_is_bounded_and_new_frame_can_recover():
    class ObservedClock(ManualClock):
        def __init__(self):
            super().__init__()
            self.frame_timer = asyncio.Event()

        async def sleep(self, seconds):
            if seconds == 5:
                self.frame_timer.set()
            await super().sleep(seconds)

    clock = ObservedClock()
    agent, iq, oq, task = await setup(clock=clock)
    agent.inference_timeout = 5
    try:
        await iq.put(frame())
        await asyncio.wait_for(agent.perception.started.get(), 2)
        await asyncio.wait_for(clock.frame_timer.wait(), 2)
        clock.advance(5)
        error = await wait_for(oq, lambda e: e.kind == "error")
        assert error.payload["code"] == "backend_failure"
        assert error.payload["detail"] == "TimeoutError"
        assert agent.pending_frame_token is None
        await iq.put(frame("recovered"))
        assert await asyncio.wait_for(agent.perception.started.get(), 2) == "recovered"
        agent.perception.release["recovered"].set()
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["text"] == "image recovered"
    finally:
        await end(iq, task)


async def test_session_end_discards_pending_frame_and_finishes_workers():
    agent, iq, oq, task = await setup()
    await iq.put(frame())
    await asyncio.wait_for(agent.perception.started.get(), 2)
    await end(iq, task)
    assert agent.pending_frame_token is None
    assert not agent.running
    assert all(worker.done() for worker in agent.workers)
