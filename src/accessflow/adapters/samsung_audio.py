"""Samsung's explicit end_of_turn to complete-WAV bridge, owned by the adapter.

Workers only publish conversion outcomes. The input pump admits them in order,
checks their generation, and then lets the controller own all conversation state.
"""

import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from .mp3_decode import decode_mp3_turn, MAX_CLIPS

MAX_AUDIO_TURNS = 32
MAX_SESSION_PCM_BYTES = 16 * 1024 * 1024


@dataclass
class Conversion:
    utterance: str
    timestamp: float
    generation: int
    ready: bool = False
    admitted: bool = False
    release: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task | None = None


class SamsungAudioInput:
    def __init__(self, protocol, converter=decode_mp3_turn):
        self.protocol = protocol
        self.converter = converter
        self.completed = asyncio.Queue(maxsize=MAX_AUDIO_TURNS)
        self.generation = 0
        self.utterance = None
        self.references = []
        self.timestamp = 0.0
        self.jobs = []
        self.turn_count = 0
        self.pcm_bytes = 0
        self.closed = False

    def invalidate(self):
        self.generation += 1
        self.utterance = None
        self.references = []
        for job in self.jobs:
            if job.task is not None and not job.ready and not job.task.done():
                job.task.cancel()
            elif job.ready and not job.admitted:
                job.release.set()

    async def accept(self, raw, incoming):
        """Runs only in the input pump. No decoding/ASR is awaited here."""
        chunk = self.protocol.admit_audio_chunk(raw)
        if self.closed:
            raise RuntimeError("Audio input is closed")
        if self.utterance is None:
            self.invalidate()
            self.turn_count += 1
            self.utterance = "samsung-audio-" + str(uuid4())
            self.timestamp = chunk["timestamp"]
            await incoming.put(self.protocol.audio_status(self.utterance, 0, self.timestamp))
        self.timestamp = chunk["timestamp"]
        self.references.append(chunk["ref"])
        if self.turn_count > MAX_AUDIO_TURNS or len(self.references) > MAX_CLIPS:
            await self.fail(incoming)
            return
        if not chunk["final"]:
            return
        if len(self.references) > 1:
            # The final clip has its own official response-latency window. A
            # transport acknowledgment is possible before decoding the full turn.
            await incoming.put(self.protocol.audio_status(self.utterance, 1, self.timestamp))
        job = Conversion(self.utterance, self.timestamp, self.generation)
        references = tuple(self.references)
        self.utterance = None
        self.references = []
        self.jobs.append(job)
        job.task = asyncio.create_task(self._convert(job, references))

    async def _convert(self, job, references):
        try:
            async with self.converter(self.protocol.media_root, references) as decoded:
                job.ready = True
                await self.completed.put((job, decoded, None))
                # Retain admitted WAVs until controller/perception shutdown. A
                # different task may still have their files open during ASR cancel.
                await job.release.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if not self.closed:
                await self.completed.put((job, None, type(exc).__name__))

    async def deliver(self, outcome, incoming):
        job, decoded, failure = outcome
        if self.closed or job.generation != self.generation:
            job.release.set()
            return
        size = decoded.frames * 2 if decoded is not None else 0
        if failure is not None or self.pcm_bytes + size > MAX_SESSION_PCM_BYTES:
            job.release.set()
            await incoming.put(self.protocol.audio_status(job.utterance, 2, job.timestamp, failed=True))
            return
        self.pcm_bytes += size
        job.admitted = True
        await incoming.put(self.protocol.decoded_audio(job.utterance, job.timestamp, decoded.path))

    async def fail(self, incoming, timestamp=None):
        """Missing final, bad file or bounded-assembly failure is not task success."""
        utterance = self.utterance or "samsung-audio-" + str(uuid4())
        at = self.timestamp if timestamp is None else timestamp
        self.invalidate()
        await incoming.put(self.protocol.audio_status(utterance, 2, at, failed=True))

    async def missing_final(self, incoming):
        if self.utterance is not None:
            await self.fail(incoming)

    async def aclose(self):
        self.closed = True
        self.invalidate()
        for job in self.jobs:
            job.release.set()
        tasks = [job.task for job in self.jobs if job.task is not None]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


__all__ = ["SamsungAudioInput"]
