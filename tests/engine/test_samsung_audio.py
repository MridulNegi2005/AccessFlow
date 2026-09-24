"""Queue admission/ordering with explicitly fake codec and ASR evidence."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from accessflow.adapters.mp3_decode import DecodedTurn
from accessflow.adapters.samsung import ParticipantAgent, HarnessAuthorization
from accessflow.contracts import Observation, PlanProposal
from accessflow.engine import Agent
from accessflow.fakes import FinalFlagPolicy
from tests.engine.test_samsung_runtime import action, event


def chunk(ref="one.mp3", final=True, at=10):
    return event("user_audio_chunk", {"audio_ref": ref, "duration_ms": 100, "end_of_turn": final}, at)


class Codec:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.gates = []
        self.started = asyncio.Queue()
        self.closed = []
        self.failure = False
        self.ignore_cancel = False

    @asynccontextmanager
    async def convert(self, root, refs):
        index = len(self.calls)
        self.calls.append(refs)
        gate = asyncio.Event()
        self.gates.append(gate)
        await self.started.put(index)
        try:
            try:
                await gate.wait()
            except asyncio.CancelledError:
                if not self.ignore_cancel:
                    raise
                await gate.wait()
            if self.failure:
                raise RuntimeError("fake codec failure")
            path = self.root / f"decoded{index}.wav"
            path.write_bytes(b"explicit fake ASR fixture")
            try:
                yield DecodedTurn(path, 16000, 16, (16,))
            finally:
                path.unlink()
        finally:
            self.closed.append(index)


class Perception:
    def __init__(self):
        self.seen = []
        self.observed = asyncio.Queue()
        self.closed = False

    async def observe(self, event):
        self.seen.append(event)
        await self.observed.put(event)
        payload = event.payload
        image = event.kind == "frame"
        if event.kind == "audio":
            assert not self.closed
            assert Path(payload.path).exists()
        yield Observation(event_id=event.event_id, source_id=payload.frame_id if image else payload.utterance_id,
            revision=0 if image else payload.revision,
            modality="image" if image else ("text" if event.kind == "transcript" else "audio"),
            text="fixture image" if image else (payload.text if event.kind == "transcript" else "fixture audio"),
            final=getattr(payload, "final", True), backend="fake/queue-test")

    async def aclose(self):
        self.closed = True


class Reasoner:
    async def plan(self, view, manifests):
        return PlanProposal(request_complete=True, response=" | ".join(item.text for item in view.observations))


async def start(tmp_path):
    for name in ("one.mp3", "two.mp3", "image.png"):
        (tmp_path / name).write_bytes(b"fake codec/perception fixture")
    perception = Perception()

    async def factory():
        return Agent(perception, FinalFlagPolicy(), Reasoner(), authorization=HarnessAuthorization(),
                     partial_debounce_s=0, frame_debounce_s=0)

    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), agent_factory=factory, media_root=tmp_path)
    await participant.setup()
    codec = Codec(tmp_path)
    participant.audio_input.converter = codec.convert
    task = asyncio.create_task(participant.run())
    await participant.in_queue.put(event("tool_manifest", {"schema_version": "1.0", "tools": {}}))
    return participant, codec, perception, task


async def stop(participant, codec, task):
    for gate in codec.gates:
        gate.set()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert all(job.task.done() for job in participant.audio_input.jobs)
    assert not participant.tasks


async def test_multiclip_waits_for_final_keeps_frame_and_retains_wav_through_asr(tmp_path):
    participant, codec, perception, task = await start(tmp_path)
    try:
        await participant.in_queue.put(chunk(final=False))
        await action(participant.out_queue, "filler_speech")
        assert codec.calls == [] and perception.seen == []
        await participant.in_queue.put(event("video_frame", {"frame_id": "f", "image_ref": "image.png"}, 11))
        assert (await asyncio.wait_for(perception.observed.get(), 2)).kind == "frame"
        await participant.in_queue.put(chunk("two.mp3", at=20))
        await action(participant.out_queue, "filler_speech")
        assert await asyncio.wait_for(codec.started.get(), 2) == 0
        assert codec.calls == [("one.mp3", "two.mp3")]
        assert not any(item.kind == "audio" for item in perception.seen)
        codec.gates[0].set()
        final = await action(participant.out_queue, "final_response")
        assert "fixture image" in final["payload"]["text"] and "fixture audio" in final["payload"]["text"]
        audio = next(item for item in perception.seen if item.kind == "audio")
        assert audio.payload.revision == 2
        assert audio.timestamp == 0.02
        assert audio.payload.speech_start == audio.payload.speech_end == 0
        assert (tmp_path / "decoded0.wav").exists()
    finally:
        await stop(participant, codec, task)
    assert codec.closed == [0] and not (tmp_path / "decoded0.wav").exists()
    assert perception.closed


@pytest.mark.parametrize("kind", ["user_speech_chunk", "interruption"])
async def test_new_text_remains_responsive_and_rejects_late_cancel_ignoring_decode(tmp_path, kind):
    participant, codec, perception, task = await start(tmp_path)
    codec.ignore_cancel = True
    try:
        await participant.in_queue.put(chunk())
        await asyncio.wait_for(codec.started.get(), 2)
        await participant.in_queue.put(event(kind, {"text": "Describe the screen", "end_of_turn": True}, 30))
        final = await action(participant.out_queue, "final_response")
        assert final["payload"]["text"] == "Describe the screen"
        codec.gates[0].set()
        await asyncio.wait_for(participant.audio_input.jobs[0].task, 2)
        assert not any(item.kind == "audio" for item in perception.seen)
    finally:
        await stop(participant, codec, task)


@pytest.mark.parametrize("failure", ["missing", "codec", "missing_final"])
async def test_audio_failure_clarifies_without_a_fabricated_observation(tmp_path, failure):
    participant, codec, perception, task = await start(tmp_path)
    try:
        if failure == "missing":
            await participant.in_queue.put(chunk("missing.mp3"))
        elif failure == "codec":
            codec.failure = True
            await participant.in_queue.put(chunk())
            await asyncio.wait_for(codec.started.get(), 2)
            codec.gates[0].set()
        else:
            await participant.in_queue.put(chunk(final=False))
            await participant.in_queue.put(event("scenario_end", {}, 40))
        message = await action(participant.out_queue, "clarification_request")
        assert "recording" in message["payload"]["text"]
        assert not perception.seen
        assert not task.done()
    finally:
        await stop(participant, codec, task)


async def test_scenario_tail_allows_completed_turn_conversion_to_finish(tmp_path):
    participant, codec, perception, task = await start(tmp_path)
    try:
        await participant.in_queue.put(chunk())
        await asyncio.wait_for(codec.started.get(), 2)
        await participant.in_queue.put(event("scenario_end", {}, 15))
        codec.gates[0].set()
        final = await action(participant.out_queue, "final_response")
        assert final["payload"]["text"] == "fixture audio"
        assert not task.done()
    finally:
        await stop(participant, codec, task)


async def test_ready_conversion_gets_service_before_raw_backlog_drains(tmp_path):
    """Continuous valid input must not starve an already-ready decode."""
    async def factory():
        return Agent(Perception(), FinalFlagPolicy(), Reasoner(), authorization=HarnessAuthorization())

    participant = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), agent_factory=factory, media_root=tmp_path)
    await participant.setup()
    served = asyncio.Event()
    remaining = []

    async def deliver(outcome, incoming):
        remaining.append(participant.in_queue.qsize())
        served.set()

    participant.audio_input.deliver = deliver
    await participant.audio_input.completed.put(object())
    await participant.in_queue.put(event("tool_manifest", {"schema_version": "1.0", "tools": {}}))
    for index in range(100):
        await participant.in_queue.put(event("scenario_end", {}, index))
    task = asyncio.create_task(participant._pump_input(asyncio.Queue()))
    try:
        await asyncio.wait_for(served.wait(), 2)
        assert remaining[0] > 0
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await participant.audio_input.aclose()


@pytest.mark.parametrize("limit", ["clips", "turns", "pcm"])
async def test_audio_resource_limit_clarifies_without_asr(tmp_path, monkeypatch, limit):
    import accessflow.adapters.samsung_audio as bridge

    participant, codec, perception, task = await start(tmp_path)
    try:
        if limit == "clips":
            monkeypatch.setattr(bridge, "MAX_CLIPS", 1)
            await participant.in_queue.put(chunk(final=False))
            await participant.in_queue.put(chunk("two.mp3"))
        elif limit == "turns":
            participant.audio_input.turn_count = bridge.MAX_AUDIO_TURNS
            await participant.in_queue.put(chunk())
        else:
            participant.audio_input.pcm_bytes = bridge.MAX_SESSION_PCM_BYTES
            await participant.in_queue.put(chunk())
            await asyncio.wait_for(codec.started.get(), 2)
            codec.gates[0].set()
        await action(participant.out_queue, "clarification_request")
        assert not perception.seen and not task.done()
    finally:
        await stop(participant, codec, task)


@pytest.mark.parametrize("key,value", [("duration_ms", True), ("duration_ms", -1),
    ("duration_ms", float("nan")), ("duration_ms", 120001), ("end_of_turn", "true")])
async def test_invalid_audio_metadata_does_not_start_conversion(tmp_path, key, value):
    from accessflow.adapters.samsung_protocol import SamsungProtocolError

    participant, codec, perception, task = await start(tmp_path)
    try:
        # Wait until the initial manifest has passed the input pump.
        await participant.in_queue.put(event("user_speech_chunk", {"text": "hello", "end_of_turn": True}))
        await action(participant.out_queue, "final_response")
        raw = chunk()
        raw["payload"][key] = value
        with pytest.raises(SamsungProtocolError):
            await participant.audio_input.accept(raw, asyncio.Queue())
        assert not codec.calls and not participant.audio_input.jobs
    finally:
        await stop(participant, codec, task)
