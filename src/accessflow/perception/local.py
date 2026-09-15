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


def validate_wav(path: Path) -> WavFormat:
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getcomptype() != "NONE":
                raise ValueError("WAV must contain uncompressed PCM audio")
            metadata = WavFormat(
                channels=handle.getnchannels(),
                sample_width=handle.getsampwidth(),
                sample_rate=handle.getframerate(),
                frames=handle.getnframes(),
            )
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"Invalid WAV file: {path}") from error

    if metadata.channels < 1 or metadata.sample_width < 1 or metadata.sample_rate < 1:
        raise ValueError(f"WAV has invalid format metadata: {path}")
    if metadata.frames < 1:
        raise ValueError(f"WAV contains no audio frames: {path}")
    return metadata


@dataclass(frozen=True)
class PngFormat:
    """Structurally validated PNG metadata used by local vision backends."""

    width: int
    height: int
    bit_depth: int
    color_type: int


def validate_png(path: Path) -> PngFormat:
    """Validate PNG chunks, CRCs, compressed data and termination without decoding pixels."""
    try:
        data = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Invalid PNG file: {path}") from error

    signature = b"\x89PNG\r\n\x1a\n"
    if len(data) < len(signature) or data[:8] != signature:
        raise ValueError(f"Invalid PNG file: {path}")

    offset = len(signature)
    ihdr: tuple[int, int, int, int] | None = None
    saw_idat = False
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
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != chunk_crc:
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

        if chunk_type == b"IDAT":
            saw_idat = True
            idat_data.extend(chunk_data)
        if chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                raise ValueError(f"Invalid PNG file: {path}")
            saw_iend = True
            break
        offset = chunk_end

    if ihdr is None or not saw_idat or not saw_iend:
        raise ValueError(f"Invalid PNG file: {path}")
    try:
        decompressor = zlib.decompressobj()
        decompressor.decompress(bytes(idat_data))
        decompressor.flush()
        if not decompressor.eof or decompressor.unused_data:
            raise ValueError(f"Invalid PNG file: {path}")
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
    """Run one provider call at a time while replacing obsolete pending work."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._pending: _PendingWork | None = None
        self._latest_tokens: dict[Hashable, int] = {}
        self._latest_revisions: dict[Hashable, int] = {}
        self._next_token = 0
        self._active: _PendingWork | None = None
        self._task: asyncio.Task | None = None

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
            if revision is not None and revision <= self._latest_revisions.get(key, -1):
                return _SUPERSEDED
            self._next_token += 1
            token = self._next_token
            self._latest_tokens[key] = token
            if revision is not None:
                self._latest_revisions[key] = revision
            previous = self._pending
            if previous is not None and not previous.result.done():
                previous.result.set_result(_SUPERSEDED)
            self._pending = _PendingWork(key, token, operation, result)
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run())
        try:
            return await result
        except asyncio.CancelledError:
            async with self._lock:
                pending = self._pending
                if pending is not None and pending.result is result:
                    self._pending = None
            raise

    async def _run(self) -> None:
        while True:
            async with self._lock:
                if self._pending is None:
                    self._task = None
                    return
                work = self._pending
                self._pending = None
                self._active = work
            try:
                value = await work.operation()
            except Exception as error:
                async with self._lock:
                    current = self._latest_tokens.get(work.key) == work.token
                if current and not work.result.done():
                    work.result.set_exception(error)
                elif not work.result.done():
                    work.result.set_result(_SUPERSEDED)
            else:
                async with self._lock:
                    current = self._latest_tokens.get(work.key) == work.token
                if not work.result.done():
                    work.result.set_result(value if current else _SUPERSEDED)
            finally:
                async with self._lock:
                    if self._active is work:
                        self._active = None

    async def aclose(self) -> None:
        async with self._lock:
            work = self._active
            pending = self._pending
            self._pending = None
            task = self._task
            self._task = None
            if pending is not None and not pending.result.done():
                pending.result.set_result(_SUPERSEDED)
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
        self._audio_worker = _LatestWorker()
        self._vision_worker = _LatestWorker()

    @property
    def audio_backend_name(self) -> str:
        """Return the truthful label for the configured local audio path."""
        if self._transcriber is not None:
            return "local/injected-asr"
        if self._model_path is not None:
            return "faster-whisper/cpu-int8"
        return "local/unconfigured-asr"

    async def observe(self, event: InputEvent) -> AsyncIterator[Observation]:
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
            result = await self._audio_worker.submit(
                ("audio", event.session_id, event.payload.utterance_id),
                lambda: self._run_with_timeout(self._transcribe(path), "audio"),
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
            text = await self._vision_worker.submit(
                ("frame", event.session_id),
                lambda: self._run_with_timeout(
                    asyncio.to_thread(self._vision_provider, path), "image"
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
        """Stop queued local work when its owning session is shutting down."""
        await asyncio.gather(self._audio_worker.aclose(), self._vision_worker.aclose())

    async def _run_with_timeout(self, awaitable, modality: str):
        if self._timeout_s is None:
            return await awaitable
        work = asyncio.create_task(awaitable)
        try:
            await asyncio.sleep(0)
            done, _ = await asyncio.wait({work}, timeout=self._timeout_s)
            if work in done:
                return work.result()
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
            raise RuntimeError(f"{modality} perception timed out after {self._timeout_s:g}s")
        finally:
            if not work.done():
                work.cancel()
            await asyncio.gather(work, return_exceptions=True)

    async def _transcribe(self, path: Path) -> tuple[str, str]:
        if self._transcriber is not None:
            return await asyncio.to_thread(self._transcriber, path), "local/injected-asr"
        if self._model_path is None:
            raise RuntimeError(
                "No local transcriber configured; install Faster Whisper and provide model_path"
            )
        return await asyncio.to_thread(self._transcribe_installed_whisper, path), "faster-whisper/cpu-int8"

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
