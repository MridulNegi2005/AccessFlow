"""Ollama-backed vision provider for LocalPerception's injected vision seam.

Plain callable matching ``Callable[[Path], str]``: a PNG path in, a text
description out. Runs synchronously (the caller wraps it in
``asyncio.to_thread``) and is bound by an explicit timeout. No automatic
fallback to another model or provider on failure — a failed request raises,
so the caller reports a genuine perception failure instead of a guess.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

DEFAULT_MODEL = "gemma3:4b"
DEFAULT_URL = "http://127.0.0.1:11434"
DEFAULT_TIMEOUT = 30.0
DEFAULT_PROMPT = (
    "Describe this image in one or two sentences. If it shows a device panel, "
    "screen, label, or error message, transcribe any readable text exactly as printed."
)


class OllamaVisionProvider:
    """Sends one image to a local Ollama vision model's ``/api/chat``."""

    def __init__(
        self,
        model: str | None = None,
        url: str | None = None,
        timeout: float | None = None,
        prompt: str = DEFAULT_PROMPT,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model or os.getenv("ACCESSFLOW_VISION_OLLAMA_MODEL", DEFAULT_MODEL)
        self.url = url or os.getenv("ACCESSFLOW_VISION_OLLAMA_URL", DEFAULT_URL)
        env_timeout = os.getenv("ACCESSFLOW_VISION_TIMEOUT")
        self.timeout = timeout if timeout is not None else (
            float(env_timeout) if env_timeout else DEFAULT_TIMEOUT
        )
        self.prompt = prompt
        self._client = client

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def __call__(self, path: Path) -> str:
        image_b64 = base64.b64encode(Path(path).read_bytes()).decode("ascii")
        body = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "user", "content": self.prompt, "images": [image_b64]}],
        }
        if self._client is not None:
            response = self._client.post(f"{self.url}/api/chat", json=body, timeout=self.timeout)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.url}/api/chat", json=body, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        text = payload["message"]["content"].strip()
        if not text:
            raise RuntimeError("Vision provider returned an empty description")
        return text


__all__ = ["OllamaVisionProvider"]
