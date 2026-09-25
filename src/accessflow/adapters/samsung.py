"""In-process Samsung queue entry point; external effects belong to the harness.

MP3 clips are assembled asynchronously at the supplied end_of_turn boundary.
Live media quality and platform readiness require separate measured evidence.
"""

import asyncio
import inspect
import json
import math
import os
import time
from collections.abc import Mapping
from pathlib import Path

from .prompt_profile import PROMPT_PROFILES
from .samsung_protocol import MediaInputError, SamsungProtocol, SamsungProtocolError
from .samsung_audio import SamsungAudioInput


PRE_MANIFEST_EVENT_LIMIT = 32
PRE_MANIFEST_BYTE_LIMIT = 65536
PRE_MANIFEST_INPUTS = {"user_speech_chunk", "user_audio_chunk", "video_frame", "interruption", "scenario_end"}


class HarnessAuthorization:
    """Only for organizer mock tools; the controller still checks spoken intent."""

    effect_environment = "mock"

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
        self.audio_input = None
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
            self.audio_input = SamsungAudioInput(protocol)
            self.agent = agent
        except Exception as exc:
            self._setup_error = exc
            raise

    async def _build_agent(self):
        from .configured_agent import build_configured_agent

        return await build_configured_agent(
            root=self.media_root or os.getenv("ACCESSFLOW_SAMSUNG_MEDIA_ROOT"),
            authorization=HarnessAuthorization(), executor=None,
            tool_documentation=self.documentation_evidence, prompt_profile=self.prompt_profile,
            read_answer_mode=self.read_answer_mode, partial_debounce_s=self.partial_debounce_s,
            fast_read_retry=self.fast_read_retry)

    async def _pump_input(self, incoming):
        manifest_seen = False
        pending = []
        pending_bytes = 0
        raw_task = None
        media_task = asyncio.create_task(self.audio_input.completed.get())
        try:
            while True:
                if raw_task is None:
                    raw_task = asyncio.create_task(self.in_queue.get())
                done, _ = await asyncio.wait({raw_task, media_task}, return_when=asyncio.FIRST_COMPLETED)
                # Process already-arrived input before a simultaneous decode
                # result, so a correction can invalidate its generation first.
                if raw_task not in done:
                    await self.audio_input.deliver(media_task.result(), incoming)
                    media_task = asyncio.create_task(self.audio_input.completed.get())
                    continue
                raw = raw_task.result()
                raw_task = None
                if (not manifest_seen and isinstance(raw, Mapping)
                        and raw.get("event_type") in PRE_MANIFEST_INPUTS):
                    # Retain the existing bounded startup ordering contract.
                    try:
                        encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False)
                    except (TypeError, ValueError) as exc:
                        raise SamsungProtocolError("Invalid input before tool_manifest") from exc
                    pending_bytes += len(encoded.encode("utf-8"))
                    if len(pending) >= PRE_MANIFEST_EVENT_LIMIT or pending_bytes > PRE_MANIFEST_BYTE_LIMIT:
                        raise SamsungProtocolError("Input before tool_manifest exceeds the startup buffer")
                    pending.append(json.loads(encoded))
                    continue
                batch = [raw, *pending] if not manifest_seen else [raw]
                for item in batch:
                    await self._deliver_input(item, incoming)
                manifest_seen = True
                pending.clear()
                pending_bytes = 0
                # One raw batch wins a simultaneous correction race; a ready
                # decode must then get service even under sustained raw input.
                if media_task.done():
                    await self.audio_input.deliver(media_task.result(), incoming)
                    media_task = asyncio.create_task(self.audio_input.completed.get())
        finally:
            readers = [task for task in (raw_task, media_task) if task is not None]
            for task in readers:
                task.cancel()
            await asyncio.gather(*readers, return_exceptions=True)

    async def _deliver_input(self, raw, incoming):
        # scenario_end translates to no event: tools may return in the tail
        # window. The harness cancels run() when that window ends.
        try:
            if isinstance(raw, Mapping) and raw.get("event_type") == "user_audio_chunk":
                try:
                    await self.audio_input.accept(raw, incoming)
                except MediaInputError:
                    self.diagnostics.append({"code": "media_unavailable"})
                    del self.diagnostics[:-128]
                    await self.audio_input.fail(incoming)
                return
            events = self.protocol.translate_input(raw)
        except MediaInputError:
            self.audio_input.invalidate()
            self.diagnostics.append({"code": "media_unavailable"})
            del self.diagnostics[:-128]
            for event in self.protocol.media_failure_events(raw):
                await incoming.put(event)
            await self.out_queue.put({"action": "clarification_request", "payload": {
                "text": "I couldn't process that media. Please describe it or provide another recording or image."}})
            return
        if raw.get("event_type") in {"interruption", "user_speech_chunk"}:
            self.audio_input.invalidate()
        elif raw.get("event_type") == "scenario_end":
            await self.audio_input.missing_final(incoming)
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
                try:
                    await self.audio_input.aclose()
                finally:
                    self._running = False
                    self._finished = True
