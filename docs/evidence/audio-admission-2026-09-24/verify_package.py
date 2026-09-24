# ruff: noqa: E402
import asyncio
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys
import time

root = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root))
import accessflow
import eval_submission as evaluator
from harness.runner import EvaluationHarness
from harness.scorer import score_scenario

assert Path(accessflow.__file__).resolve().is_relative_to(root)
manifest = json.loads((root / "package_manifest.json").read_text(encoding="utf-8"))
for name, expected in manifest["files"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
pins = (root / "requirements.txt").read_text().splitlines()
for pin in pins:
    name, expected = pin.split("==")
    assert importlib.metadata.version(name) == expected, name
config, cls, errors = evaluator.validate_submission(str(root))
assert not errors, errors
assert config["requirements"] == pins
scenario = json.loads((root / "scenarios/pub_06_audio_disfluency.json").read_text())
instances = []
def factory(incoming, outgoing):
    agent = cls(incoming, outgoing)
    instances.append(agent)
    return agent

async def main():
    harness = EvaluationHarness(scenario, factory, time_scale=1, verbose=False)
    started = time.monotonic()
    await asyncio.wait_for(harness.prepare(), 300)
    assert instances[-1].agent is not None, "Official setup failed"
    setup_s = time.monotonic() - started
    trace = await asyncio.wait_for(harness.run(), 120)
    return {"mode": "isolated-native-package/live-public-audio/single-attempt",
        "python": sys.version, "platform": platform.platform(),
        "files_verified": len(manifest["files"]), "pins_verified": len(pins),
        "import_errors": errors, "profile": json.loads((root / "runtime_profile.json").read_text()),
        "warmup_backends": instances[-1].agent.perception_warmup_backends,
        "setup_s": setup_s, "wall_s": time.monotonic() - started,
        "package_manifest_sha256": hashlib.sha256((root / "package_manifest.json").read_bytes()).hexdigest(),
        "trace": trace, "score": score_scenario(scenario, trace),
        "limitations": ["Reused previously fresh isolated venv on same Windows host; every pin rechecked.",
            "No microphone, vision, clean OS, Linux, Docker, repeated score or hidden-set claim."]}

result = asyncio.run(main())
output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in ("files_verified", "pins_verified", "setup_s", "wall_s")}))
print(json.dumps({"total": result["score"]["total"]}))
