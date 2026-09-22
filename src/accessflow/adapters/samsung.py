"""In-process Samsung queue entry point; external effects belong to the harness.

This is an integration adapter, not a claim of full multimodal readiness. MP3
assembly remains an explicit perception integration dependency.
"""

import asyncio
import inspect
import os
import time
from pathlib import Path

from accessflow.engine import Agent

from .samsung_protocol import MediaInputError, SamsungProtocol


class HarnessAuthorization:
    """Only for organizer mock tools; the controller still checks spoken intent."""

    def allows(self, view, call):
        return True


class ScenarioClock:
    """Seconds since run began, at the official evaluation speed (1x)."""

    def __init__(self):
        self.started = time.monotonic()

    def now(self):
        return time.monotonic() - self.started

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


class ParticipantAgent:
    """Constructed by Samsung as ParticipantAgent(in_queue, out_queue).

    Tests inject an async factory returning an Agent. Production setup requires
    an explicit backend and media root; it never substitutes scripted reasoning.
    Use the harness at time_scale=1: accelerated runs are not supported yet.
    """

    def __init__(self, in_queue, out_queue, *, agent_factory=None, media_root=None):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.agent_factory = agent_factory
        self.media_root = media_root
        self.agent = None
        self.protocol = None
        self.tasks = set()
        self.diagnostics = []
        self._running = False
        self._finished = False
        self._setup_error = None

    async def setup(self):
        if self.agent is not None:
            return
        if self._setup_error is not None:
            raise RuntimeError("Samsung adapter setup previously failed") from self._setup_error
        try:
            root = self.media_root or os.getenv("ACCESSFLOW_SAMSUNG_MEDIA_ROOT")
            if root is None or not str(root).strip() or not Path(root).is_dir():
                raise ValueError("Set ACCESSFLOW_SAMSUNG_MEDIA_ROOT to the kit media root")
            protocol = SamsungProtocol(media_root=Path(root))
            agent = await self.agent_factory() if self.agent_factory else await self._build_agent()
            if agent.executor is not None:
                raise ValueError("Samsung adapter requires executor=None; the harness executes tools")
            self.protocol = protocol
            self.agent = agent
        except Exception as exc:
            self._setup_error = exc
            raise

    async def _build_agent(self):
        # Imports and remote/model warm-up occur off the scenario clock in setup.
        from accessflow.perception.local import LocalPerception
        from accessflow.turn_policy import HeuristicTurnPolicy

        from .models import JsonBackend, ModelReasoner

        backend_name = os.getenv("ACCESSFLOW_SAMSUNG_BACKEND")
        if not backend_name:
            raise ValueError("Set ACCESSFLOW_SAMSUNG_BACKEND explicitly; no model fallback is enabled")
        backend = JsonBackend(backend_name)
        await backend.warmup()
        return Agent(LocalPerception(), HeuristicTurnPolicy(), ModelReasoner(backend),
                     executor=None, authorization=HarnessAuthorization())

    async def _pump_input(self, incoming):
        while True:
            raw = await self.in_queue.get()
            # scenario_end translates to no event: tools may return in the tail
            # window. The harness cancels run() when that window ends.
            try:
                events = self.protocol.translate_input(raw)
            except MediaInputError:
                self.diagnostics.append({"code": "media_unavailable"})
                del self.diagnostics[:-128]
                for event in self.protocol.media_failure_events(raw):
                    await incoming.put(event)
                await self.out_queue.put({"action": "clarification_request", "payload": {
                    "text": "I couldn't process that media. Please describe it or provide another recording or image."}})
                continue
            for event in events:
                await incoming.put(event)

    async def _pump_output(self, outgoing):
        while True:
            event = await outgoing.get()
            try:
                if event.kind == "error":
                    # Preserve bounded diagnostics without inventing a sixth
                    # official action type or passing tool errors as speech.
                    self.diagnostics.append(event.model_dump(mode="json"))
                    del self.diagnostics[:-128]
                action = self.protocol.translate_output(event)
                if action is not None:
                    await self.out_queue.put(action)
            finally:
                outgoing.task_done()

    async def run(self):
        if self._running or self._finished:
            raise RuntimeError("Use a fresh Samsung agent instance per scenario")
        if self.agent is None:
            raise RuntimeError("Call setup() successfully before run()") from self._setup_error
        self._running = True
        incoming, outgoing = asyncio.Queue(maxsize=32), asyncio.Queue(maxsize=32)
        engine = asyncio.create_task(self.agent.run(incoming, outgoing, ScenarioClock()))
        self.tasks = {engine, asyncio.create_task(self._pump_input(incoming)),
                      asyncio.create_task(self._pump_output(outgoing))}
        try:
            done, _ = await asyncio.wait(self.tasks, return_when=asyncio.FIRST_COMPLETED)
            # Surface parser/engine failures to the harness's agent_crash trace;
            # never leave a dead input pump looking like a healthy silent agent.
            for task in done:
                task.result()
            if engine in done:
                await asyncio.wait_for(outgoing.join(), timeout=1)
        finally:
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()
            try:
                close = getattr(self.agent.perception, "aclose", None)
                if close is not None:
                    result = close()
                    if inspect.isawaitable(result):
                        await asyncio.wait_for(result, timeout=2)
            finally:
                self._running = False
                self._finished = True
