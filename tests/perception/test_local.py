import asyncio
import math
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


@pytest.mark.parametrize("timeout_s", [0, -1, math.nan, math.inf, -math.inf, "fast"])
def test_local_perception_rejects_invalid_timeout(timeout_s):
    with pytest.raises(ValueError, match="timeout_s"):
        LocalPerception(timeout_s=timeout_s)


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


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_audio_rejects_empty_transcriber_output(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="empty-audio"),
    )

    with pytest.raises(RuntimeError, match="audio perception returned empty text"):
        await _one(LocalPerception(transcriber=lambda _: "  \t"), event)

async def test_audio_transcriber_timeout_is_classified(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    started = threading.Event()
    finished = threading.Event()

    def transcriber(path: Path) -> str:
        started.set()
        try:
            time.sleep(0.2)
            return "late transcript"
        finally:
            finished.set()

    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="timed-out-audio"),
    )

    observation_task = asyncio.create_task(
        _one(LocalPerception(transcriber=transcriber, timeout_s=0.05), event)
    )
    for _ in range(100):
        if started.is_set():
            break
        await asyncio.sleep(0.01)
    assert started.is_set()
    with pytest.raises(RuntimeError, match=r"audio perception timed out after 0.05s"):
        await observation_task
    for _ in range(100):
        if finished.is_set():
            break
        await asyncio.sleep(0.01)
    assert finished.is_set()


async def test_cancelled_audio_provider_releases_observer(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    started = threading.Event()
    finished = threading.Event()

    def transcriber(path: Path) -> str:
        started.set()
        try:
            time.sleep(0.2)
            return "late transcript"
        finally:
            finished.set()

    event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="cancelled-audio"),
    )
    observation_task = asyncio.create_task(
        _one(LocalPerception(transcriber=transcriber, timeout_s=1), event)
    )
    for _ in range(100):
        if started.is_set():
            break
        await asyncio.sleep(0.01)
    assert started.is_set()

    observation_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await observation_task
    for _ in range(100):
        if finished.is_set():
            break
        await asyncio.sleep(0.01)
    assert finished.is_set()


async def test_slow_audio_transcriber_does_not_block_event_loop(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    transcriber_started = threading.Event()

    def transcriber(path: Path) -> str:
        transcriber_started.set()
        time.sleep(0.15)
        return "Book Wednesday"

    event = AudioEvent(
        session_id="s1",
        event_id="slow-audio-event",
        payload=Audio(path=str(wav_path), utterance_id="slow-audio"),
    )
    observation_task = asyncio.create_task(_one(LocalPerception(transcriber=transcriber), event))

    assert await asyncio.to_thread(transcriber_started.wait, 1)
    heartbeat = asyncio.create_task(asyncio.sleep(0.02))
    await asyncio.wait_for(heartbeat, timeout=0.1)
    assert not observation_task.done()

    observation = await asyncio.wait_for(observation_task, timeout=1)
    assert observation.source_id == "slow-audio"
    assert observation.text == "Book Wednesday"

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
@pytest.mark.asyncio
async def test_image_rejects_non_text_provider_output(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "device.png"
    _write_png(image_path)
    event = FrameEvent(
        session_id="s1",
        payload=Frame(path=str(image_path), frame_id="empty-frame"),
    )

    with pytest.raises(RuntimeError, match="image perception returned empty text"):
        await _one(LocalPerception(vision_provider=lambda _: None), event)

async def test_image_provider_timeout_is_classified(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "screen.png"
    _write_png(image_path)
    started = threading.Event()
    finished = threading.Event()

    def provider(path: Path) -> str:
        started.set()
        try:
            time.sleep(0.2)
            return "late evidence"
        finally:
            finished.set()

    event = FrameEvent(
        session_id="s1",
        payload=Frame(path=str(image_path), frame_id="timed-out-frame"),
    )

    observation_task = asyncio.create_task(
        _one(LocalPerception(vision_provider=provider, timeout_s=0.05), event)
    )
    for _ in range(100):
        if started.is_set():
            break
        await asyncio.sleep(0.01)
    assert started.is_set()
    with pytest.raises(RuntimeError, match=r"image perception timed out after 0.05s"):
        await observation_task
    for _ in range(100):
        if finished.is_set():
            break
        await asyncio.sleep(0.01)
    assert finished.is_set()


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


@pytest.mark.asyncio
async def test_pending_frames_are_coalesced_and_stale_results_are_suppressed(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    paths = [tmp_path / f"frame-{index}.png" for index in range(1, 4)]
    for path in paths:
        _write_png(path)
    provider_started = threading.Event()
    release_first = threading.Event()
    calls = []

    def provider(path: Path) -> str:
        calls.append(path)
        if len(calls) == 1:
            provider_started.set()
            assert release_first.wait(1)
        return f"evidence from {path.stem}"

    async def collect(adapter, event):
        return [observation async for observation in adapter.observe(event)]

    adapter = LocalPerception(vision_provider=provider)
    events = [
        FrameEvent(session_id="s1", payload=Frame(path=str(path), frame_id=f"frame-{index}"))
        for index, path in enumerate(paths, start=1)
    ]
    first_task = asyncio.create_task(collect(adapter, events[0]))
    assert await asyncio.to_thread(provider_started.wait, 1)
    second_task = asyncio.create_task(collect(adapter, events[1]))
    await asyncio.sleep(0.05)
    third_task = asyncio.create_task(collect(adapter, events[2]))
    await asyncio.sleep(0.05)
    release_first.set()

    first, second, third = await asyncio.gather(first_task, second_task, third_task)

    assert first == []
    assert second == []
    assert [item.source_id for item in third] == ["frame-3"]
    assert calls == [paths[0], paths[2]]


@pytest.mark.asyncio
async def test_newer_audio_revision_replaces_pending_work(tmp_path: Path):
    wav_path = tmp_path / "speech.wav"
    _write_wav(wav_path)
    provider_started = threading.Event()
    release_first = threading.Event()
    calls = []

    def transcriber(path: Path) -> str:
        calls.append(path)
        if len(calls) == 1:
            provider_started.set()
            assert release_first.wait(1)
        return f"revision {len(calls)}"

    async def collect(adapter, event):
        return [observation async for observation in adapter.observe(event)]

    adapter = LocalPerception(transcriber=transcriber)
    first_event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="utterance-1", revision=0),
    )
    revised_event = AudioEvent(
        session_id="s1",
        payload=Audio(path=str(wav_path), utterance_id="utterance-1", revision=1),
    )
    first_task = asyncio.create_task(collect(adapter, first_event))
    assert await asyncio.to_thread(provider_started.wait, 1)
    revised_task = asyncio.create_task(collect(adapter, revised_event))
    await asyncio.sleep(0.05)
    release_first.set()

    first, revised = await asyncio.gather(first_task, revised_task)

    assert first == []
    assert [item.revision for item in revised] == [1]
    assert revised[0].text == "revision 2"
    assert calls == [wav_path, wav_path]


@pytest.mark.asyncio
async def test_audio_and_image_workers_run_independently(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    wav_path = tmp_path / "speech.wav"
    image_path = tmp_path / "screen.png"
    _write_wav(wav_path)
    _write_png(image_path)
    audio_started = threading.Event()
    image_started = threading.Event()
    release = threading.Event()

    def transcriber(path: Path) -> str:
        audio_started.set()
        assert release.wait(1)
        return "spoken evidence"

    def provider(path: Path) -> str:
        image_started.set()
        assert release.wait(1)
        return "visual evidence"

    async def collect(adapter, event):
        return [observation async for observation in adapter.observe(event)]

    adapter = LocalPerception(transcriber=transcriber, vision_provider=provider)
    audio_task = asyncio.create_task(
        collect(
            adapter,
            AudioEvent(
                session_id="s1",
                payload=Audio(path=str(wav_path), utterance_id="audio-1"),
            ),
        )
    )
    image_task = asyncio.create_task(
        collect(
            adapter,
            FrameEvent(session_id="s1", payload=Frame(path=str(image_path), frame_id="frame-1")),
        )
    )
    await asyncio.wait_for(
        asyncio.gather(
            asyncio.to_thread(audio_started.wait, 1),
            asyncio.to_thread(image_started.wait, 1),
        ),
        timeout=1,
    )
    assert audio_started.is_set()
    assert image_started.is_set()
    release.set()
    audio, image = await asyncio.gather(audio_task, image_task)

    assert [item.text for item in audio] == ["spoken evidence"]
    assert [item.text for item in image] == ["visual evidence"]


@pytest.mark.asyncio
async def test_same_frame_id_from_different_sessions_is_not_coalesced(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    paths = [tmp_path / "first.png", tmp_path / "second.png"]
    for path in paths:
        _write_png(path)
    provider_started = threading.Event()
    release_first = threading.Event()
    calls = []

    def provider(path: Path) -> str:
        calls.append(path)
        if len(calls) == 1:
            provider_started.set()
            assert release_first.wait(1)
        return f"evidence from {path.stem}"

    async def collect(adapter, event):
        return [observation async for observation in adapter.observe(event)]

    adapter = LocalPerception(vision_provider=provider)
    first_task = asyncio.create_task(
        collect(
            adapter,
            FrameEvent(session_id="session-1", payload=Frame(path=str(paths[0]), frame_id="frame-1")),
        )
    )
    assert await asyncio.to_thread(provider_started.wait, 1)
    second_task = asyncio.create_task(
        collect(
            adapter,
            FrameEvent(session_id="session-2", payload=Frame(path=str(paths[1]), frame_id="frame-1")),
        )
    )
    await asyncio.sleep(0.05)
    release_first.set()

    first, second = await asyncio.gather(first_task, second_task)

    assert [item.source_id for item in first] == ["frame-1"]
    assert [item.source_id for item in second] == ["frame-1"]
    assert calls == paths


@pytest.mark.asyncio
async def test_aclose_releases_active_observer_without_waiting_for_thread(tmp_path: Path):
    from accessflow.contracts import Frame, FrameEvent

    image_path = tmp_path / "screen.png"
    _write_png(image_path)
    provider_started = threading.Event()
    release = threading.Event()
    provider_finished = threading.Event()

    def provider(path: Path) -> str:
        provider_started.set()
        try:
            assert release.wait(1)
            return "visual evidence"
        finally:
            provider_finished.set()

    async def collect(adapter, event):
        return [observation async for observation in adapter.observe(event)]

    adapter = LocalPerception(vision_provider=provider)
    task = asyncio.create_task(
        collect(
            adapter,
            FrameEvent(session_id="s1", payload=Frame(path=str(image_path), frame_id="frame-1")),
        )
    )
    assert await asyncio.to_thread(provider_started.wait, 1)
    await adapter.aclose()
    assert await task == []
    release.set()
    assert await asyncio.to_thread(provider_finished.wait, 1)
    await adapter.aclose()

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
