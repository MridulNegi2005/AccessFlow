"""Preflight and supervise the pinned official FDB-v3 pipeline; never submit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import wave

PIN = "3e799c45a045256f47d5f1c9cda90157e2d2ec9e"
PROVIDER = "accessflow"
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("mock_apis.py", "latency_injector.py", "livekit_inference.py",
            "run_tool_benchmark_all_released.py", "evaluate_tool_calls.py",
            "evaluate_pass_rate.py", "analyze_tool_latency.py", "benchmark_data_v2.json")
CONFIG = {
    "FDB_PLANNER_PROVIDER": "livekit", "FDB_LIVEKIT_MODEL": "openai/gpt-5.6-luna",
    "FDB_GROQ_MODEL": "qwen/qwen3.8-27b", "FDB_GROQ_STT_MODEL": "whisper-large-v3",
    "FDB_TTS_PROVIDER": "livekit", "FDB_PROMPT_PROFILE": "compact-v2",
    "FDB_LATENCY_PROFILE": "instant", "ACCESSFLOW_MAX_OUTPUT_TOKENS": "950",
    "ACCESSFLOW_MAX_CONTEXT_CHARS": "32768", "ACCESSFLOW_GROQ_STRUCTURED": "0",
}


def git_output(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def recordings(data: Path, expected: int = 100) -> list[Path]:
    """Match the released runner's flat layout without consuming answer labels."""
    if not data.is_dir():
        raise ValueError("Released recording directory is missing")
    result = []
    for folder in sorted(data.iterdir()):
        if not folder.is_dir() or not re.fullmatch(r".+_[0-9a-f]{24}", folder.name):
            continue
        audio, metadata = folder / "input.wav", folder / "metadata.json"
        for asset in (audio, metadata):
            if not asset.is_file() or asset.is_symlink() or not asset.resolve().is_relative_to(data.resolve()):
                raise ValueError("Released input is missing or escapes its data directory")
        with wave.open(str(audio), "rb") as wav:
            if wav.getnframes() == 0 or wav.getframerate() != 48000 or wav.getcomptype() != "NONE":
                raise ValueError("Expected nonempty 48 kHz PCM released WAV recordings")
        result.append(audio)
    if len(result) != expected:
        raise ValueError(f"Expected {expected} released recordings, found {len(result)}")
    return result


def commands(fdb: Path, scorer: str, evidence: Path, *, semantic: bool = True) -> list[list[str]]:
    data = str(fdb / "fdb_v3_data_released")
    benchmark = str(fdb / "benchmark_data_v2.json")
    judge = ["--use-llm"] if semantic else []
    return [
        [scorer, str(fdb / "run_tool_benchmark_all_released.py"), "--provider", PROVIDER,
         "--root_dir", data],
        [scorer, str(fdb / "evaluate_tool_calls.py"), "--provider", PROVIDER,
         "--benchmark", benchmark, "--results-dir", data, "--output",
         str(evidence / "tool_accuracy.json"), *judge],
        [scorer, str(fdb / "evaluate_pass_rate.py"), "--provider", PROVIDER,
         "--benchmark", benchmark, "--results-dir", data, "--output",
         str(evidence / "strict_pass_rate.json"), *judge],
        [scorer, str(fdb / "analyze_tool_latency.py"), "--provider", PROVIDER,
         "--results-dir", data, "--output", str(evidence / "latency.json")],
    ]


def verify_results(inputs: list[Path]) -> dict:
    """The upstream batch can exit zero while individual examples fail."""
    states: dict[str, int] = {}
    missing = []
    for audio in inputs:
        path = audio.parent / f"result_{PROVIDER}.json"
        if not path.is_file() or path.is_symlink():
            missing.append(audio.parent.name)
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
            status = row.get("status", "missing_status") if isinstance(row, dict) else "malformed"
            if not isinstance(status, str):
                status = "malformed"
        except (ValueError, OSError):
            status = "malformed"
        states[status] = states.get(status, 0) + 1
    return {"expected": len(inputs), "missing": missing, "status_counts": states}


def verify_reports(evidence: Path, expected: int) -> None:
    for name in ("tool_accuracy.json", "strict_pass_rate.json"):
        report = json.loads((evidence / name).read_text(encoding="utf-8"))
        if type(report.get("total_scenarios")) is not int or report["total_scenarios"] != expected:
            raise ValueError(f"{name} does not cover the declared {expected}-recording denominator")
    if not (evidence / "latency.json").is_file():
        raise ValueError("Official latency report is missing")


def preserve_outputs(inputs: list[Path], evidence: Path, telemetry: Path) -> list[dict]:
    """Copy generated outputs, never expected answers, into the private run."""
    retained = []
    rooms = set()
    for audio in inputs:
        folder = evidence / "results" / audio.parent.name
        for name in (f"result_{PROVIDER}.json", f"output_{PROVIDER}.wav",
                     f"latency_tool_analysis_{PROVIDER}.json"):
            source = audio.parent / name
            if not source.is_file() or source.is_symlink():
                continue
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / name
            shutil.copyfile(source, target)
            retained.append({"path": str(target.relative_to(evidence)), "sha256": digest(target)})
            if name == f"result_{PROVIDER}.json":
                try:
                    row = json.loads(source.read_text(encoding="utf-8"))
                    if isinstance(row, dict) and isinstance(row.get("room_name"), str):
                        rooms.add(row["room_name"])
                except ValueError:
                    pass  # Preserve malformed output honestly; verification fails separately.
    if telemetry.is_file() and rooms:
        target = evidence / "room_tool_calls.jsonl"
        with telemetry.open(encoding="utf-8") as source, target.open("w", encoding="utf-8") as out:
            for line in source:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get("room") in rooms:
                    out.write(json.dumps(row) + "\n")
        retained.append({"path": target.name, "sha256": digest(target)})
    return retained


def sanitized_config(env: dict[str, str]) -> dict:
    # Explicit allowlist only: never serialize arbitrary environment variables.
    return {name: env.get(name, default) for name, default in CONFIG.items()}


def stop_worker(worker: subprocess.Popen, timeout: float = 10) -> None:
    """Stop only the process started by this invocation."""
    if worker.poll() is None:
        worker.terminate()
        try:
            worker.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait()


def wait_registered(worker: subprocess.Popen, log: Path, timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if worker.poll() is not None:
            raise RuntimeError("Worker exited before registration; inspect private worker.log")
        if log.exists() and "registered worker" in log.read_text(encoding="utf-8", errors="replace").lower():
            return
        time.sleep(0.25)
    raise TimeoutError("Worker registration not observed before timeout")


def preflight(fdb: Path, scorer: str, env: dict[str, str], *, need_runtime: bool = True,
              need_inference: bool = True, need_judge: bool = True) -> dict:
    if git_output(fdb, "rev-parse", "HEAD") != PIN:
        raise ValueError("FDB reference commit does not match the declared pin")
    if git_output(fdb, "status", "--porcelain", "--untracked-files=no", "--", "."):
        raise ValueError("Pinned FDB-v3 tracked files were modified")
    if any(not (fdb / name).is_file() for name in REQUIRED):
        raise ValueError("Incomplete official v3 source checkout")
    if need_inference and not (ROOT / "src/accessflow/perception/fdb_v3/agent.py").is_file():
        raise ValueError("FDB worker is absent: integrate the reviewed B implementation first")
    data = fdb / "fdb_v3_data_released"
    inputs = recordings(data)
    if not Path(scorer).is_file():
        raise ValueError("Supply an existing separate scorer Python executable")
    if need_inference and shutil.which("ffmpeg") is None:
        raise ValueError("ffmpeg is required on PATH")
    keys = (["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"] if need_inference else [])
    if need_judge:
        keys.append("OPENAI_API_KEY")
    missing = [key for key in keys
               if not env.get(key)]
    if need_inference and not any(env.get(key) for key in ("ACCESSFLOW_GROQ_API_KEY", "GROQ_API_KEY", "SECRET_GROQ_API_KEY")):
        missing.append("ACCESSFLOW_GROQ_API_KEY or GROQ_API_KEY")
    if missing:
        raise ValueError("Missing private settings: " + ", ".join(missing))
    if env.get("FDB_PLANNER_PROVIDER", "livekit") not in {"livekit", "groq"}:
        raise ValueError("Unsupported planner provider")
    if env.get("FDB_TTS_PROVIDER", "livekit") not in {"livekit", "groq"}:
        raise ValueError("Unsupported TTS provider")
    if need_runtime:
        # Import discovery does not load NeMo model weights or send API requests.
        modules = ["openai", "dotenv"] + (["nemo", "numpy", "pydub", "livekit"] if need_inference else [])
        probe = f"import importlib.util; assert all(importlib.util.find_spec(x) for x in {modules!r}), 'Missing scorer dependencies'"
        subprocess.run([scorer, "-c", probe], check=True, cwd=fdb, env=env)
        if need_inference:
            subprocess.run([sys.executable, "-m", "accessflow.perception.fdb_v3.agent", "check"],
                           check=True, cwd=ROOT, env=env)
    return {"fdb_commit": PIN, "input_count": len(inputs), "source_sha256": {
        name: digest(fdb / name) for name in REQUIRED}, "config": sanitized_config(env),
        "inputs": [{"folder": audio.parent.name, "sha256": digest(audio)} for audio in inputs]}


def run_pipeline(args, env: dict[str, str]) -> dict:
    fdb, evidence = args.fdb_root.resolve(), args.output.resolve()
    if evidence.exists():
        raise ValueError("Use a new output directory for each invocation; prior evidence is preserved")
    evidence.mkdir(parents=True)
    manifest = {"started_at": datetime.now(timezone.utc).isoformat(), "status": "started",
                "mode": args.mode, "scoring": "exact-match diagnostic" if args.exact_match else "official scripts with semantic judge",
                "judge_verification": "Upstream may silently fall back to exact matching; judge execution is not independently verified by this supervisor",
                "agent_commit": git_output(ROOT, "rev-parse", "HEAD"),
                "agent_tree_dirty": bool(git_output(ROOT, "status", "--porcelain")),
                "seed_policy": "Official scripts expose no seed option; configuration and input hashes retained"}
    worker = None
    try:
        manifest.update(preflight(fdb, args.scorer_python, env,
                                  need_inference=args.mode != "score", need_judge=args.mode != "run"))
        inputs = recordings(fdb / "fdb_v3_data_released")
        plan = commands(fdb, args.scorer_python, evidence, semantic=not args.exact_match)
        manifest["commands"] = plan
        if args.mode == "doctor":
            manifest["status"] = "preflight_passed_not_evaluated"
            return manifest
        if args.mode in {"run", "reproduce"}:
            existing = [audio for audio in inputs if any((audio.parent / name).exists() for name in
                        (f"result_{PROVIDER}.json", f"output_{PROVIDER}.wav"))]
            if existing and not args.overwrite_results:
                raise ValueError("Existing results/audio would be reused by upstream; use --overwrite-results explicitly or a fresh data copy")
            if args.overwrite_results:
                plan[0].append("--force")
            with (evidence / "worker.log").open("w", encoding="utf-8") as log:
                worker = subprocess.Popen([sys.executable, "-m", "accessflow.perception.fdb_v3.agent", "start"],
                                          cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                wait_registered(worker, evidence / "worker.log", args.registration_timeout)
                subprocess.run(plan[0], check=True, cwd=fdb, env=env)
                stop_worker(worker)
        results = verify_results(inputs)
        manifest["results"] = results
        telemetry = Path(fdb.anchor) / "tmp/agent_tool_calls.log"
        manifest["retained_outputs"] = preserve_outputs(inputs, evidence, telemetry)
        if results["missing"] or results["status_counts"].get("malformed"):
            raise ValueError("Incomplete/malformed results: a complete aggregate cannot be claimed")
        if args.mode in {"score", "reproduce"}:
            for command in plan[1:]:
                subprocess.run(command, check=True, cwd=fdb, env=env)
            verify_reports(evidence, len(inputs))
            manifest["retained_outputs"] = preserve_outputs(inputs, evidence, telemetry)
            manifest["status"] = "scored_with_recorded_outcomes"
        else:
            manifest["status"] = "inference_recorded_not_scored"
        # Capture exact resolved installations, not secrets or input answers.
        for name, executable in (("agent", sys.executable), ("scorer", args.scorer_python)):
            result = subprocess.run([executable, "-m", "pip", "freeze"], capture_output=True, text=True)
            if result.returncode == 0:
                (evidence / f"{name}_freeze.txt").write_text(result.stdout, encoding="utf-8")
            else:
                manifest[f"{name}_freeze_unavailable"] = True
        return manifest
    except BaseException as error:
        manifest["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        # Known configuration errors are value-free. Child errors disclose only type/code.
        manifest["failure"] = str(error) if isinstance(error, (ValueError, TimeoutError, RuntimeError)) else type(error).__name__
        raise
    finally:
        if worker is not None:
            stop_worker(worker)
        manifest["ended_at"] = datetime.now(timezone.utc).isoformat()
        (evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fdb-root", type=Path, required=True, help="Pinned official clone's v3 directory")
    parser.add_argument("--scorer-python", required=True, help="Separate scorer environment Python")
    parser.add_argument("--output", type=Path, required=True, help="New private evidence directory")
    parser.add_argument("--mode", choices=("doctor", "run", "score", "reproduce"), default="doctor")
    parser.add_argument("--exact-match", action="store_true", help="Label tool scoring diagnostic, not semantic judge scoring")
    parser.add_argument("--overwrite-results", action="store_true", help="Explicitly let upstream replace existing result files")
    parser.add_argument("--registration-timeout", type=float, default=90)
    args = parser.parse_args(argv)
    args.scorer_python = str(Path(args.scorer_python).resolve())
    if not 1 <= args.registration_timeout <= 600:
        parser.error("Registration timeout must be between 1 and 600 seconds")
    env = dict(os.environ)
    try:
        from dotenv import dotenv_values
        for key, value in dotenv_values(args.fdb_root / ".env.local").items():
            if value is not None:
                env.setdefault(key, value)
        for key, value in CONFIG.items():
            env.setdefault(key, value)
        env["FDB_V3_ROOT"] = str(args.fdb_root.resolve())
        # Scorer always reads this rooted path, not the worker's custom override.
        env["FDB_TOOL_LOG"] = str(Path(args.fdb_root.resolve().anchor) / "tmp/agent_tool_calls.log")
        env["PYTHONUTF8"] = "1"
        result = run_pipeline(args, env)
    except (ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError, OSError, ImportError) as error:
        print(str(error) if isinstance(error, (ValueError, RuntimeError, TimeoutError)) else
              f"Reproduction prerequisite/process failed ({type(error).__name__}); inspect private evidence", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "evidence": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
