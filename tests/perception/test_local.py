import asyncio
import struct
import threading
import time
import zlib
import wave
from pathlib import Path

import pytest

from accessflow.contracts import Audio, AudioEvent, Transcript, TranscriptEvent
from accessflow.perception import LocalPerception, PngFormat, WavFormat, validate_png, validate_wav

def _write_png(path: Path, *, width: int = 1, height: int = 1) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    row = b"\x00" + b"\x00\x40\x80\xff" * width
    pixels = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )

def _write_wav(path: Path, *, frames: int = 160) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\x00\x00" * frames)


async def _one(adapter: LocalPerception, event):
    observations = [observation async for observation in adapter.observe(event)]
    assert len(observations) == 1
    return observations[0]


@pytest.mark.asyncio
async def test_transcript_pass_through_preserves_revision_and_timing():
    event = TranscriptEvent(
        session_id="s1",
        event_id="e1",
        timestamp=4.2,
        sequence=7,
        payload=Transcript(
            utterance_id="u1",
            revision=2,
            text="Tuesday... actually Wednesday",
            final=False,
            speech_start=1.1,
            speech_end=4.0,
        ),
    )

    observation = await _one(LocalPerception(), event)

    assert observation.model_dump() == {
        "event_id": "e1",
        "source_id": "u1",
        "revision": 2,
        "modality": "text",
        "text": "Tuesday... actually Wednesday",
        "final": False,
        "speech_start": 1.1,
        "speech_end": 4.0,
        "backend": "local/text-pass-through",
    }


@pytest.mark.asyncio
async def test_audio_validates_wav_and_uses_injected_transcriber(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    seen_paths = []

    def transcriber(path: Path) -> str:
        seen_paths.append(path)
        return "Book Wednesday at five"

    event = AudioEvent(
        session_id="s1",
        event_id="e2",
        payload=Audio(
            path=str(wav_path),
            utterance_id="u2",
            revision=3,
            speech_start=0.5,
            speech_end=2.5,
        ),
    )

    observation = await _one(LocalPerception(transcriber=transcriber), event)

    assert seen_paths == [wav_path]
    assert observation.modality == "audio"
    assert observation.source_id == "u2"
    assert observation.revision == 3
    assert observation.text == "Book Wednesday at five"
    assert observation.final is True
    assert observation.backend == "local/injected-asr"


def test_wav_validation_returns_metadata_for_backend_checks(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path, frames=320)

    metadata = validate_wav(wav_path)

    assert metadata == WavFormat(channels=1, sample_width=2, sample_rate=16_000, frames=320)


@pytest.mark.asyncio
async def test_audio_rejects_malformed_wav(tmp_path: Path):
    wav_path = tmp_path / "broken.wav"
    wav_path.write_bytes(b"not a wav")
    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="u3"),
    )

    with pytest.raises(ValueError, match="Invalid WAV"):
        await _one(LocalPerception(transcriber=lambda _: "never"), event)


@pytest.mark.asyncio
async def test_image_input_requires_real_provider():
    # No canned caption is emitted for an image until a replaceable provider exists.
    from accessflow.contracts import Frame, FrameEvent

    event = FrameEvent(session_id="s1", payload=Frame(path="device.png", frame_id="f1"))

    with pytest.raises(RuntimeError, match="explicit vision provider"):
        await _one(LocalPerception(), event)


@pytest.mark.asyncio
async def test_image_input_preserves_frame_identity_with_injected_provider(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "device.png"
    _write_png(image_path, width=320, height=240)
    seen_paths = []

    def provider(path: Path) -> str:
        seen_paths.append(path)
        return "screen has a horizontal flicker"

    event = FrameEvent(
        session_id="s1",
        event_id="e4",
        timestamp=2.5,
        payload=Frame(path=str(image_path), frame_id="frame-7"),
    )

    observation = await _one(LocalPerception(vision_provider=provider), event)

    assert seen_paths == [image_path]
    assert observation.event_id == "e4"
    assert observation.source_id == "frame-7"
    assert observation.revision == 0
    assert observation.modality == "image"
    assert observation.text == "screen has a horizontal flicker"
    assert observation.speech_start == observation.speech_end == 2.5
    assert observation.backend == "local/injected-vision"


@pytest.mark.asyncio
async def test_slow_image_provider_does_not_block_event_loop(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "device.png"
    _write_png(image_path)
    provider_started = threading.Event()

    def provider(path: Path) -> str:
        provider_started.set()
        time.sleep(0.15)
        return "screen evidence"

    event = FrameEvent(
        session_id="s1",
        event_id="slow-image-event",
        payload=Frame(path=str(image_path), frame_id="slow-frame"),
    )
    observation_task = asyncio.create_task(_one(LocalPerception(vision_provider=provider), event))

    assert await asyncio.to_thread(provider_started.wait, 1)
    heartbeat = asyncio.create_task(asyncio.sleep(0.02))
    await asyncio.wait_for(heartbeat, timeout=0.1)
    assert not observation_task.done()

    observation = await asyncio.wait_for(observation_task, timeout=1)
    assert observation.source_id == "slow-frame"
    assert observation.text == "screen evidence"

def test_png_validation_returns_structural_metadata(tmp_path: Path):
    image_path = tmp_path / "valid.png"
    _write_png(image_path, width=320, height=240)

    assert validate_png(image_path) == PngFormat(width=320, height=240, bit_depth=8, color_type=6)


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["truncated", "bad-crc", "bad-idat"])
async def test_image_input_rejects_structurally_invalid_png(tmp_path: Path, corruption: str):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "broken.png"
    _write_png(image_path)
    data = bytearray(image_path.read_bytes())
    if corruption == "truncated":
        data = data[:-4]
    elif corruption == "bad-crc":
        data[-1] ^= 1
    else:
        idat_offset = 8 + 4 + 4 + 13 + 4
        idat_length = struct.unpack(">I", data[idat_offset : idat_offset + 4])[0]
        idat_data_start = idat_offset + 8
        idat_data_end = idat_data_start + idat_length
        data[idat_data_start:idat_data_end] = b"\x00" * idat_length
        crc = zlib.crc32(b"IDAT" + data[idat_data_start:idat_data_end]) & 0xFFFFFFFF
        data[idat_data_end : idat_data_end + 4] = struct.pack(">I", crc)
    image_path.write_bytes(data)
    event = FrameEvent(session_id="s1", payload=Frame(path=str(image_path), frame_id="frame-9"))

    with pytest.raises(ValueError, match="Invalid PNG"):
        await _one(LocalPerception(vision_provider=lambda _: "never"), event)
@pytest.mark.asyncio
async def test_image_input_rejects_malformed_png(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "broken.png"
    image_path.write_bytes(b"not a png")
    event = FrameEvent(session_id="s1", payload=Frame(path=str(image_path), frame_id="frame-8"))

    with pytest.raises(ValueError, match="Invalid PNG"):
        await _one(LocalPerception(vision_provider=lambda _: "never"), event)

@pytest.mark.asyncio
async def test_checked_in_audio_fixture_uses_the_raw_wav_route():
    fixture = Path(__file__).parents[1] / "fixtures" / "audio" / "synthetic_tone.wav"
    metadata = validate_wav(fixture)

    assert metadata == WavFormat(channels=1, sample_width=2, sample_rate=16_000, frames=8_000)
@pytest.mark.asyncio
async def test_installed_whisper_uses_local_model_factory_and_cpu_int8(tmp_path: Path):
    from types import SimpleNamespace

    model_dir = tmp_path / "whisper-model"
    model_dir.mkdir()
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    factory_calls = []

    class FakeModel:
        def transcribe(self, path: str, beam_size: int):
            assert Path(path) == wav_path
            assert beam_size == 5
            return [SimpleNamespace(text=" Book "), SimpleNamespace(text="Wednesday")], None

    def factory(path: str, **kwargs):
        factory_calls.append((path, kwargs))
        return FakeModel()

    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="u4"),
    )
    observation = await _one(
        LocalPerception(model_path=model_dir, whisper_factory=factory),
        event,
    )

    assert factory_calls == [(str(model_dir), {"device": "cpu", "compute_type": "int8"})]
    assert observation.text == "Book Wednesday"
    assert observation.backend == "faster-whisper/cpu-int8"


@pytest.mark.asyncio
async def test_installed_whisper_rejects_missing_local_model(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="u5"),
    )

    with pytest.raises(FileNotFoundError, match="model not found"):
        await _one(LocalPerception(model_path=tmp_path / "missing"), event)
