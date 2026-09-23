# Isolated Windows package installation — 23 September 2026

Source: clean cd53bc23cdd1f9f540551ea8964df67219480588. All 78 generated package
file hashes verified before execution. Organizer files/media remain in the ignored
local package; this bundle contains only the verifier, results and build metadata.

Installed 21 exact pinned dependencies into a newly created Python 3.11.15 venv
using cached wheels. uv pip check reported all compatible. Ran the verifier with
Python -I from the package directory, removing ACCESSFLOW_* and Python import
path overrides from its environment before supplying the credential in memory.
The imported Samsung adapter was inside the generated package, not this repo.
The verifier records installed versions, platform and frozen runtime profile.

- Samsung package validation: no errors.
- Samsung contract startup probe: no errors (including bounded pre-manifest input).
- One pub_04_text_no_tool attempt: score100, no harness/agent failure, no tool calls.
  Substantive final at735ms; scorer10ms latency refers to an earlier response and
  is not the final-answer delay. Total verification wall time9.015s including setup.
- Defaults tested: full prompt, prose read mode, Groq Qwen qwen/qwen3.8-27b.
  This is not the optional compact-v2/evidence profile used in the text screen.

Reproduce in a fresh output directory from the named commit:

```powershell
python -m scripts.build_samsung_package --kit ../participant-kit/participant-kit --output artifacts/new-check/package --team AccessFlow --model qwen/qwen3.8-27b
uv venv --python 3.11 artifacts/new-check/venv
uv pip install --offline --python artifacts/new-check/venv/Scripts/python.exe -r artifacts/new-check/package/requirements.txt
uv pip check --python artifacts/new-check/venv/Scripts/python.exe
```

Copy verify_package.py.txt to artifacts/new-check/verify_package.py. In a shell with ACCESSFLOW_* and
Python path overrides cleared, supply SECRET_GROQ_API_KEY through the environment,
change into that package directory and run ../venv/Scripts/python.exe -I ../verify_package.py.
The verifier refuses to overwrite verification.json. Never put the credential in
this script or bundle. The local team label is not registration confirmation.

Limits: same Windows host, cached downloads, fresh environment rather than fresh
OS; no Docker command available in PATH; no Linux, hardware portability, raw-media
ASR/vision or repeated official score verified. The base requirements omit optional
ASR dependencies/weights, and Samsung media wiring remains incomplete. This closes
only the scoped base-package installation/import/startup check on this host.
