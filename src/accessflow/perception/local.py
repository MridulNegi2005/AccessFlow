"""Local, independently testable perception adapters.

The adapter keeps transcript handling deterministic and validates audio before
passing it to an optional local transcriber. Model work runs off the event loop.
"""

from __future__ import annotations

import asyncio
import math
import struct
import threading
import wave
import zlib
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable, Hashable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts import AudioEvent, FrameEvent, InputEvent, Observation, TranscriptEvent


@dataclass(frozen=True)
class WavFormat:
    """Validated PCM WAV metadata used by a local audio backend."""

    channels: int
    sample_width: int
    sample_rate: int
    frames: int


MAX_WAV_FILE_BYTES = 8 * 1024 * 1024
MAX_WAV_DECODED_BYTES = 64 * 1024 * 1024
MAX_SESSION_WORKERS = 64


def validate_wav(path: Path) -> WavFormat:
    try:
        if path.stat().st_size > MAX_WAV_FILE_BYTES:
            raise ValueError(f"WAV file is too large: {path}")
        with wave.open(str(path), "rb") as handle:
            if handle.getcomptype() != "NONE":
                raise ValueError("WAV must contain uncompressed PCM audio")
            metadata = WavFormat(
                channels=handle.getnchannels(),
                sample_width=handle.getsampwidth(),
                sample_rate=handle.getframerate(),
                frames=handle.getnframes(),
            )
            if metadata.channels < 1 or metadata.sample_width < 1 or metadata.sample_rate < 1:
                raise ValueError(f"WAV has invalid format metadata: {path}")
            if metadata.frames < 1:
                raise ValueError(f"WAV contains no audio frames: {path}")
            frame_width = metadata.channels * metadata.sample_width
            if metadata.frames * frame_width > MAX_WAV_DECODED_BYTES:
                raise ValueError(f"WAV decoded payload is too large: {path}")
            remaining = metadata.frames
            while remaining:
                chunk_frames = min(remaining, 8192)
                chunk = handle.readframes(chunk_frames)
                if len(chunk) != chunk_frames * frame_width:
                    raise ValueError(f"WAV PCM payload is truncated: {path}")
                remaining -= chunk_frames
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"Invalid WAV file: {path}") from error
    return metadata


@dataclass(frozen=True)
class PngFormat:
    """Structurally validated PNG metadata used by local vision backends."""

    width: int
    height: int
    bit_depth: int
    color_type: int


MAX_PNG_FILE_BYTES = 8 * 1024 * 1024
MAX_PNG_DECODED_BYTES = 64 * 1024 * 1024
_PNG_CRITICAL_CHUNKS = frozenset({b"IHDR", b"PLTE", b"IDAT", b"IEND"})


def validate_png(path: Path) -> PngFormat:
    """Validate PNG chunks, CRCs, compressed data and termination without decoding pixels."""
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_PNG_FILE_BYTES + 1)
    except OSError as error:
        raise ValueError(f"Invalid PNG file: {path}") from error
    if len(data) > MAX_PNG_FILE_BYTES:
        raise ValueError(f"PNG file is too large: {path}")

    signature = b"\x89PNG\r\n\x1a\n"
    if len(data) < len(signature) or data[:8] != signature:
        raise ValueError(f"Invalid PNG file: {path}")

    offset = len(signature)
    ihdr: tuple[int, int, int, int] | None = None
    interlace: int | None = None
    palette_entries: int | None = None
    saw_idat = False
    idat_closed = False
    idat_data = bytearray()
    saw_iend = False
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError(f"Invalid PNG file: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ValueError(f"Invalid PNG file: {path}")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        chunk_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        if (
            len(chunk_type) != 4
            or any(
                not (65 <= value <= 90 or 97 <= value <= 122)
                for value in chunk_type
            )
            or 97 <= chunk_type[2] <= 122
        ):
            raise ValueError(f"Invalid PNG chunk type: {path}")
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != chunk_crc:
            raise ValueError(f"Invalid PNG file: {path}")
        if chunk_type not in _PNG_CRITICAL_CHUNKS and 65 <= chunk_type[0] <= 90:
            raise ValueError(f"Invalid PNG file: {path}")

        if ihdr is None:
            if chunk_type != b"IHDR" or length != 13:
                raise ValueError(f"Invalid PNG file: {path}")
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            valid_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if (
                width < 1
                or height < 1
                or bit_depth not in valid_depths.get(color_type, set())
                or compression != 0
                or filter_method != 0
                or interlace not in (0, 1)
            ):
                raise ValueError(f"Invalid PNG file: {path}")
            ihdr = (width, height, bit_depth, color_type)
        elif chunk_type == b"IHDR":
            raise ValueError(f"Invalid PNG file: {path}")

        if chunk_type == b"PLTE":
            if (
                ihdr is None
                or saw_idat
                or palette_entries is not None
                or ihdr[3] in {0, 4}
                or length < 3
                or length > 768
                or length % 3
            ):
                raise ValueError(f"Invalid PNG palette: {path}")
            palette_entries = length // 3
            if ihdr[3] == 3 and palette_entries > (1 << ihdr[2]):
                raise ValueError(f"Invalid PNG palette: {path}")
        if chunk_type == b"IDAT":
            if idat_closed:
                raise ValueError(f"Invalid PNG chunk order: {path}")
            if ihdr is not None and ihdr[3] == 3 and palette_entries is None:
                raise ValueError(f"Invalid PNG palette: {path}")
            saw_idat = True
            idat_data.extend(chunk_data)
        elif saw_idat and chunk_type != b"IEND":
            idat_closed = True
        if chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                raise ValueError(f"Invalid PNG file: {path}")
            saw_iend = True
            break
        offset = chunk_end

    if ihdr is None or not saw_idat or not saw_iend:
        raise ValueError(f"Invalid PNG file: {path}")
    if ihdr[3] == 3 and palette_entries is None:
        raise ValueError(f"Invalid PNG palette: {path}")
    if interlace is None:
        raise ValueError(f"Invalid PNG file: {path}")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ihdr[3]]
    bits_per_pixel = channels * ihdr[2]
    scanline_groups: list[tuple[int, int]] = []
    if interlace == 0:
        row_bytes = (ihdr[0] * bits_per_pixel + 7) // 8
        scanline_groups.append((row_bytes, ihdr[1]))
    else:
        for x_start, y_start, x_step, y_step in (
            (0, 0, 8, 8),
            (4, 0, 8, 8),
            (0, 4, 4, 8),
            (2, 0, 4, 4),
            (0, 2, 2, 4),
            (1, 0, 2, 2),
            (0, 1, 1, 2),
        ):
            pass_width = (ihdr[0] - x_start + x_step - 1) // x_step if ihdr[0] > x_start else 0
            pass_height = (ihdr[1] - y_start + y_step - 1) // y_step if ihdr[1] > y_start else 0
            row_bytes = (pass_width * bits_per_pixel + 7) // 8
            if pass_width and pass_height:
                scanline_groups.append((row_bytes, pass_height))
    expected_size = sum((row_bytes + 1) * row_count for row_bytes, row_count in scanline_groups)
    if expected_size > MAX_PNG_DECODED_BYTES:
        raise ValueError(f"Invalid PNG decoded payload is too large: {path}")
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(bytes(idat_data), expected_size + 1)
        if (
            len(decoded) != expected_size
            or not decompressor.eof
            or decompressor.unused_data
            or decompressor.unconsumed_tail
        ):
            raise ValueError(f"Invalid PNG file: {path}")
        offset = 0
        for row_bytes, row_count in scanline_groups:
            for _ in range(row_count):
                if decoded[offset] > 4:
                    raise ValueError(f"Invalid PNG filter byte: {path}")
                offset += row_bytes + 1
    except zlib.error as error:
        raise ValueError(f"Invalid PNG file: {path}") from error
    return PngFormat(*ihdr)


def _transcribe_with_whisper(model: Any, path: Path) -> str:
    segments, _ = model.transcribe(str(path), beam_size=5)
    return " ".join(segment.text.strip() for segment in segments).strip()


def _normalize_provider_text(value: Any, modality: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{modality} perception returned empty text")
    return value.strip()


_SUPERSEDED = object()


@dataclass
class _PendingWork:
    key: Hashable
    token: int
    operation: Callable[[], Awaitable[Any]]
    result: asyncio.Future


class _LatestWorker:
    """Run one provider call at a time with bounded recent source coalescing state.

    The controller remains responsible for authoritative per-session revision
    gating; this worker only suppresses stale work while its recent state is
    retained.
    """

    def __init__(self, *, max_pending_keys: int = 8, max_state_keys: int = 64) -> None:
        if max_pending_keys < 1:
            raise ValueError("max_pending_keys must be positive")
        if max_state_keys < max_pending_keys + 1:
            raise ValueError("max_state_keys must hold active and pending work")
        self._lock = asyncio.Lock()
        self._pending: dict[Hashable, _PendingWork] = {}
        self._max_pending_keys = max_pending_keys
        self._max_state_keys = max_state_keys
        self._latest_state: OrderedDict[Hashable, tuple[int, int | None]] = OrderedDict()
        self._next_token = 0
        self._active: _PendingWork | None = None
        self._task: asyncio.Task | None = None
        self._closed = False
        self.native_slot = asyncio.Semaphore(1)

    def _evict_state(self) -> None:
        protected = set(self._pending)
        if self._active is not None:
            protected.add(self._active.key)
        while len(self._latest_state) > self._max_state_keys:
            for key in self._latest_state:
                if key not in protected:
                    del self._latest_state[key]
                    break
            else:
                return

    async def submit(
        self,
        key: Hashable,
        operation: Callable[[], Awaitable[Any]],
        *,
        revision: int | None = None,
    ) -> Any:
        loop = asyncio.get_running_loop()
        result = loop.create_future()
        async with self._lock:
            if self._closed:
                return _SUPERSEDED
            previous_state = self._latest_state.get(key)
            if (
                revision is not None
                and previous_state is not None
                and previous_state[1] is not None
                and revision <= previous_state[1]
            ):
                return _SUPERSEDED
            self._next_token += 1
            token = self._next_token
            self._latest_state[key] = (token, revision)
            self._latest_state.move_to_end(key)
            previous = self._pending.get(key)
            if previous is not None and not previous.result.done():
                previous.result.set_result(_SUPERSEDED)
            if previous is None and len(self._pending) >= self._max_pending_keys:
                oldest_key = next(iter(self._pending))
                oldest = self._pending.pop(oldest_key)
                if not oldest.result.done():
                    oldest.result.set_result(_SUPERSEDED)
            self._pending[key] = _PendingWork(key, token, operation, result)
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
        try:
            return await result
        except asyncio.CancelledError:
            async with self._lock:
                pending = self._pending.get(key)
                if pending is not None and pending.result is result:
                    del self._pending[key]
                active = self._active
                if (
                    (pending is not None and pending.result is result)
                    or (active is not None and active.result is result)
                ) and self._latest_state.get(key, (None, None))[0] == token:
                    if previous_state is None:
                        self._latest_state.pop(key, None)
                    else:
                        self._latest_state[key] = previous_state
                        self._latest_state.move_to_end(key)
            raise

    async def _run(self) -> None:
        while True:
            async with self._lock:
                if not self._pending:
                    self._task = None
                    return
                key = next(iter(self._pending))
                work = self._pending.pop(key)
                self._active = work
            try:
                value = await work.operation()
            except Exception as error:
                async with self._lock:
                    current = self._latest_state.get(work.key, (None, None))[0] == work.token
                if current and not work.result.done():
                    work.result.set_exception(error)
                elif not work.result.done():
                    work.result.set_result(_SUPERSEDED)
            else:
                async with self._lock:
                    current = self._latest_state.get(work.key, (None, None))[0] == work.token
                if not work.result.done():
                    work.result.set_result(value if current else _SUPERSEDED)
            finally:
                async with self._lock:
                    if self._active is work:
                        self._active = None
                    self._evict_state()

    async def aclose(self) -> None:
        async with self._lock:
            self._closed = True
            work = self._active
            pending = list(self._pending.values())
            self._pending.clear()
            task = self._task
            self._task = None
            for item in pending:
                if not item.result.done():
                    item.result.set_result(_SUPERSEDED)
            if work is not None and not work.result.done():
                work.result.set_result(_SUPERSEDED)
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


class LocalPerception:
    """Convert input events into observations without mutating session state.

    ``transcriber`` is a small injection point for tests or another local ASR
    backend. When omitted, ``model_path`` must point to an already-installed
    Faster Whisper model; no model is downloaded during ``observe``.
    """

    def __init__(
        self,
        transcriber: Callable[[Path], str] | None = None,
        *,
        model_path: str | Path | None = None,
        vision_provider: Callable[[Path], str] | None = None,
        whisper_factory: Callable[..., Any] | None = None,
        timeout_s: float | None = None,
    ) -> None:
        if transcriber is not None and model_path is not None:
            raise ValueError("Pass transcriber or model_path, not both")
        if (
            timeout_s is not None
            and (
                isinstance(timeout_s, bool)
                or not isinstance(timeout_s, (int, float))
                or not math.isfinite(timeout_s)
                or timeout_s <= 0
            )
        ):
            raise ValueError("timeout_s must be a finite positive number")
        self._transcriber = transcriber
        self._model_path = Path(model_path) if model_path is not None else None
        self._vision_provider = vision_provider
        self._whisper_factory = whisper_factory
        self._timeout_s = timeout_s
        self._whisper_model: Any | None = None
        self._model_lock = threading.Lock()
        self._lifecycle_lock = asyncio.Lock()
        self._closed = False
        self._audio_workers: dict[str, _LatestWorker] = {}
        self._vision_workers: dict[str, _LatestWorker] = {}
        self._native_tasks: set[asyncio.Task[Any]] = set()

    async def _worker_for(
        self, workers: dict[str, _LatestWorker], session_id: str
    ) -> _LatestWorker | None:
        async with self._lifecycle_lock:
            if self._closed:
                return None
            return self._worker_for_open(workers, session_id)

    @staticmethod
    def _worker_for_open(workers: dict[str, _LatestWorker], session_id: str) -> _LatestWorker:
        worker = workers.get(session_id)
        if worker is None:
            if len(workers) >= MAX_SESSION_WORKERS:
                raise RuntimeError("perception session worker limit reached")
            worker = _LatestWorker()
            workers[session_id] = worker
        return worker

    @property
    def audio_backend_name(self) -> str:
        """Return the truthful label for the configured local audio path."""
        if self._transcriber is not None:
            return "local/injected-asr"
        if self._model_path is not None:
            return "faster-whisper/cpu-int8"
        return "local/unconfigured-asr"

    @property
    def native_work_in_flight(self) -> int:
        """Return native calls whose underlying worker thread has not returned."""
        return len(self._native_tasks)

    async def observe(self, event: InputEvent) -> AsyncIterator[Observation]:
        if self._closed:
            return
        if isinstance(event, TranscriptEvent):
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.utterance_id,
                revision=event.payload.revision,
                modality="text",
                text=event.payload.text,
                final=event.payload.final,
                speech_start=event.payload.speech_start,
                speech_end=event.payload.speech_end,
                backend="local/text-pass-through",
            )
            return

        if isinstance(event, AudioEvent):
            path = Path(event.payload.path)
            await asyncio.to_thread(validate_wav, path)
            worker = await self._worker_for(self._audio_workers, event.session_id)
            if worker is None:
                return
            result = await worker.submit(
                ("audio", event.payload.utterance_id),
                lambda: self._transcribe(path, worker.native_slot),
                revision=event.payload.revision,
            )
            if result is _SUPERSEDED:
                return
            text, backend = result
            text = _normalize_provider_text(text, "audio")
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.utterance_id,
                revision=event.payload.revision,
                modality="audio",
                text=text,
                final=True,
                speech_start=event.payload.speech_start,
                speech_end=event.payload.speech_end,
                backend=backend,
            )
            return

        if isinstance(event, FrameEvent):
            if self._vision_provider is None:
                raise RuntimeError("Image perception requires an explicit vision provider")
            path = Path(event.payload.path)
            await asyncio.to_thread(validate_png, path)
            worker = await self._worker_for(self._vision_workers, event.session_id)
            if worker is None:
                return
            text = await worker.submit(
                ("frame",),
                lambda: self._run_native_with_timeout(
                    self._vision_provider, path, "image", worker.native_slot
                ),
            )
            if text is _SUPERSEDED:
                return
            text = _normalize_provider_text(text, "image")
            yield Observation(
                event_id=event.event_id,
                source_id=event.payload.frame_id,
                revision=0,
                modality="image",
                text=text,
                final=True,
                speech_start=event.timestamp,
                speech_end=event.timestamp,
                backend=getattr(self._vision_provider, "backend_name", "local/injected-vision"),
            )
            return
        raise ValueError(f"Unsupported perception event: {event.kind}")

    async def aclose(self) -> None:
        """Close admission while tracking non-cancellable native calls to completion."""
        async with self._lifecycle_lock:
            self._closed = True
            workers = [*self._audio_workers.values(), *self._vision_workers.values()]
            self._audio_workers.clear()
            self._vision_workers.clear()
        await asyncio.gather(*(worker.aclose() for worker in workers))

    async def _run_native_with_timeout(
        self,
        provider: Callable[[Path], str],
        path: Path,
        modality: str,
        native_slot: asyncio.Semaphore,
    ) -> str:
        """Bound admission and provider execution as separate phases.

        ``timeout_s`` historically bounded the provider await. The native slot
        adds the same bounded wait for admission, but it is not a single total
        budget. A provider that outlives its execution deadline remains tracked
        and owns the slot until its underlying thread actually returns.
        """
        acquired = False
        native: asyncio.Task[str] | None = None
        try:
            if self._timeout_s is None:
                await native_slot.acquire()
            else:
                try:
                    await asyncio.wait_for(native_slot.acquire(), timeout=self._timeout_s)
                except TimeoutError as error:
                    raise RuntimeError(
                        f"{modality} perception timed out waiting for native capacity "
                        f"after {self._timeout_s:g}s"
                    ) from error
            acquired = True
            native = asyncio.create_task(asyncio.to_thread(provider, path))
            self._native_tasks.add(native)

            def release_slot(done: asyncio.Task[str]) -> None:
                self._native_tasks.discard(done)
                native_slot.release()
                if not done.cancelled():
                    done.exception()

            native.add_done_callback(release_slot)
            acquired = False
            if self._timeout_s is None:
                return await asyncio.shield(native)
            try:
                return await asyncio.wait_for(asyncio.shield(native), timeout=self._timeout_s)
            except TimeoutError as error:
                raise RuntimeError(
                    f"{modality} perception timed out after {self._timeout_s:g}s"
                ) from error
        finally:
            if acquired and native is None:
                native_slot.release()

    async def _transcribe(
        self, path: Path, native_slot: asyncio.Semaphore
    ) -> tuple[str, str]:
        if self._transcriber is not None:
            return (
                await self._run_native_with_timeout(
                    self._transcriber, path, "audio", native_slot
                ),
                "local/injected-asr",
            )
        if self._model_path is None:
            raise RuntimeError(
                "No local transcriber configured; install Faster Whisper and provide model_path"
            )
        return (
            await self._run_native_with_timeout(
                self._transcribe_installed_whisper, path, "audio", native_slot
            ),
            "faster-whisper/cpu-int8",
        )

    def _transcribe_installed_whisper(self, path: Path) -> str:
        if self._model_path is None or not self._model_path.exists():
            raise FileNotFoundError(f"Installed Faster Whisper model not found: {self._model_path}")
        if self._whisper_model is None:
            with self._model_lock:
                if self._whisper_model is None:
                    if self._whisper_factory is not None:
                        self._whisper_model = self._whisper_factory(
                            str(self._model_path),
                            device="cpu",
                            compute_type="int8",
                        )
                    else:
                        try:
                            from faster_whisper import WhisperModel
                        except ImportError as error:
                            raise RuntimeError(
                                "Faster Whisper is optional; install the audio extra to use model_path"
                            ) from error
                        self._whisper_model = WhisperModel(
                            str(self._model_path),
                            device="cpu",
                            compute_type="int8",
                        )
        return _transcribe_with_whisper(self._whisper_model, path)
