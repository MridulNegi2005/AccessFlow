"""Optional local Ollama vision provider for PNG perception experiments."""

from __future__ import annotations

import base64
import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import error as url_error
from urllib import request
from urllib.parse import urlparse


class OllamaVisionProvider:
    """Send one PNG to an already-running local Ollama generate endpoint.

    The provider never downloads a model. The caller supplies a model already
    available to the Ollama service, and the response remains untrusted evidence.
    """

    def __init__(
        self,
        *,
        model: str = "gemma3:4b",
        endpoint: str = "http://127.0.0.1:11434/api/generate",
        prompt: str = "Describe only the visible device evidence and state uncertainty.",
        timeout_s: float = 30.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Ollama vision model cannot be empty")
        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("Ollama vision endpoint cannot be empty")
        parsed_endpoint = urlparse(endpoint.strip())
        if parsed_endpoint.scheme not in {"http", "https"} or parsed_endpoint.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise ValueError("Ollama vision endpoint must use a loopback host")
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s)
            or timeout_s <= 0
        ):
            raise ValueError("Ollama vision timeout_s must be positive")
        self.model = model.strip()
        self.endpoint = endpoint.strip()
        self.prompt = prompt
        self.timeout_s = timeout_s
        self._opener = opener or request.urlopen

    @property
    def backend_name(self) -> str:
        return f"ollama/{self.model}"

    def __call__(self, path: Path) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": self.prompt,
                "images": [base64.b64encode(path.read_bytes()).decode("ascii")],
                "stream": False,
            }
        ).encode("utf-8")
        req = request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(req, timeout=self.timeout_s) as response:
                response_body = response.read()
        except url_error.HTTPError as exc:
            try:
                response_body = exc.read()
            except OSError:
                response_body = b""
            try:
                error_payload = json.loads(response_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_payload = None
            if isinstance(error_payload, dict) and error_payload.get("error"):
                raise RuntimeError(f"Ollama vision error: {error_payload['error']}") from exc
            raise RuntimeError(f"Ollama vision request failed: {self.endpoint}") from exc
        except (OSError, url_error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"Ollama vision request failed: {self.endpoint}") from exc
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Ollama vision returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Ollama vision returned invalid JSON shape")
        if payload.get("error"):
            raise RuntimeError(f"Ollama vision error: {payload['error']}")
        result = payload.get("response")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Ollama vision response did not contain text")
        return result.strip()
