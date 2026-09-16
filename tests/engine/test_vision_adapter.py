from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest

from accessflow.adapters.vision import DEFAULT_MODEL, DEFAULT_URL, OllamaVisionProvider


def _png(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.png"
    path.write_bytes(b"not-a-real-png-but-bytes-are-all-this-test-needs")
    return path


def test_call_posts_base64_image_and_returns_stripped_text(tmp_path: Path):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": "  PANEL-B\nERR-42  "}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OllamaVisionProvider(model="gemma3:4b", url="http://127.0.0.1:11435", client=client)

    result = provider(_png(tmp_path))

    assert result == "PANEL-B\nERR-42"
    assert seen["url"] == "http://127.0.0.1:11435/api/chat"
    assert seen["body"]["model"] == "gemma3:4b"
    assert seen["body"]["stream"] is False
    message = seen["body"]["messages"][0]
    assert base64.b64decode(message["images"][0]) == _png(tmp_path).read_bytes()


def test_empty_response_raises_without_fabricating_a_caption(tmp_path: Path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"message": {"content": "   "}})))
    provider = OllamaVisionProvider(client=client)

    with pytest.raises(RuntimeError):
        provider(_png(tmp_path))


def test_http_error_propagates_without_fallback(tmp_path: Path):
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(500, json={"error": "boom"})))
    provider = OllamaVisionProvider(client=client)

    with pytest.raises(httpx.HTTPStatusError):
        provider(_png(tmp_path))


def test_defaults_come_from_env_when_unset(monkeypatch):
    monkeypatch.delenv("ACCESSFLOW_VISION_OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("ACCESSFLOW_VISION_OLLAMA_URL", raising=False)
    provider = OllamaVisionProvider()
    assert provider.model == DEFAULT_MODEL
    assert provider.url == DEFAULT_URL

    monkeypatch.setenv("ACCESSFLOW_VISION_OLLAMA_MODEL", "custom-model")
    monkeypatch.setenv("ACCESSFLOW_VISION_OLLAMA_URL", "http://example.invalid")
    provider = OllamaVisionProvider()
    assert provider.model == "custom-model"
    assert provider.url == "http://example.invalid"
