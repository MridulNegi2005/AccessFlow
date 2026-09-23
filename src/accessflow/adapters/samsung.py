"""In-process Samsung queue entry point; external effects belong to the harness.

This is an integration adapter, not a claim of full multimodal readiness. MP3
assembly remains an explicit perception integration dependency.
"""

import asyncio
import inspect
import json
import math
import os
import time
from collections.abc import Mapping
from pathlib import Path

from accessflow.engine import Agent

from .prompt_profile import PROMPT_PROFILES
from .samsung_protocol import MediaInputError, SamsungProtocol, SamsungProtocolError


PRE_MANIFEST_EVENT_LIMIT = 32
PRE_MANIFEST_BYTE_LIMIT = 65536
PRE_MANIFEST_INPUTS = {"user_speech_chunk", "user_audio_chunk", "video_frame", "interruption", "scenario_end"}


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

    def __init__(self, in_queue, out_queue, *, agent_factory=None, media_root=None,
                 tool_documentation=None):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.agent_factory = agent_factory
        self.media_root = media_root
        self.tool_documentation = tool_documentation
        self.documentation_evidence = None
        self.partial_debounce_s = 0.08
        self.fast_read_retry = True
        self.prompt_profile = "full"
        self.read_answer_mode = "prose"
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
            self.partial_debounce_s = float(os.getenv("ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S", "0.08"))
            if not math.isfinite(self.partial_debounce_s) or not 0 <= self.partial_debounce_s <= 5:
                raise ValueError("Samsung partial debounce must be between 0 and 5 seconds")
            fast_read_retry = os.getenv("ACCESSFLOW_SAMSUNG_FAST_READ_RETRY", "1")
            if fast_read_retry not in {"0", "1"}:
                raise ValueError("Samsung fast read retry must be 0 or 1")
            self.fast_read_retry = fast_read_retry == "1"
            self.prompt_profile = os.getenv("ACCESSFLOW_SAMSUNG_PROMPT_PROFILE", "full")
            if self.prompt_profile not in PROMPT_PROFILES:
                raise ValueError("Samsung prompt profile must be " + ", ".join(sorted(PROMPT_PROFILES)))
            from accessflow.read_answer import READ_ANSWER_MODES

            self.read_answer_mode = os.getenv("ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE", "prose")
            if self.read_answer_mode not in READ_ANSWER_MODES:
                raise ValueError("Invalid Samsung read answer mode")
            documentation = (self.tool_documentation if self.tool_documentation is not None
                             else os.getenv("ACCESSFLOW_SAMSUNG_TOOL_DOCUMENTATION"))
            if documentation is not None:
                from .tool_metadata import load_tool_documentation
                self.documentation_evidence = load_tool_documentation(Path(root), documentation)
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
        return Agent(LocalPerception(), HeuristicTurnPolicy(),
                     ModelReasoner(backend, tool_documentation=self.documentation_evidence,
                                   prompt_profile=self.prompt_profile, read_answer_mode=self.read_answer_mode),
                     executor=None, authorization=HarnessAuthorization(),
                     partial_debounce_s=self.partial_debounce_s, fast_read_retry=self.fast_read_retry,
                     read_answer_mode=self.read_answer_mode)

    async def _pump_input(self, incoming):
        manifest_seen = False
        pending = []
        pending_bytes = 0
        while True:
            raw = await self.in_queue.get()
            if (not manifest_seen and isinstance(raw, Mapping)
                    and raw.get("event_type") in PRE_MANIFEST_INPUTS):
                # The official contract probe sends speech before any manifest.
                # Retain bounded user input, but give the controller no authority
                # or observations until its actual tool registry is initialized.
                try:
                    encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False)
                except (TypeError, ValueError) as exc:
                    raise SamsungProtocolError("Invalid input before tool_manifest") from exc
                pending_bytes += len(encoded.encode("utf-8"))
                if len(pending) >= PRE_MANIFEST_EVENT_LIMIT or pending_bytes > PRE_MANIFEST_BYTE_LIMIT:
                    raise SamsungProtocolError("Input before tool_manifest exceeds the startup buffer")
                pending.append(json.loads(encoded))
                continue
            # The strict translator still validates the manifest before any held
            # input. Unknown event types and unsolicited tool results still fail.
            batch = [raw, *pending] if not manifest_seen else [raw]
            for item in batch:
                await self._deliver_input(item, incoming)
            manifest_seen = True
            pending.clear()
            pending_bytes = 0

    async def _deliver_input(self, raw, incoming):
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
            return
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
