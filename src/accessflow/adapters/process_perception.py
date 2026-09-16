"""Bounded native perception process adapter.

Text is intentionally handled by :class:`LocalPerception` in this process.  The
model backed modalities run in a separate Python process so cancellation can
actually stop a native call instead of merely cancelling its coroutine.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

from ..contracts import FrameEvent, InputEvent, Observation, TranscriptEvent
from ..perception.local import LocalPerception

DEFAULT_WORKER_MODULE = "accessflow.adapters.perception_worker"
MAX_JSON_BYTES = 256 * 1024
MAX_OBSERVATIONS = 64


class ProcessPerception:
    """Perception adapter with a persistent, bounded native worker.

    ``worker_module`` and ``worker_args`` are intentionally injectable for
    deterministic protocol tests.  Production uses the package worker, which
    constructs ``LocalPerception(model_path=...)`` in the child.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        observation_timeout_s: float = 30.0,
        timeout_s: float | None = None,
        shutdown_timeout_s: float = 1.0,
        max_json_bytes: int = MAX_JSON_BYTES,
        worker_module: str = DEFAULT_WORKER_MODULE,
        worker_args: Sequence[str] = (),
    ) -> None:
        if timeout_s is not None:
            observation_timeout_s = timeout_s
        if observation_timeout_s <= 0 or shutdown_timeout_s <= 0:
            raise ValueError("worker timeouts must be positive")
        if max_json_bytes < 1024:
            raise ValueError("max_json_bytes is too small for the protocol")
        self.model_path = Path(model_path) if model_path is not None else None
        self.observation_timeout_s = observation_timeout_s
        self.shutdown_timeout_s = shutdown_timeout_s
        self.max_json_bytes = max_json_bytes
        self.worker_module = worker_module
        self.worker_args = tuple(str(arg) for arg in worker_args)
        self._process: asyncio.subprocess.Process | None = None
        self._stderr_tasks: dict[int, asyncio.Task[None]] = {}
        self._cleanup_tasks: dict[int, asyncio.Task[None]] = {}
        self._startup_task: asyncio.Task[asyncio.subprocess.Process] | None = None
        self._lifecycle_lock = asyncio.Lock()
        self._lock = asyncio.Lock()
        self._closed = False
        self._text = LocalPerception()

    @property
    def child_pid(self) -> int | None:
        """PID of the current native worker, if it has been started."""
        return self._process.pid if self._process is not None else None

    @property
    def child_alive(self) -> bool:
        process = self._process
        return process is not None and process.returncode is None

    @property
    def pid(self) -> int | None:
        return self.child_pid

    @property
    def is_alive(self) -> bool:
        return self.child_alive

    async def observe(self, event: InputEvent) -> AsyncIterator[Observation]:
        """Yield observations for one event, serializing native requests."""
        if self._closed:
            raise RuntimeError("perception adapter is closed")
        if isinstance(event, TranscriptEvent):
            async for observation in self._text.observe(event):
                yield observation
            return
        if not isinstance(event, FrameEvent) and event.kind != "audio":
            raise ValueError(f"Unsupported perception event: {event.kind}")
        async with self._lock:
            if self._closed:
                raise RuntimeError("perception adapter is closed")
            try:
                async with asyncio.timeout(self.observation_timeout_s):
                    observations = await self._request(event)
            except asyncio.CancelledError:
                await self._abort_worker()
                raise
            except TimeoutError:
                await self._abort_worker()
                raise TimeoutError("perception worker timed out")
            except Exception:
                await self._abort_worker()
                raise
        for observation in observations:
            yield observation

    async def aclose(self) -> None:
        """Close the adapter and terminate its child; safe to call repeatedly."""
        self._closed = True
        await self._abort_worker()

    async def __aenter__(self) -> ProcessPerception:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def _request(self, event: InputEvent) -> list[Observation]:
        process = await self._ensure_process()
        payload = json.dumps(event.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")).encode()
        if len(payload) > self.max_json_bytes:
            raise ValueError("perception input exceeds JSONL frame limit")
        try:
            assert process.stdin is not None
            process.stdin.write(payload + b"\n")
            await process.stdin.drain()
            return await self._read_response(process, event.event_id)
        except (BrokenPipeError, ConnectionError) as error:
            raise RuntimeError("perception worker stopped") from error

    async def _ensure_process(self) -> asyncio.subprocess.Process:
        async with self._lifecycle_lock:
            if self._closed:
                raise RuntimeError("perception adapter is closed")
            process = self._process
            if process is not None and process.returncode is None:
                return process
            if process is not None:
                old_process = process
            else:
                old_process = None
            startup = self._startup_task
            if startup is None and old_process is None:
                if self.model_path is None or not self.model_path.exists():
                    raise FileNotFoundError(f"Installed local model not found: {self.model_path}")
                startup = asyncio.create_task(self._spawn_process())
                self._startup_task = startup
        if old_process is not None:
            await self._stop_process(old_process)
            return await self._ensure_process()
        try:
            process = await asyncio.shield(startup)
        finally:
            if startup.done():
                async with self._lifecycle_lock:
                    if self._startup_task is startup:
                        self._startup_task = None
        if self._closed:
            await self._stop_process(process)
            raise RuntimeError("perception adapter is closed")
        return process

    async def _spawn_process(self) -> asyncio.subprocess.Process:
        arguments = [self.worker_module, *self.worker_args, "--model-path", str(self.model_path)]
        if os.name == "nt" and sys.prefix != sys.base_prefix:
            # Windows venv python.exe is a redirector: its PID can differ from
            # the Python worker's PID. Start the actual interpreter directly,
            # restoring this environment's import paths without a second child.
            bootstrap = (
                "import json,runpy,sys; config=json.loads(sys.argv[1]); "
                "sys.path[:]=config['path']; sys.prefix=config['prefix']; "
                "sys.exec_prefix=config['exec_prefix']; sys.argv=sys.argv[2:]; "
                "runpy.run_module(sys.argv[0],run_name='__main__')"
            )
            environment = json.dumps({"path": [os.getcwd(), *sys.path], "prefix": sys.prefix,
                                      "exec_prefix": sys.exec_prefix})
            command = [sys._base_executable, "-c", bootstrap, environment, *arguments]
        else:
            command = [sys.executable, "-m", *arguments]
        kwargs = {
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "limit": self.max_json_bytes + 1,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            process = await asyncio.create_subprocess_exec(*command, **kwargs)
        except OSError as error:
            raise RuntimeError("could not start perception worker") from error
        stderr_task = asyncio.create_task(self._drain_stderr(process))
        async with self._lifecycle_lock:
            self._process = process
            self._stderr_tasks[id(process)] = stderr_task
            closed = self._closed
        if closed:
            await self._stop_process(process)
            raise RuntimeError("perception adapter is closed")
        return process

    async def _abort_worker(self) -> None:
        """Finish shielded startup, then stop whichever process it created."""
        startup = self._startup_task
        if startup is not None:
            try:
                await asyncio.shield(startup)
            except Exception:
                pass
            finally:
                if startup.done():
                    async with self._lifecycle_lock:
                        if self._startup_task is startup:
                            self._startup_task = None
        await self._stop_process(self._process)

    async def _read_response(self, process: asyncio.subprocess.Process, event_id: str) -> list[Observation]:
        if process.stdout is None:
            raise RuntimeError("perception worker has no stdout")
        observations: list[Observation] = []
        while True:
            try:
                line = await process.stdout.readline()
            except (asyncio.LimitOverrunError, ValueError) as error:
                raise RuntimeError("perception worker output exceeds JSONL frame limit") from error
            if not line:
                raise RuntimeError("perception worker ended before completing the request")
            if len(line) > self.max_json_bytes or not line.endswith(b"\n"):
                raise RuntimeError("perception worker returned an invalid JSONL frame")
            try:
                message = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError("perception worker returned malformed JSON") from error
            if not isinstance(message, dict):
                raise RuntimeError("perception worker returned malformed JSON")
            message_type = message.get("type")
            if message_type == "done":
                return observations
            if message_type == "error":
                raise RuntimeError("perception worker backend failure")
            if message_type != "observation":
                raise RuntimeError("perception worker returned an unknown message")
            if len(observations) >= MAX_OBSERVATIONS:
                raise RuntimeError("perception worker returned too many observations")
            try:
                observation = Observation.model_validate(message.get("observation"))
            except Exception as error:
                raise RuntimeError("perception worker returned malformed observation") from error
            if observation.event_id != event_id:
                raise RuntimeError("perception worker returned an observation for another event")
            observations.append(observation)

    async def _drain_stderr(self, process: asyncio.subprocess.Process) -> None:
        if process.stderr is None:
            return
        while await process.stderr.read(4096):
            pass

    async def _stop_process(self, process: asyncio.subprocess.Process | None) -> None:
        if process is None:
            return
        key = id(process)
        async with self._lifecycle_lock:
            cleanup = self._cleanup_tasks.get(key)
            if cleanup is None:
                cleanup = asyncio.create_task(self._terminate_and_reap(process))
                self._cleanup_tasks[key] = cleanup
        try:
            await asyncio.shield(cleanup)
        finally:
            if cleanup.done():
                async with self._lifecycle_lock:
                    if self._cleanup_tasks.get(key) is cleanup:
                        self._cleanup_tasks.pop(key, None)

    async def _terminate_and_reap(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is None:
            try:
                process.terminate()
            except (OSError, ProcessLookupError):
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=self.shutdown_timeout_s)
            except asyncio.TimeoutError:
                if process.returncode is None:
                    try:
                        process.kill()
                    except (OSError, ProcessLookupError):
                        pass
                try:
                    await asyncio.wait_for(process.wait(), timeout=self.shutdown_timeout_s)
                except asyncio.TimeoutError as error:
                    raise RuntimeError("perception worker did not stop") from error
        stderr_task = self._stderr_tasks.get(id(process))
        if stderr_task is not None and not stderr_task.done():
            try:
                await asyncio.wait_for(stderr_task, timeout=self.shutdown_timeout_s)
            except asyncio.TimeoutError:
                stderr_task.cancel()
                await asyncio.gather(stderr_task, return_exceptions=True)
        async with self._lifecycle_lock:
            self._stderr_tasks.pop(id(process), None)
            if process is self._process:
                self._process = None


NativePerception = ProcessPerception

__all__ = ["DEFAULT_WORKER_MODULE", "NativePerception", "ProcessPerception"]
