"""Groq media wire behavior with a fake HTTP transport, never a fake final answer."""

import asyncio
import base64
import json
import wave

import httpx
import pytest

from accessflow.adapters.groq_media import GroqMediaPerception
from accessflow.contracts import Audio, AudioEvent, Frame, FrameEvent, Transcript, TranscriptEvent


def wav(tmp_path):
    path = tmp_path / "spoken.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 160)
    return path


def png():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "fixtures/images/device_panel.png"


async def test_cloud_audio_and_image_preserve_sources_and_use_declared_models(tmp_path):
    seen = []

    def handler(request):
        assert request.headers["Authorization"] == "Bearer fixture-key"
        seen.append(str(request.url))
        if request.url.path.endswith("/audio/transcriptions"):
            assert b'whisper-large-v3-turbo' in request.content
            assert b'speech.wav' in request.content
            return httpx.Response(200, json={"text": "  Book Wednesday at five. "})
        body = json.loads(request.content)
        assert body["model"] == "qwen/qwen3.8-27b"
        image_url = body["messages"][0]["content"][1]["image_url"]["url"]
        assert base64.b64decode(image_url.split(",", 1)[1]) == png().read_bytes()
        return httpx.Response(200, json={"choices": [{"message": {"content": "  PANEL-B ERR-42  "}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqMediaPerception(api_key="fixture-key", client=client)
    try:
        audio = AudioEvent(session_id="one", event_id="audio-e", payload=Audio(
            path=str(wav(tmp_path)), utterance_id="utterance-7", revision=2))
        frame = FrameEvent(session_id="one", event_id="image-e", payload=Frame(
            path=str(png()), frame_id="frame-3"))
        spoken = [item async for item in provider.observe(audio)]
        viewed = [item async for item in provider.observe(frame)]
        assert [(item.event_id, item.source_id, item.revision, item.text, item.backend)
                for item in spoken + viewed] == [
            ("audio-e", "utterance-7", 2, "Book Wednesday at five.", "groq/whisper-large-v3-turbo"),
            ("image-e", "frame-3", 0, "PANEL-B ERR-42", "groq/qwen/qwen3.8-27b"),
        ]
        assert seen == ["https://api.groq.com/openai/v1/audio/transcriptions",
                        "https://api.groq.com/openai/v1/chat/completions"]
    finally:
        await provider.aclose()
        await client.aclose()


@pytest.mark.parametrize("modality,status", [("audio", 429), ("image", 500)])
async def test_http_failure_is_explicit_without_response_body_or_key(tmp_path, modality, status):
    client = httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _: httpx.Response(status, json={"error": "private fixture content"})))
    provider = GroqMediaPerception(api_key="fixture-key", client=client)
    event = (AudioEvent(session_id="one", payload=Audio(path=str(wav(tmp_path)), utterance_id="u"))
             if modality == "audio" else FrameEvent(session_id="one", payload=Frame(path=str(png()), frame_id="f")))
    try:
        with pytest.raises(RuntimeError, match=f"Groq {modality} HTTP {status}") as exc:
            [item async for item in provider.observe(event)]
        assert "fixture-key" not in str(exc.value)
        assert "private fixture content" not in str(exc.value)
    finally:
        await client.aclose()


async def test_audio_request_can_be_cancelled_while_network_is_pending(tmp_path):
    started = asyncio.Event()

    async def handler(_):
        started.set()
        await asyncio.Event().wait()

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = GroqMediaPerception(api_key="fixture-key", client=client)
    event = AudioEvent(session_id="one", payload=Audio(path=str(wav(tmp_path)), utterance_id="u"))

    async def run():
        return [item async for item in provider.observe(event)]

    task = asyncio.create_task(run())
    try:
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
    finally:
        await client.aclose()


async def test_text_passes_without_contacting_cloud():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected HTTP")))
    provider = GroqMediaPerception(api_key="fixture-key", client=client)
    event = TranscriptEvent(session_id="one", payload=Transcript(
        utterance_id="u", revision=0, text="Hello", final=True))
    try:
        result = [item async for item in provider.observe(event)]
        assert result[0].text == "Hello"
        assert result[0].backend == "local/text-pass-through"
    finally:
        await client.aclose()
