import base64
import json
from pathlib import Path

import pytest

from accessflow.perception import OllamaVisionProvider


class FakeResponse:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


def test_ollama_provider_posts_one_png_and_returns_trimmed_response(tmp_path: Path):
    image = tmp_path / "screen.png"
    image_bytes = b"png-test-bytes"
    image.write_bytes(image_bytes)
    seen = {}

    def opener(request, *, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"response": "  The screen is flickering.  "})

    provider = OllamaVisionProvider(
        model="gemma3:4b",
        endpoint="http://127.0.0.1:11434/api/generate",
        prompt="Describe the screen.",
        timeout_s=7,
        opener=opener,
    )

    assert provider(image) == "The screen is flickering."
    assert provider.backend_name == "ollama/gemma3:4b"
    assert seen["url"].endswith("/api/generate")
    assert seen["timeout"] == 7
    assert seen["body"]["model"] == "gemma3:4b"
    assert seen["body"]["prompt"] == "Describe the screen."
    assert seen["body"]["stream"] is False
    assert seen["body"]["images"] == [base64.b64encode(image_bytes).decode("ascii")]


@pytest.mark.parametrize("body", [[], None])
def test_ollama_provider_rejects_non_object_json_response(tmp_path: Path, body):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="invalid JSON shape"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse(body))(image)


def test_ollama_provider_surfaces_service_and_shape_errors(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="Ollama vision error: model unavailable"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse({"error": "model unavailable"}))(image)

    with pytest.raises(RuntimeError, match="did not contain text"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse({"response": ""}))(image)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": " "}, "model cannot be empty"),
        ({"endpoint": " "}, "endpoint cannot be empty"),
        ({"endpoint": "https://example.com/api/generate"}, "endpoint must use a loopback host"),
        ({"timeout_s": 0}, "timeout_s must be positive"),
    ],
)
def test_ollama_provider_rejects_invalid_configuration(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OllamaVisionProvider(**kwargs)
