"""Private Kaggle GPU preparation; full cloud evaluation is an explicit second run.

Uses unchanged pinned FDB-v3 scripts and separate agent/scorer environments.
No credential values are printed or saved to notebook outputs.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

AGENT_PIN = "91e3b8d76083135cdef38550c0360b7765c80c5f"
FDB_PIN = "3e799c45a045256f47d5f1c9cda90157e2d2ec9e"
ARCHIVE_SHA = "37545bd896f81718136598cf5be25d42ea9aa22efcd91f58370938d05d7d672f"
WORK = Path("/tmp/accessflow-fdb")
EVIDENCE = Path("/kaggle/working/accessflow-fdb/evidence")
SECRETS = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
           "OPENAI_API_KEY", "ACCESSFLOW_GROQ_API_KEY")


def command(args, *, cwd=None, env=None, log=None):
    if log is None:
        subprocess.run([str(x) for x in args], check=True, cwd=cwd, env=env)
    else:
        with log.open("w", encoding="utf-8") as stream:
            subprocess.run([str(x) for x in args], check=True, cwd=cwd, env=env,
                           stdout=stream, stderr=subprocess.STDOUT)


def extract_corpus(archive: Path, destination: Path):
    """Verify the released archive and reject escaping/symlink members."""
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != ARCHIVE_SHA:
        raise ValueError("Released archive checksum mismatch")
    base = destination.resolve()
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (base / member.filename).resolve()
            if (not target.is_relative_to(base) or "\\" in member.orig_filename
                    or (member.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError("Unsafe archive member")
        zipped.extractall(base)


def prepare():
    if sys.platform != "linux" or not Path("/kaggle/working").is_dir():
        raise ValueError("Run this script inside a private Kaggle GPU notebook")
    WORK.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    command(["nvidia-smi"], log=EVIDENCE / "gpu.txt")
    command([sys.executable, "-m", "pip", "install", "uv==0.11.16"],
            log=EVIDENCE / "uv-install.log")
    uv = shutil.which("uv")
    if uv is None:
        raise ValueError("uv install did not provide its executable")
    if shutil.which("ffmpeg") is None:
        command(["apt-get", "update"], log=EVIDENCE / "apt-update.log")
        command(["apt-get", "install", "-y", "ffmpeg"], log=EVIDENCE / "ffmpeg-install.log")
    agent, reference = WORK / "AccessFlow", WORK / "Full-Duplex-Bench"
    for folder, url, pin in (
        (agent, "https://github.com/MridulNegi2005/AccessFlow.git", AGENT_PIN),
        (reference, "https://github.com/DanielLin94144/Full-Duplex-Bench.git", FDB_PIN),
    ):
        if not folder.exists():
            command(["git", "clone", url, folder], log=EVIDENCE / f"{folder.name}-clone.log")
        command(["git", "-C", folder, "checkout", "--detach", pin],
                log=EVIDENCE / f"{folder.name}-checkout.log")
    scorer_env = WORK / "scorer-env"
    scorer = scorer_env / "bin/python"
    if not scorer.exists():
        command([uv, "venv", "--python", "3.10", "--seed", scorer_env],
                log=EVIDENCE / "scorer-create.log")
    # Candidate compatibility profile, not a claimed tested lock until GPU probe succeeds.
    command([uv, "pip", "install", "--python", scorer, "torch==2.6.0", "torchaudio==2.6.0",
             "--index-url", "https://download.pytorch.org/whl/cu124"],
            log=EVIDENCE / "torch-install.log")
    command([uv, "pip", "install", "--python", scorer,
             "nemo_toolkit[asr]==2.4.0", "numpy==1.26.4", "huggingface-hub<1",
             "transformers==4.51.3", "livekit==1.1.2", "openai==1.109.1",
             "python-dotenv==1.2.3", "pydub==0.25.1", "ffmpeg-python==0.2.0", "gdown==5.2.0"],
            log=EVIDENCE / "scorer-install.log")
    command([uv, "pip", "check", "--python", scorer], log=EVIDENCE / "scorer-dependency-check.log")
    env = dict(os.environ)
    env["UV_PROJECT_ENVIRONMENT"] = str(agent / ".venv-fdb")
    command([uv, "sync", "--project", agent, "--python", "3.11", "--frozen", "--no-dev",
             "--extra", "fdb"], env=env, log=EVIDENCE / "agent-install.log")
    command([scorer, "-m", "pip", "freeze"], log=EVIDENCE / "scorer-freeze.txt")
    fdb = reference / "v3"
    # Actual unchanged official loader, GPU transfer and a synthetic silence smoke test.
    probe = """import json,time,torch,numpy as np
from run_tool_benchmark import load_asr_model
assert torch.cuda.is_available(), 'CUDA is unavailable'
t=time.monotonic(); model=load_asr_model()
model.transcribe([np.zeros(16000,dtype=np.float32)],batch_size=1)
print(json.dumps({'status':'gpu_model_and_silence_probe_passed',
 'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,
 'cuda':torch.version.cuda,'seconds':time.monotonic()-t}))
"""
    command([scorer, "-c", probe], cwd=fdb, log=EVIDENCE / "nemo-gpu-health.log")
    archive = WORK / "fdb_v3_data_released.zip"
    if not archive.exists():
        command([scorer, "-m", "gdown", "1SO_4MTazWQ_jvCx0dtmpQ-t40bdd07yz", "-O", archive],
                log=EVIDENCE / "corpus-download.log")
    if not (fdb / "fdb_v3_data_released").is_dir():
        extract_corpus(archive, fdb)
    return agent, fdb, scorer


def main():
    report = {"agent_commit": AGENT_PIN, "fdb_commit": FDB_PIN,
              "status": "started", "mode": os.environ.get("ACCESSFLOW_KAGGLE_MODE", "prepare"),
              "scope": "GPU setup is not an agent benchmark or microphone test"}
    try:
        agent, fdb, scorer = prepare()
        from kaggle_secrets import UserSecretsClient
        client = UserSecretsClient()
        env = dict(os.environ)
        missing = []
        for name in SECRETS:
            try:
                value = client.get_secret(name)
            except Exception:
                value = None
            if value:
                env[name] = value
            elif not env.get(name):
                missing.append(name)
        report["missing_secret_names"] = missing
        report["status"] = "gpu_setup_passed_runtime_not_evaluated"
        if report["mode"] not in {"prepare", "run", "reproduce"}:
            raise ValueError("Use prepare, run or reproduce mode")
        if report["mode"] in {"run", "reproduce"}:
            required_missing = [name for name in missing
                                if name != "OPENAI_API_KEY" or report["mode"] == "reproduce"]
            if required_missing:
                raise ValueError("Required Kaggle Secrets are not attached")
            run = EVIDENCE / f"official-run-{time.time_ns()}"
            # The supervisor performs preflight before starting its worker.
            # Run-only mode can gather real outputs while judge credit is unavailable.
            command([agent / ".venv-fdb/bin/python", agent / "scripts/reproduce_fdb.py",
                     "--fdb-root", fdb, "--scorer-python", scorer, "--output", run,
                     "--mode", report["mode"]], env=env, log=EVIDENCE / "reproduce.log")
            report["status"] = ("inference_finished_not_scored" if report["mode"] == "run"
                                else "official_supervised_run_finished_inspect_manifest")
    except Exception as error:
        report["status"] = "failed"
        # Do not print exceptions from SDKs that might contain credential values.
        report["failure_type"] = type(error).__name__
    finally:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "kaggle-status.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    return int(report["status"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
