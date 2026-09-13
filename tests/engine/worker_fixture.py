"""Safe protocol fixture used by native perception subprocess tests.

This module is deliberately a test-only worker.  It never loads a model and is
selected explicitly through ``ProcessPerception(worker_module=...)``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def _observation(event: dict) -> dict:
    payload = event["payload"]
    if event["kind"] == "audio":
        source_id = payload["utterance_id"]
        revision = payload["revision"]
        modality = "audio"
        text = "fixture audio"
        start, end = payload["speech_start"], payload["speech_end"]
    else:
        source_id = payload["frame_id"]
        revision = 0
        modality = "image"
        text = "fixture image"
        start = end = event["timestamp"]
    return {
        "event_id": event["event_id"],
        "source_id": source_id,
        "revision": revision,
        "modality": modality,
        "text": text,
        "final": True,
        "speech_start": start,
        "speech_end": end,
        "backend": "fixture/native",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="echo")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--ready-file")
    args = parser.parse_args()
    for raw in sys.stdin.buffer:
        event = json.loads(raw)
        if args.mode == "block" and event["event_id"] == "block":
            if args.ready_file:
                Path(args.ready_file).write_text(str(os.getpid()))
            time.sleep(60)
        if args.mode == "eof":
            return
        if args.mode == "crash":
            os._exit(23)
        if args.mode == "malformed":
            sys.stdout.write("{not-json\n")
            sys.stdout.flush()
            continue
        if args.mode == "oversized":
            sys.stdout.write(json.dumps({"type": "observation", "observation": "x" * 300_000}) + "\n")
            sys.stdout.flush()
            continue
        if args.mode == "stderr":
            sys.stderr.write("fixture diagnostic " * 100_000)
            sys.stderr.flush()
        if args.mode == "native_stdout":
            from accessflow.adapters.perception_worker import _redirect_native_stdout
            with _redirect_native_stdout():
                print("Python provider diagnostic")
                os.write(1, b"Native provider diagnostic\n")
        sys.stdout.write(json.dumps({"type": "observation", "observation": _observation(event)}) + "\n")
        sys.stdout.write(json.dumps({"type": "done"}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
