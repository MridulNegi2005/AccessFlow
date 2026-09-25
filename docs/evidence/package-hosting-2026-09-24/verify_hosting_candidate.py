# ruff: noqa: E402
import asyncio
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import time

root = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root))
import accessflow
import eval_submission
from hosting.start_vision_server import service

assert Path(accessflow.__file__).resolve().is_relative_to(root)
manifest = json.loads((root / "package_manifest.json").read_text())
for name, expected in manifest["files"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
pins = (root / "requirements.txt").read_text().splitlines()
for pin in pins:
    name, expected = pin.split("==")
    assert version(name) == expected, name
config, cls, errors = eval_submission.validate_submission(str(root))
assert not errors and config["requirements"] == pins
profile = json.loads((root / "runtime_profile.json").read_text())
report = {"mode": "isolated-package-installed-service-and-full-real-setup", "python": sys.version,
    "platform": platform.platform(), "package_files_verified": len(manifest["files"]),
    "pins_verified": len(pins), "profile": profile,
    "package_manifest_sha256": hashlib.sha256((root / "package_manifest.json").read_bytes()).hexdigest(),
    "limitations": ["Reused isolated Windows venv; no Docker/Linux execution.",
        "Setup uses installation fixtures and hosted Qwen readiness only; no official task score."]}

async def setup():
    agent = cls(asyncio.Queue(), asyncio.Queue())
    started = time.monotonic()
    try:
        await asyncio.wait_for(agent.setup(), 300)
        report["warmup_backends"] = agent.agent.perception_warmup_backends
        report["reasoner_backend"] = agent.agent.reasoner.backend.name
    finally:
        report["setup_s"] = time.monotonic() - started
        if agent.agent is not None:
            await agent.agent.perception.aclose()

try:
    with service(profile, executable="D:/AccessFlow-LocalRuntime/ollama-v0.34.0/ollama.exe",
                 models_dir="D:/AccessFlow-LocalRuntime/models", log_path=output.with_suffix(".service.log"),
                 expected_version="0.34.0",
                 expected_digest="a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a") as (child, ready):
        report["service"] = ready
        asyncio.run(setup())
    report["service_exit_code"] = child.poll()
    report["failure"] = None
except Exception as error:
    report["failure"] = type(error).__name__
finally:
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
if report["failure"]:
    raise SystemExit(1)
