"""JSONL subprocess entry point for the native LocalPerception adapter."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import os
import sys
from pathlib import Path

from pydantic import TypeAdapter

from .vision import OllamaVisionProvider
from ..contracts import InputEvent
from ..perception.local import LocalPerception

MAX_JSON_BYTES = 256 * 1024
_events = TypeAdapter(InputEvent)


class _NamedVisionProvider:
    """Expose the A-side provider identity through LocalPerception's B-side seam."""

    def __init__(self, provider: OllamaVisionProvider) -> None:
        self._provider = provider
        self.backend_name = provider.name

    def __call__(self, path: Path) -> str:
        return self._provider(path)


def _positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("vision timeout must be a finite positive number") from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("vision timeout must be a finite positive number")
    return timeout


def _vision_provider(
    provider_name: str,
    *,
    model: str | None = None,
    url: str | None = None,
    timeout: float | None = None,
) -> _NamedVisionProvider | None:
    if provider_name == "none":
        if model is not None or url is not None or timeout is not None:
            raise ValueError("vision options require --vision-provider ollama")
        return None
    if provider_name != "ollama":
        raise ValueError(f"unsupported vision provider: {provider_name}")
    options = {
        key: value
        for key, value in {
            "model": model,
            "url": url,
            "timeout": timeout,
        }.items()
        if value is not None
    }
    return _NamedVisionProvider(OllamaVisionProvider(**options))


def _build_perception(
    model_path: Path,
    *,
    provider_name: str = "none",
    vision_model: str | None = None,
    vision_url: str | None = None,
    vision_timeout: float | None = None,
) -> LocalPerception:
    provider = _vision_provider(
        provider_name,
        model=vision_model,
        url=vision_url,
        timeout=vision_timeout,
    )
    if provider is None:
        return LocalPerception(model_path=model_path)
    return LocalPerception(model_path=model_path, vision_provider=provider)


def _write(message: dict) -> None:
    encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("worker response exceeds JSONL frame limit")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


async def _serve(
    model_path: Path,
    *,
    provider_name: str = "none",
    vision_model: str | None = None,
    vision_url: str | None = None,
    vision_timeout: float | None = None,
) -> None:
    # The child owns model construction and therefore has the only synchronous
    # native call.  Redirect Python model chatter so stdout remains protocol-only.
    perception = _build_perception(
        model_path,
        provider_name=provider_name,
        vision_model=vision_model,
        vision_url=vision_url,
        vision_timeout=vision_timeout,
    )
    try:
        for raw in sys.stdin.buffer:
            if len(raw) > MAX_JSON_BYTES or not raw.endswith(b"\n"):
                _write({"type": "error", "code": "protocol"})
                continue
            try:
                event = _events.validate_json(raw)
                with _redirect_native_stdout():
                    observations = [item async for item in perception.observe(event)]
                for observation in observations:
                    _write({"type": "observation", "observation": observation.model_dump(mode="json")})
                _write({"type": "done"})
            except Exception:
                # Backend details can contain paths, prompts or provider data.  Keep
                # them out of the protocol; stderr remains drained by the parent.
                _write({"type": "error", "code": "backend_failure"})
    finally:
        await perception.aclose()


@contextlib.contextmanager
def _redirect_native_stdout():
    """Keep Python and native model diagnostics off the JSONL stdout pipe."""
    sys.stdout.flush()
    saved_fd = os.dup(1)
    try:
        os.dup2(sys.stderr.fileno(), 1)
        with contextlib.redirect_stdout(sys.stderr):
            yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_fd, 1)
        os.close(saved_fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--vision-provider", choices=("none", "ollama"), default="none")
    parser.add_argument("--vision-model", default=None)
    parser.add_argument("--vision-url", default=None)
    parser.add_argument("--vision-timeout", type=_positive_timeout, default=None)
    args = parser.parse_args()
    try:
        asyncio.run(
            _serve(
                Path(args.model_path),
                provider_name=args.vision_provider,
                vision_model=args.vision_model,
                vision_url=args.vision_url,
                vision_timeout=args.vision_timeout,
            )
        )
    except Exception:
        # Startup failures are intentionally generic and never sent to stdout.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
