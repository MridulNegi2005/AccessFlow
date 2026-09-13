import struct
import wave
from pathlib import Path

import pytest

from accessflow.contracts import Audio, AudioEvent, Transcript, TranscriptEvent
from accessflow.perception import LocalPerception, WavFormat, validate_wav

def _write_png(path: Path, *, width: int = 1, height: int = 1) -> None:
    header = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
    path.write_bytes(header + struct.pack(">II", width, height))


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
async def test_image_input_rejects_malformed_png(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "broken.png"
    image_path.write_bytes(b"not a png")
    event = FrameEvent(session_id="s1", payload=Frame(path=str(image_path), frame_id="frame-8"))

    with pytest.raises(ValueError, match="Invalid PNG"):
        await _one(LocalPerception(vision_provider=lambda _: "never"), event)
