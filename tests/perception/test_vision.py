import base64
import io
import json
import math
from pathlib import Path
from urllib.error import HTTPError

import pytest

from accessflow.perception import OllamaVisionProvider
from accessflow.perception import vision as vision_module


class FakeResponse:
    def __init__(self, body: object):
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")

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


def test_ollama_provider_rejects_invalid_json_bytes(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="returned invalid JSON"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse(b"{not-json"))(image)


def test_ollama_provider_normalizes_timeout(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    def opener(request, *, timeout):
        raise TimeoutError("vision request timed out")

    with pytest.raises(RuntimeError, match="Ollama vision request failed"):
        OllamaVisionProvider(opener=opener)(image)


def test_ollama_provider_rejects_oversized_image_before_request(tmp_path: Path):
    image = tmp_path / "large.png"
    image.write_bytes(b"x" * (vision_module.MAX_VISION_IMAGE_BYTES + 1))
    called = False

    def opener(request, *, timeout):
        nonlocal called
        called = True
        return FakeResponse({"response": "unexpected"})

    with pytest.raises(RuntimeError, match="image is too large"):
        OllamaVisionProvider(opener=opener)(image)

    assert called is False


def test_ollama_provider_rejects_oversized_response(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="response is too large"):
        OllamaVisionProvider(
            opener=lambda request, timeout: FakeResponse(
                b"x" * (vision_module.MAX_VISION_RESPONSE_BYTES + 1)
            )
        )(image)


def test_ollama_provider_classifies_missing_image(tmp_path: Path):
    with pytest.raises(RuntimeError, match="image could not be read"):
        OllamaVisionProvider()(tmp_path / "missing.png")


@pytest.mark.parametrize("body", [[], None])
def test_ollama_provider_rejects_non_object_json_response(tmp_path: Path, body):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="invalid JSON shape"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse(body))(image)


@pytest.mark.parametrize("done", [False, "true"])
def test_ollama_provider_rejects_incomplete_response(tmp_path: Path, done):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="incomplete response"):
        OllamaVisionProvider(
            opener=lambda request, timeout: FakeResponse(
                {"done": done, "response": "partial caption"}
            )
        )(image)


def test_ollama_provider_surfaces_service_and_shape_errors(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="Ollama vision error: model unavailable"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse({"error": "model unavailable"}))(image)

    with pytest.raises(RuntimeError, match="did not contain text"):
        OllamaVisionProvider(opener=lambda request, timeout: FakeResponse({"response": ""}))(image)


def test_ollama_provider_surfaces_quota_exhaustion(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    with pytest.raises(RuntimeError, match="Ollama vision error: quota exhausted"):
        OllamaVisionProvider(
            opener=lambda request, timeout: FakeResponse({"error": "quota exhausted"})
        )(image)


def test_ollama_provider_surfaces_http_quota_exhaustion(tmp_path: Path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-test-bytes")

    def opener(request, *, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            {},
            io.BytesIO(json.dumps({"error": "quota exhausted"}).encode("utf-8")),
        )

    with pytest.raises(RuntimeError, match="Ollama vision error: quota exhausted"):
        OllamaVisionProvider(opener=opener)(image)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": " "}, "model cannot be empty"),
        ({"endpoint": " "}, "endpoint cannot be empty"),
        ({"endpoint": "https://example.com/api/generate"}, "endpoint must use a loopback host"),
        ({"timeout_s": 0}, "timeout_s must be positive"),
        ({"timeout_s": math.nan}, "timeout_s must be positive"),
        ({"timeout_s": math.inf}, "timeout_s must be positive"),
        ({"timeout_s": True}, "timeout_s must be positive"),
        ({"model": None}, "model cannot be empty"),
        ({"endpoint": None}, "endpoint cannot be empty"),
    ],
)
def test_ollama_provider_rejects_invalid_configuration(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OllamaVisionProvider(**kwargs)
