"""Observe pinned scorer requests without changing prompts, replies or scoring.

Run only in the separate official scorer process, never inside the voice agent.
The audit contains no credentials, user text, expected answers or model replies.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
import importlib.metadata
import json
import math
from pathlib import Path
import runpy
import sys
import time

KINDS = {
    "evaluate_tool_calls.py": "correctness",
    "evaluate_pass_rate.py": "correctness",
    "analyze_tool_latency.py": "latency",
}


def valid_reply(response, kind: str) -> bool:
    """Check only reply structure; never evaluate the expected/actual answer."""
    try:
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()
        row = json.loads(raw)
        if not isinstance(row, dict):
            return False
        if kind == "correctness":
            return type(row.get("correct")) is bool and isinstance(row.get("explanation"), str)
        if kind != "latency":
            return False
        strings = ("filler_sentence", "key_info_sentence")
        times = ("filler_start_time", "filler_end_time", "key_info_start_time", "key_info_end_time")
        return (all(isinstance(row.get(key), str) for key in strings)
                and all(key in row and (row[key] is None or
                        (type(row[key]) in (int, float) and math.isfinite(row[key]))) for key in times))
    except (ValueError, AttributeError, IndexError, TypeError):
        return False


@contextmanager
def observe_requests(kind: str, rows: list[dict]):
    """Pass through the exact synchronous SDK call used by the pinned scripts."""
    from openai.resources.chat.completions import Completions

    original = Completions.create

    @wraps(original)
    def observed(resource, *args, **kwargs):
        started = time.monotonic()
        row = {"request": len(rows) + 1, "model": "gpt-4o" if kwargs.get("model") == "gpt-4o" else "unexpected_model"}
        try:
            response = original(resource, *args, **kwargs)
            row["status"] = "valid_response" if valid_reply(response, kind) else "invalid_response"
            usage = getattr(response, "usage", None)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = getattr(usage, key, None)
                if type(value) is int and value >= 0:
                    row[key] = value
            return response
        except BaseException as error:
            # Do not retain the error message: provider errors can include input text.
            row.update(status="request_error", error_type=type(error).__name__)
            raise
        finally:
            row["duration_s"] = round(time.monotonic() - started, 6)
            rows.append(row)

    Completions.create = observed
    try:
        yield
    finally:
        Completions.create = original


def summary(script: Path, rows: list[dict]) -> dict:
    failures = sum(row["status"] != "valid_response" or row["model"] != "gpt-4o" for row in rows)
    return {"version": 1, "script": script.name, "observed_requests": len(rows),
            "failed_requests": failures,
            "status": "unverified_failures" if failures else "observed_valid_requests" if rows else "no_requests_observed",
            "openai_sdk": importlib.metadata.version("openai"), "requests": rows,
            "scope": "SDK request/reply structure only; not proof of judge accuracy or all report coverage"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    script = args.script.resolve()
    if script.name not in KINDS or not script.is_file():
        parser.error("Expected an existing pinned FDB scoring script")
    if args.output.exists():
        parser.error("Refusing to overwrite prior judge evidence")
    rows: list[dict] = []
    old_argv, old_path = sys.argv[:], sys.path[:]
    started = datetime.now(timezone.utc).isoformat()
    try:
        sys.argv = [str(script), *args.arguments[1:]] if args.arguments[:1] == ["--"] else [str(script), *args.arguments]
        sys.path.insert(0, str(script.parent))
        with observe_requests(KINDS[script.name], rows):
            runpy.run_path(str(script), run_name="__main__")
        return 0
    finally:
        sys.argv, sys.path = old_argv, old_path
        report = summary(script, rows)
        report.update(started_at=started, ended_at=datetime.now(timezone.utc).isoformat())
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
