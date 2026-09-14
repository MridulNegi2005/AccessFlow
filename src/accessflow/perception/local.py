"""Local, independently testable perception adapters.

The adapter keeps transcript handling deterministic and validates audio before
passing it to an optional local transcriber. Model work runs off the event loop.
"""

from __future__ import annotations

import asyncio
import struct
import threading
import wave
import zlib
from collections.abc import AsyncIterator, Callable
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
    """Validate PNG chunks, CRCs and termination without decoding pixel data."""
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
        if chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                raise ValueError(f"Invalid PNG file: {path}")
            saw_iend = True
            break
        offset = chunk_end

    if ihdr is None or not saw_idat or not saw_iend:
        raise ValueError(f"Invalid PNG file: {path}")
    return PngFormat(*ihdr)


def _transcribe_with_whisper(model: Any, path: Path) -> str:
    segments, _ = model.transcribe(str(path), beam_size=5)
    return " ".join(segment.text.strip() for segment in segments).strip()


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
    ) -> None:
        if transcriber is not None and model_path is not None:
            raise ValueError("Pass transcriber or model_path, not both")
        self._transcriber = transcriber
        self._model_path = Path(model_path) if model_path is not None else None
        self._vision_provider = vision_provider
        self._whisper_factory = whisper_factory
        self._whisper_model: Any | None = None
        self._model_lock = threading.Lock()

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
            text, backend = await self._transcribe(path)
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
            text = await asyncio.to_thread(self._vision_provider, path)
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
