"""Controller-side EndEvent closure races from product decision D3."""

import asyncio

import pytest

from accessflow.contracts import (
    EndEvent, Frame, FrameEvent, Observation, PlanProposal, ProposedCall,
    Start, StartEvent, ToolManifest, ToolResult, Transcript, TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakeTools, FinalFlagPolicy, MockOnlyAuthorization


def write_manifest():
    return ToolManifest(
        name="reserve",
        description="Reserve a time",
        effect="write",
        timeout_s=30,
        parameters={
            "type": "object",
            "properties": {"day": {"type": "string"}},
            "required": ["day"],
            "additionalProperties": False,
        },
    )


def write_plan():
    return PlanProposal(
        intent="reserve",
        slot_updates={"day": "Wednesday"},
        request_complete=True,
        write_requested=True,
        calls=[ProposedCall(tool="reserve", arguments={"day": "Wednesday"},
                            dependencies=["day"])],
    )


class GatedReasoner:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, view, manifests):
        self.started.set()
        await self.release.wait()
        return write_plan()


class GatedPerception:
    def __init__(self):
        self.started = asyncio.Queue()
        self.release = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def observe(self, event):
        await self.started.put(event)
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        yield Observation(event_id=event.event_id, source_id=event.payload.frame_id,
                          modality="image", final=True, text="unused", backend="gated-test")


class PendingExecutor:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancelled = []
        self.calls = []

    async def execute(self, call):
        self.calls.append(call)
        self.started.set()
        await self.release.wait()
        return ToolResult(call_id=call.call_id, status="success", committed=True,
                          result={"reserved": True})

    async def cancel(self, call_id):
        self.cancelled.append(call_id)
        return "cancelled_before_commit"


async def start_agent(reasoner, *, perception=None, executor=None):
    agent = Agent(perception or _ImmediatePerception(), FinalFlagPolicy(), reasoner,
                  executor=executor or FakeTools(), authorization=MockOnlyAuthorization(),
                  partial_debounce_s=0, frame_debounce_s=0)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(session_id="s", payload=Start(tools=[write_manifest()])))
    async with asyncio.timeout(2):
        while getattr(agent, "session_id", None) is None:
            await asyncio.sleep(0)
    return agent, incoming, outgoing, task


class _ImmediatePerception:
    async def observe(self, event):
        payload = event.payload
        if isinstance(event, FrameEvent):
            yield Observation(event_id=event.event_id, source_id=payload.frame_id,
                              modality="image", final=True, text="unused", backend="test")
        else:
            yield Observation(event_id=event.event_id, source_id=payload.utterance_id,
                              revision=payload.revision, modality="text", final=True,
                              text=payload.text, backend="test")


async def wait_for(queue, predicate):
    async with asyncio.timeout(2):
        while True:
            item = await queue.get()
            if predicate(item):
                return item


async def wait_until(predicate):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_end_admitted_before_late_plan_result_never_dispatches_write():
    reasoner = GatedReasoner()
    agent, incoming, outgoing, task = await start_agent(reasoner)
    await incoming.put(TranscriptEvent(session_id="s", payload=Transcript(
        utterance_id="u", revision=0, text="Reserve Wednesday", final=True)))
    await asyncio.wait_for(reasoner.started.wait(), 2)

    # Wait until the controller inbox has admitted EndEvent, then let the in-flight
    # planner return. Its result must not become a dispatched effect after closure.
    await incoming.put(EndEvent(session_id="s"))
    await wait_until(lambda: any(isinstance(event, EndEvent) for event in agent.inbox._queue))
    reasoner.release.set()
    await asyncio.wait_for(task, 2)

    assert not agent.executor.calls
    assert not any(event.kind in {"tool_call", "final", "clarify"}
                   for event in list(outgoing._queue))
    assert not agent.workers


@pytest.mark.asyncio
async def test_end_discards_pending_frame_and_cancels_perception_worker():
    perception = GatedPerception()
    agent, incoming, _outgoing, task = await start_agent(object(), perception=perception)
    frame = FrameEvent(session_id="s", payload=Frame(frame_id="frame-1", path="unused.png"))
    await incoming.put(frame)
    observed = await asyncio.wait_for(perception.started.get(), 2)
    assert observed.payload.frame_id == "frame-1"
    assert agent.pending_frame_token is not None

    await incoming.put(EndEvent(session_id="s"))
    await asyncio.wait_for(task, 2)

    assert agent.pending_frame_token is None
    assert await asyncio.wait_for(perception.cancelled.wait(), 1)
    assert not agent.perception_workers
    assert not agent.workers
    assert not agent.observations


@pytest.mark.asyncio
async def test_end_requests_cancellation_for_pending_external_write():
    executor = PendingExecutor()
    agent, incoming, outgoing, task = await start_agent(
        _ImmediateReasoner(), executor=executor)
    await incoming.put(TranscriptEvent(session_id="s", payload=Transcript(
        utterance_id="u", revision=0, text="Reserve Wednesday", final=True)))
    await asyncio.wait_for(executor.started.wait(), 2)
    call_id = executor.calls[0].call_id

    await incoming.put(EndEvent(session_id="s"))
    await asyncio.wait_for(task, 2)

    assert executor.cancelled == [call_id]
    assert agent.ledger[call_id].status == "cancelled"
    assert not any(event.kind == "final" for event in list(outgoing._queue))
    assert not agent.workers


class _ImmediateReasoner:
    async def plan(self, view, manifests):
        return write_plan()

