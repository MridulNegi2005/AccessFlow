"""Restore private recorded FDB outputs for scoring without rerunning inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from scripts import reproduce_fdb as fdb


def source_matches(path: Path, sha: str) -> bool:
    # Git may check out the same pinned text as CRLF on Windows and LF on Linux.
    # This allowance is for reference source only; audio/output hashes stay exact.
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    return sha in {hashlib.sha256(data).hexdigest() for data in (raw, lf, lf.replace(b"\n", b"\r\n"))}


def restore(evidence: Path, reference: Path) -> dict:
    evidence, reference = evidence.resolve(), reference.resolve()
    manifest_path = evidence / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("Evidence manifest must not be a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Evidence manifest must be an object")
    if manifest.get("fdb_commit") != fdb.PIN:
        raise ValueError("Recorded reference pin does not match the supported pin")
    if fdb.git_output(reference, "rev-parse", "HEAD") != fdb.PIN:
        raise ValueError("Target reference is not pinned")
    if fdb.git_output(reference, "status", "--porcelain", "--untracked-files=no", "--", "."):
        raise ValueError("Target reference has tracked modifications")
    hashes = manifest.get("source_sha256", {})
    if not isinstance(hashes, dict):
        raise ValueError("Recorded source hashes are invalid")
    for name in fdb.REQUIRED:
        target = reference / name
        if target.is_symlink() or not target.is_file() or not source_matches(target, hashes.get(name)):
            raise ValueError("Recorded and target reference sources differ")

    inputs = fdb.recordings(reference / "fdb_v3_data_released")
    saved_inputs = manifest.get("inputs", [])
    if not isinstance(saved_inputs, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("folder"), str) for row in saved_inputs
    ):
        raise ValueError("Recorded input inventory is invalid")
    folders = [row.get("folder") for row in saved_inputs if isinstance(row, dict)]
    if len(saved_inputs) != len(inputs) or len(set(folders)) != len(inputs):
        raise ValueError("Recorded inputs are missing or duplicated")
    saved = {row["folder"]: row for row in saved_inputs}
    target_inputs = {audio.parent.name: audio for audio in inputs}
    if set(saved) != set(target_inputs):
        raise ValueError("Recorded and target input sets differ")
    for folder, audio in target_inputs.items():
        if audio.parent.is_symlink():
            raise ValueError("Target input folder must not be a symlink")
        if saved[folder].get("sha256") != fdb.digest(audio):
            raise ValueError("Target input audio does not match the recorded run")

    # Validate every source and destination before copying any file. Never copy
    # expected answers, configuration, scripts, logs or arbitrary manifest paths.
    allowed = {
        f"result_{fdb.PROVIDER}.json",
        f"output_{fdb.PROVIDER}.wav",
        f"latency_tool_analysis_{fdb.PROVIDER}.json",
    }
    rows = manifest.get("retained_outputs", [])
    if not isinstance(rows, list):
        raise ValueError("Retained output inventory is invalid")
    plan, seen, result_statuses = [], set(), {}
    for row in rows:
        path = row.get("path") if isinstance(row, dict) else None
        if path == "room_tool_calls.jsonl":
            continue  # Scorers consume the room calls already in result JSON.
        if not isinstance(path, str) or "\\" in path:
            raise ValueError("Invalid retained output path")
        parts = path.split("/")
        if (
            len(parts) != 3
            or parts[0] != "results"
            or parts[1] not in target_inputs
            or parts[2] not in allowed
            or path in seen
        ):
            raise ValueError("Unexpected or duplicate retained output path")
        seen.add(path)
        source = evidence / path
        if (
            any(parent.is_symlink() for parent in (source, source.parent, source.parent.parent))
            or not source.is_file()
            or not source.resolve().is_relative_to(evidence)
        ):
            raise ValueError("Retained output is missing or escapes its evidence directory")
        sha = row.get("sha256")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha) or fdb.digest(source) != sha:
            raise ValueError("Retained output checksum mismatch")
        destination = target_inputs[parts[1]].parent / parts[2]
        if destination.is_symlink() or (
            destination.exists() and (not destination.is_file() or fdb.digest(destination) != sha)
        ):
            raise ValueError("Existing target output differs; use a fresh released-data checkout")
        if parts[2] == f"result_{fdb.PROVIDER}.json":
            result = json.loads(source.read_text(encoding="utf-8"))
            status = result.get("status") if isinstance(result, dict) else None
            if not isinstance(status, str):
                raise ValueError("Recorded result has no valid status")
            result_statuses[status] = result_statuses.get(status, 0) + 1
        plan.append((source, destination))
    recorded = manifest.get("results", {})
    if (
        not isinstance(recorded, dict)
        or sum(result_statuses.values()) != len(inputs)
        or not result_statuses.get("completed")
        or recorded.get("expected") != len(inputs)
        or recorded.get("missing") != []
        or recorded.get("status_counts") != result_statuses
    ):
        raise ValueError("Recorded result coverage/statuses do not match a completed inference run")
    copied = 0
    for source, destination in plan:
        if not destination.exists():
            shutil.copyfile(source, destination)
            copied += 1
    return {
        "status": "recorded_outputs_restored_not_scored",
        "recordings": len(inputs),
        "files_copied": copied,
        "already_present": len(plan) - copied,
        "source_manifest_sha256": fdb.digest(manifest_path),
        "recorded_agent_commit": manifest.get("agent_commit"),
        "result_status_counts": result_statuses,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence", type=Path, required=True, help="Private run directory containing manifest.json"
    )
    parser.add_argument(
        "--fdb-root", type=Path, required=True, help="Fresh pinned official checkout's v3 directory"
    )
    args = parser.parse_args(argv)
    try:
        report = restore(args.evidence, args.fdb_root)
    except (ValueError, KeyError, TypeError, OSError) as error:
        # No arbitrary source text/provider messages are disclosed.
        parser.exit(1, f"Restore failed ({type(error).__name__}); original files preserved\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
