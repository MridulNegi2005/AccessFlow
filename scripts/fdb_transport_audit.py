"""Retain swallowed official audio-client errors without changing inference."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time


def redact(text: str) -> str:
    for name, value in os.environ.items():
        if value and (name.endswith(("_KEY", "_SECRET", "_TOKEN")) or name == "LIVEKIT_URL"):
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
                  "[REDACTED JWT]", text)


def observe_run(original, output: Path):
    def observed(args, *positional, **kwargs):
        is_client = (isinstance(args, (list, tuple)) and len(args) > 1
                     and Path(str(args[1])).name == "livekit_inference.py")
        started = time.monotonic()
        try:
            result = original(args, *positional, **kwargs)
        except subprocess.CalledProcessError as error:
            if is_client:
                append("failed", error.returncode, error.stdout, error.stderr, started)
            raise
        else:
            if is_client:
                append("finished", result.returncode, None,
                       result.stderr if result.returncode else None, started)
            return result

    def append(status, code, stdout, stderr, started):
        def text(value):
            if isinstance(value, bytes):
                value = value.decode("utf-8", errors="replace")
            return redact(str(value or ""))[:20000]
        row = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": status,
               "exit_code": code, "seconds": round(time.monotonic() - started, 3)}
        if status == "failed" or code:
            row.update(stdout=text(stdout), stderr=text(stderr))
        with output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row) + "\n")
    return observed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Use a new client-audit file; existing evidence is preserved")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.touch()
    arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    original, saved_argv = subprocess.run, sys.argv
    saved_path = list(sys.path)
    try:
        subprocess.run = observe_run(original, args.output)
        sys.argv = [str(args.script), *arguments]
        sys.path.insert(0, str(args.script.resolve().parent))
        runpy.run_path(str(args.script), run_name="__main__")
    finally:
        subprocess.run, sys.argv = original, saved_argv
        sys.path[:] = saved_path
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
