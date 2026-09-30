# Development commands

Use Python 3.11 and `uv` from the repository root:

```powershell
uv sync --frozen --extra dev --extra fdb
uv run --frozen --extra dev --extra fdb python -m pytest -q
uv run --frozen --extra dev ruff check .
uv run --frozen accessflow replay scenarios/dev/text_correction.json
uv run --frozen accessflow suite scenarios/dev --output-dir artifacts/development-suite
uv run --frozen accessflow responsiveness --samples 100 --output-dir artifacts/responsiveness
```

Replay scenarios use mock tools and are development checks, not the released voice
benchmark. Output artifacts and private provider settings stay outside Git.
Input-receipt latency differs from speech-end latency; missing calibrated timing data
must remain unmeasured.

For the voice worker and navigation dashboard, follow the [README](../README.md).
For released audio, GPU dependencies and saved-result grading, use
[FDB reproduction](FDB_REPRODUCTION.md).

The Docker image runs offline text replay:

```powershell
docker build -t accessflow .
docker run --rm accessflow
```

Corrected container execution is unverified in the current environment. The image has
no model weights and does not replace the prepared FDB voice-evaluation environment.
