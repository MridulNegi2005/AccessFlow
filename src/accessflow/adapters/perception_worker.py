"""JSONL subprocess entry point for the native LocalPerception adapter."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
from pathlib import Path

from pydantic import TypeAdapter

from ..contracts import InputEvent
from ..perception.local import LocalPerception

MAX_JSON_BYTES = 256 * 1024
_events = TypeAdapter(InputEvent)


def _write(message: dict) -> None:
    encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("worker response exceeds JSONL frame limit")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


async def _serve(model_path: Path) -> None:
    # The child owns model construction and therefore has the only synchronous
    # native call.  Redirect Python model chatter so stdout remains protocol-only.
    perception = LocalPerception(model_path=model_path)
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
    args = parser.parse_args()
    try:
        asyncio.run(_serve(Path(args.model_path)))
    except Exception:
        # Startup failures are intentionally generic and never sent to stdout.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
