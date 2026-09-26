"""Controller-level D4 acceptance checks using deterministic offline doubles.

These tests establish source identity, ordering, and write guards at the Agent
boundary. Fake perception and tools are contract fixtures, not live model evidence.
"""

import asyncio

import pytest

from accessflow.contracts import (
    EndEvent,
    Frame,
    FrameEvent,
    ImageSlotBinding,
    Observation,
    PlanProposal,
    ProposedCall,
    Start,
    StartEvent,
    ToolManifest,
    Transcript,
    TranscriptEvent,
)
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FakeTools, FinalFlagPolicy, MockOnlyAuthorization


RESERVATION = ToolManifest(
    name="reserve",
    description="Reserve a service using the selected date and address.",
    effect="write",
    parameters={
        "type": "object",
        "properties": {"date": {"type": "string"}, "address": {"type": "string"}},
        "required": ["date", "address"],
        "additionalProperties": False,
    },
)


def frame(frame_id, *, session="session", event_id=None, timestamp=0):
    return FrameEvent(
        session_id=session,
        event_id=event_id or f"event-{frame_id}",
        timestamp=timestamp,
        payload=Frame(path=f"{frame_id}.png", frame_id=frame_id),
    )


def transcript(text, *, session="session", utterance="request"):
    return TranscriptEvent(
        session_id=session,
        event_id=f"speech-event-{utterance}",
        payload=Transcript(utterance_id=utterance, revision=0, text=text, final=True),
    )


def image_observation(event, text):
    return Observation(
        event_id=event.event_id,
        source_id=event.payload.frame_id,
        revision=0,
        modality="image",
        text=text,
        final=True,
        backend="fixture/offline-image",
    )


def image_binding(reference, event_id, quote, revision=0):
    return ImageSlotBinding(
        image_reference=reference,
        event_id=event_id,
        processing_revision=revision,
        evidence_quote=quote,
    )


def write_proposal(date_binding, address_binding, *, date="2026-10-01", address="17 Main Street"):
    return PlanProposal(
        intent="reservation",
        slot_updates={"date": date, "address": address},
        request_complete=True,
        write_requested=True,
        image_bindings={"date": date_binding, "address": address_binding},
        calls=[ProposedCall(
            tool="reserve",
            arguments={"date": date, "address": address},
            dependencies=["date", "address"],
        )],
    )


class DelayedFakePerception(FakePerception):
    """FakePerception with explicit gates for deterministic completion ordering."""

    def __init__(self, captions):
        super().__init__()
        self.captions = captions
        self.started = asyncio.Queue()
        self.release = {frame_id: asyncio.Event() for frame_id in captions}

    async def observe(self, event):
        if isinstance(event, FrameEvent):
            frame_id = event.payload.frame_id
            await self.started.put(frame_id)
            await self.release[frame_id].wait()
            yield image_observation(event, self.captions[frame_id])
            return
        async for observation in super().observe(event):
            yield observation


class CaptionFakePerception(FakePerception):
    """Immediate fixture captions for admission and session-isolation cases."""

    async def observe(self, event):
        if isinstance(event, FrameEvent):
            yield image_observation(event, f"caption for {event.payload.frame_id}")
            return
        async for observation in super().observe(event):
            yield observation


class TypedImageReasoner:
    def __init__(self, proposal_for_speech=None, *, proposal_for_third_image=None):
        self.proposal_for_speech = proposal_for_speech
        self.proposal_for_third_image = proposal_for_third_image
        self.views = []

    async def plan(self, view, manifests):
        self.views.append(view.model_copy(deep=True))
        if (self.proposal_for_third_image is not None and len(view.image_history) >= 3
                and view.image_history[-1].status == "observed"):
            return self.proposal_for_third_image
        if any(o.modality in {"text", "audio"} and o.final for o in view.observations):
            if self.proposal_for_speech is not None:
                return self.proposal_for_speech
        return PlanProposal()


async def wait_for(output, predicate):
    async with asyncio.timeout(3):
        while True:
            event = await output.get()
            if predicate(event):
                return event


async def start_agent(*, perception=None, reasoner=None, tools=None, session="session", manifests=None):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    agent = Agent(
        perception or CaptionFakePerception(),
        FinalFlagPolicy(),
        reasoner or TypedImageReasoner(),
        tools or FakeTools(),
        MockOnlyAuthorization(),
        partial_debounce_s=0,
        frame_debounce_s=0,
    )
    task = asyncio.create_task(agent.run(incoming, outgoing))
    await incoming.put(StartEvent(
        session_id=session,
        payload=Start(tools=list(manifests or [])),
    ))
    return agent, incoming, outgoing, task


async def stop_agent(incoming, task, session="session"):
    await incoming.put(EndEvent(session_id=session))
    await asyncio.wait_for(task, 3)


async def accept_frame(incoming, outgoing, event):
    await incoming.put(event)
    ack = await wait_for(outgoing, lambda item: item.kind == "acknowledge"
                         and item.payload.get("image_received", {}).get("event_id") == event.event_id)
    return ack.payload["image_received"]


async def two_accepted_images(*, reasoner=None, perception=None, tools=None):
    agent, incoming, outgoing, task = await start_agent(
        perception=perception, reasoner=reasoner, tools=tools, manifests=[RESERVATION],
    )
    first, second = frame("image-a"), frame("image-b")
    first_receipt = await accept_frame(incoming, outgoing, first)
    second_receipt = await accept_frame(incoming, outgoing, second)
    return agent, incoming, outgoing, task, first, second, first_receipt, second_receipt


async def test_two_images_keep_admission_order_when_latest_finishes_first_and_bind_one_write():
    captions = {"image-a": "Date shown: 2026-10-01", "image-b": "Address shown: 17 Main Street"}
    perception = DelayedFakePerception(captions)
    tools = FakeTools()
    reasoner = TypedImageReasoner()
    agent, incoming, outgoing, task, first, second, first_receipt, second_receipt = (
        await two_accepted_images(reasoner=reasoner, perception=perception, tools=tools)
    )
    try:
        assert await perception.started.get() == "image-a"
        assert await perception.started.get() == "image-b"

        # Image 2 is the latest accepted image, but its result completes first.
        perception.release["image-b"].set()
        async with asyncio.timeout(3):
            while not any(view.image_history[1].status == "observed" for view in reasoner.views
                          if len(view.image_history) == 2):
                await asyncio.sleep(0)

        perception.release["image-a"].set()
        async with asyncio.timeout(3):
            while not any(
                len(view.image_history) == 2
                and [image.status for image in view.image_history] == ["observed", "observed"]
                for view in reasoner.views
            ):
                await asyncio.sleep(0)

        request = transcript("Use the date from the first image and address from the second image to reserve.")
        reasoner.proposal_for_speech = write_proposal(
            image_binding("Image 1", first.event_id, "2026-10-01"),
            image_binding("Image 2", second.event_id, "17 Main Street"),
        )
        await incoming.put(request)
        final = await wait_for(outgoing, lambda item: item.kind == "final")

        assert [(image.ordinal, image.frame_id, image.status) for image in reasoner.views[-1].image_history] == [
            (1, "image-a", "observed"), (2, "image-b", "observed")
        ]
        assert reasoner.views[-1].image_history[0].observation.text == captions["image-a"]
        assert reasoner.views[-1].image_history[1].observation.text == captions["image-b"]
        assert first_receipt["ordinal"] == 1 and second_receipt["ordinal"] == 2
        assert agent.state.slot_image_sources["date"].image_reference == "Image 1"
        assert agent.state.slot_image_sources["address"].image_reference == "Image 2"
        assert final.kind == "final"
        assert len(tools.effects) == 1
        assert len(tools.calls) == 1
        assert tools.calls[0].arguments == {"date": "2026-10-01", "address": "17 Main Street"}
    finally:
        await stop_agent(incoming, task)


@pytest.mark.parametrize("fault", ["quote", "event", "revision", "ambiguous_old"])
async def test_invalid_image_binding_or_ambiguous_old_reference_never_writes(fault):
    captions = {"image-a": "Date: 2026-10-01", "image-b": "Address: 17 Main Street"}
    if fault == "ambiguous_old":
        captions["image-c"] = "More details: side entrance"
    perception = DelayedFakePerception(captions)
    tools = FakeTools()
    agent, incoming, outgoing, task, first, second, *_ = await two_accepted_images(
        reasoner=TypedImageReasoner(), perception=perception, tools=tools,
    )
    try:
        for frame_id in ("image-a", "image-b"):
            assert await perception.started.get() == frame_id
            perception.release[frame_id].set()
        async with asyncio.timeout(3):
            while not agent.image_registry or any(record.status != "observed" for record in agent.image_registry.view()):
                await asyncio.sleep(0)

        address_binding = image_binding("Image 2", second.event_id, "17 Main Street")
        date_binding = image_binding("Image 1", first.event_id, "2026-10-01")
        if fault == "quote":
            date_binding = image_binding("Image 1", first.event_id, "2026-10-02")
        elif fault == "event":
            date_binding = image_binding("Image 1", "unrelated-event", "2026-10-01")
        elif fault == "revision":
            date_binding = image_binding("Image 1", first.event_id, "2026-10-01", revision=1)
        elif fault == "ambiguous_old":
            third = frame("image-c")
            await accept_frame(incoming, outgoing, third)
            assert await perception.started.get() == "image-c"
            perception.release["image-c"].set()
            async with asyncio.timeout(3):
                while agent.image_registry.resolve(3).status != "observed":
                    await asyncio.sleep(0)
            date_binding = ImageSlotBinding.model_construct(
                image_reference="old image", event_id=first.event_id,
                processing_revision=0, evidence_quote="2026-10-01",
            )

        proposal_date_binding = (image_binding("Image 1", first.event_id, "2026-10-01")
                                 if fault == "ambiguous_old" else date_binding)
        bad_plan = write_proposal(proposal_date_binding, address_binding)
        if fault == "ambiguous_old":
            # Model-boundary validation normally rejects this contextual reference;
            # model_copy lets this test prove the controller also rejects a custom
            # reasoner that returns an unvalidated proposal.
            bad_plan = bad_plan.model_copy(update={
                "image_bindings": {"date": date_binding, "address": address_binding},
            })
        reasoner = agent.reasoner
        reasoner.proposal_for_speech = bad_plan
        request_text = ("Use the date from the old image and address from the second image to reserve."
                        if fault == "ambiguous_old" else
                        "Use the date from the first image and address from the second image to reserve.")
        await incoming.put(transcript(request_text))
        await wait_for(outgoing, lambda item: item.kind == "error" and
                       item.payload.get("code") == "invalid_image_binding")

        assert not tools.calls
        assert not tools.effects
        assert "date" not in agent.state.slots
    finally:
        await stop_agent(incoming, task)


async def test_third_image_cannot_silently_rebind_existing_image_derived_field():
    captions = {
        "image-a": "Date: 2026-10-01",
        "image-b": "Address: 17 Main Street",
        "image-c": "Date: 2026-11-02",
    }
    perception = DelayedFakePerception(captions)
    tools = FakeTools()
    reasoner = TypedImageReasoner()
    agent, incoming, outgoing, task, first, second, *_ = await two_accepted_images(
        reasoner=reasoner, perception=perception, tools=tools,
    )
    try:
        for frame_id in ("image-a", "image-b"):
            assert await perception.started.get() == frame_id
            perception.release[frame_id].set()
        async with asyncio.timeout(3):
            while any(record.status != "observed" for record in agent.image_registry.view()):
                await asyncio.sleep(0)

        reasoner.proposal_for_speech = write_proposal(
            image_binding("Image 1", first.event_id, "2026-10-01"),
            image_binding("Image 2", second.event_id, "17 Main Street"),
        )
        await incoming.put(transcript("Use the date from image 1 and address from image 2 to reserve."))
        await wait_for(outgoing, lambda item: item.kind == "final")
        original_date_source = agent.state.slot_image_sources["date"].model_copy(deep=True)

        reasoner.proposal_for_third_image = PlanProposal(
            intent="reservation", slot_updates={"date": "2026-11-02"}, request_complete=True,
        )
        third = frame("image-c")
        await accept_frame(incoming, outgoing, third)
        assert await perception.started.get() == "image-c"
        perception.release["image-c"].set()
        await wait_for(outgoing, lambda item: item.kind == "error" and
                       item.payload.get("code") == "invalid_image_binding")

        assert agent.state.slots["date"].value == "2026-10-01"
        assert agent.state.slot_image_sources["date"] == original_date_source
        assert agent.image_registry.resolve(3).ordinal == 3
        assert agent.image_registry.resolve(3).observation.text == captions["image-c"]
        assert len(tools.effects) == 1
        assert len(tools.calls) == 1
    finally:
        await stop_agent(incoming, task)


async def test_unqualified_image_reference_defaults_to_newest_accepted_source():
    perception = DelayedFakePerception({
        "image-a": "Date: 2026-10-01", "image-b": "Date: 2026-10-02",
    })
    reasoner = TypedImageReasoner()
    agent, incoming, outgoing, task, first, second, *_ = await two_accepted_images(
        reasoner=reasoner, perception=perception,
    )
    try:
        for frame_id in ("image-a", "image-b"):
            assert await perception.started.get() == frame_id
            perception.release[frame_id].set()
        async with asyncio.timeout(3):
            while any(record.status != "observed" for record in agent.image_registry.view()):
                await asyncio.sleep(0)

        reasoner.proposal_for_speech = PlanProposal(
            slot_updates={"date": "2026-10-01"},
            image_bindings={"date": image_binding("Image 1", first.event_id, "2026-10-01")},
            request_complete=True,
        )
        await incoming.put(transcript("Use the image date to prepare my request."))
        await wait_for(outgoing, lambda item: item.kind == "error" and
                       item.payload.get("code") == "invalid_image_binding")
        assert "date" not in agent.state.slots

        # A specifically named source remains addressable after the clarification.
        reasoner.proposal_for_speech = PlanProposal(
            slot_updates={"date": "2026-10-01"},
            image_bindings={"date": image_binding("Image 1", first.event_id, "2026-10-01")},
            request_complete=True,
        )
        await incoming.put(transcript("Use the date from Image 1.", utterance="specific"))
        async with asyncio.timeout(3):
            while "date" not in agent.state.slots:
                await asyncio.sleep(0)
        assert agent.state.slot_image_sources["date"].image_reference == "Image 1"
        assert agent.image_registry.resolve(2).event_id == second.event_id
    finally:
        await stop_agent(incoming, task)


async def test_ninth_image_is_rejected_without_reindexing_the_eight_accepted_images():
    agent, incoming, outgoing, task = await start_agent()
    try:
        receipts = []
        for index in range(1, 9):
            event = frame(f"image-{index}")
            receipts.append(await accept_frame(incoming, outgoing, event))
        rejected = frame("image-9")
        await incoming.put(rejected)
        await wait_for(outgoing, lambda item: item.kind == "error" and
                       item.payload.get("code") == "image_admission_rejected")

        assert [receipt["ordinal"] for receipt in receipts] == list(range(1, 9))
        assert [(record.ordinal, record.frame_id) for record in agent.image_registry.view()] == [
            (index, f"image-{index}") for index in range(1, 9)
        ]
    finally:
        await stop_agent(incoming, task)


async def test_new_session_starts_with_empty_image_registry():
    first, incoming1, outgoing1, task1 = await start_agent(session="session-one")
    try:
        event = frame("reused-frame-id", session="session-one", event_id="session-one-event")
        await accept_frame(incoming1, outgoing1, event)
        async with asyncio.timeout(3):
            while first.image_registry.resolve("reused-frame-id").status != "observed":
                await asyncio.sleep(0)
        await stop_agent(incoming1, task1, "session-one")
    finally:
        if not task1.done():
            await stop_agent(incoming1, task1, "session-one")

    second, incoming2, outgoing2, task2 = await start_agent(session="session-two")
    try:
        event = frame("reused-frame-id", session="session-two", event_id="session-two-event")
        receipt = await accept_frame(incoming2, outgoing2, event)
        assert receipt["ordinal"] == 1
        assert second.image_registry.session_id == "session-two"
        assert [(record.frame_id, record.ordinal) for record in second.image_registry.view()] == [
            ("reused-frame-id", 1)
        ]
        assert first.image_registry.view()[0].session_id == "session-one"
    finally:
        await stop_agent(incoming2, task2, "session-two")
