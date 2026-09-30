# Reproduce AccessFlow on Full-Duplex-Bench v3

AccessFlow runs its interruptible voice controller in LiveKit rooms and uses the unchanged released FDB-v3 tools and evaluator. Agent and scorer run in separate Python environments on the same host.

## Prerequisites

- Agent: Python 3.11, Git and `uv`.
- Inference/scorer host: ffmpeg on PATH and the pinned reference's compatible Python 3.10, Torch/CUDA and NeMo environment.
- Hosted providers: LiveKit project credentials and Groq speech-recognition access.
- Semantic and latency grading: independent OpenAI API access required by the unchanged public reference scripts.

Samsung's guide says its organizer rerun uses one pinned judge. It does not explicitly require teams to purchase OpenAI credit. The public reference calls `gpt-4o`; a different judge must be labelled a separate diagnostic, not the same benchmark score.

## Install and prepare the reference

From the AccessFlow repository root:

```powershell
uv sync --frozen --extra fdb
git clone --filter=blob:none --no-checkout https://github.com/DanielLin94144/Full-Duplex-Bench.git C:\FDB-reference
git -C C:\FDB-reference sparse-checkout set --cone v3
git -C C:\FDB-reference checkout --detach 3e799c45a045256f47d5f1c9cda90157e2d2ec9e
```

Sparse checkout avoids irrelevant older-version Windows path-length problems. Download the released ZIP linked in the [pinned reference README](https://github.com/DanielLin94144/Full-Duplex-Bench/blob/3e799c45a045256f47d5f1c9cda90157e2d2ec9e/v3/README.md). Extract `fdb_v3_data_released` under `C:\FDB-reference\v3`. Preserve all 100 original `input.wav` files and their released per-folder metadata. The validated originals include 93 at 48 kHz and seven at 16 kHz; do not rewrite them. The official reader normalizes playback using ffmpeg.

The agent never receives benchmark expected answers. Do not modify official scripts, scenario labels or tool definitions.

## Private configuration

Copy `.env.fdb.example` to `C:\FDB-reference\v3\.env.local`, or a separate private file supplied with `--env-file`. Never commit populated settings or include keys in video/screenshots.

Required runtime names: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `ACCESSFLOW_GROQ_API_KEY`. `OPENAI_API_KEY` is needed for reference judging, independently of agent planning.

Declared profile:

| Component | Selection |
| --- | --- |
| Speech input | Groq `whisper-large-v3` |
| Planning | `FDB_PLANNER_PROVIDER=livekit`, `FDB_LIVEKIT_MODEL=openai/gpt-5.6-luna` |
| Speech output | `FDB_TTS_PROVIDER=livekit`, Deepgram Aura-2 |
| Prompt profile | `FDB_PROMPT_PROFILE=compact-v2` |

Optional Groq planning uses `FDB_PLANNER_PROVIDER=groq` and `FDB_GROQ_MODEL`. Record the actual profile; no silent fallback or mixed-backend score is permitted. Provider usage is subject to its configured quotas/billing.

Settings precedence is process environment, explicit private file, clone `.env.local`, then defaults. File values are literal, without `${...}` interpolation. Reference and telemetry paths are controlled by the supervisor.

## Prepare the separate scorer

Follow the pinned official README for a Python 3.10 environment with compatible Torch/CUDA, `nemo_toolkit[asr]`, LiveKit client dependencies, NumPy, pydub, ffmpeg-python, OpenAI and python-dotenv. The official client also needs the `livekit-api` distribution. Do not put GPU/NeMo packages into the agent environment.

The upstream reference has no exact scorer lock. Save resolved dependencies and hardware information with every run. A resolved `pip freeze` is not a hash-locked installation. The [Kaggle guide](KAGGLE_FDB.md) describes a tested candidate GPU profile.

## One-command installation and evaluation

On a prepared host, provide a tested hashed scorer requirements file:

```powershell
python scripts/bootstrap_fdb.py --fdb-root C:\FDB-reference\v3 --scorer-python C:\FDB-scorer\Scripts\python.exe --scorer-lock C:\FDB-scorer\requirements.lock --env-file C:\private\accessflow-fdb.env --output artifacts/fdb-final-run --mode reproduce
```

This installs the frozen agent and hash-checked scorer dependencies, then supervises inference and grading. If the scorer is already prepared, replace `--scorer-lock ...` with `--reuse-scorer`; that explicitly skips scorer installation/lock validation. Use Linux `bin/python` paths on Linux.

The default agent environment is `.venv-fdb/`. A custom `--agent-env` must be a dedicated repository subdirectory; inputs, scorer, keys and evidence must remain outside it. Existing evidence is not overwritten.

After prerequisites are installed, direct supervision is:

```powershell
uv run --frozen --extra fdb python -m scripts.reproduce_fdb --fdb-root C:\FDB-reference\v3 --scorer-python C:\FDB-scorer\Scripts\python.exe --env-file C:\private\accessflow-fdb.env --output artifacts/fdb-run-001 --mode reproduce
```

| Mode | Behavior |
| --- | --- |
| `doctor` | Preflight; no evaluation/provider request |
| `run` | Real audio inference without grading |
| `score` | Grade existing outputs without a live worker or GPU/NeMo |
| `reproduce` | Infer and grade all 100 released inputs |

The supervisor validates pins, corpus and dependency/key presence; starts the worker; waits for registration; streams the originals; stops its worker; runs unchanged tool, strict-pass and latency evaluators; validates full coverage. Semantic tool/pass grading is requested by default. `--exact-match` produces a labelled tool diagnostic; the latency analyzer still uses its LLM judge.

Existing result JSON or response audio blocks fresh inference unless `--overwrite-results` is explicitly supplied. Prefer a fresh data copy for a new run.

Worker and scorer must share telemetry. Linux uses `/tmp/agent_tool_calls.log`; Windows uses the `tmp` directory on the reference clone's drive. The supervisor sets `FDB_TOOL_LOG`. Do not run another unnamed worker, including the navigation extension worker, in the same project during evaluation.

## Runtime and targeted development

The 100 recordings contain approximately 78.6 minutes of audio. The released runner processes them sequentially; the LiveKit client publishes paced 20 ms chunks, followed by silence and room cleanup. ASR and provider requests add overhead. A full run taking over an hour is expected. GPU acceleration does not eliminate the real-time input clock.

Kaggle redirects subprocess output to `reproduce.log` and prints stage starts/ends. A long-running stage is not proof of a hang. Room activity is not a task-pass count; inspect final results and manifests.

For a small development subset, place selected original released folders in an isolated private directory and run:

```powershell
C:\FDB-scorer\Scripts\python.exe C:\FDB-reference\v3\run_tool_benchmark_all_released.py --provider accessflow --root_dir C:\FDB-development-subset
```

This low-level command does not start the worker, load private settings or apply full-run guards. First configure the environment and start exactly one matching worker on the same host with shared telemetry. Use a separate project/session if a full run is active. Record input hashes, source commit, configuration and actual outcomes. The released-layout CLI accepts `--root_dir`, not `--example` or `--pid`; those belong to the separate legacy-capable runner with different metadata handling. The supervised final run requires all 100 originals. A subset is development evidence only.

## Score a retained Kaggle run without repeating audio inference

Preserve the downloaded `official-run-.../manifest.json`, generated outputs and their original inference provenance. Prepare a fresh pinned reference/data copy, then restore:

```powershell
uv run --frozen --extra fdb python -m scripts.restore_fdb_evidence --evidence artifacts/kaggle-run/accessflow-fdb/evidence/official-run-... --fdb-root artifacts/fdb-reference/v3
uv venv --python 3.11 artifacts/fdb-score-env
uv pip install --python artifacts/fdb-score-env/Scripts/python.exe --require-hashes --requirements requirements/fdb-score.lock
uv run --frozen --extra fdb python -m scripts.reproduce_fdb --fdb-root artifacts/fdb-reference/v3 --scorer-python artifacts/fdb-score-env/Scripts/python.exe --env-file C:\private\accessflow-fdb.env --output artifacts/fdb-score-retained --mode score
```

Restoration checks clean reference/pin, 100 input hashes, output hashes and result/status coverage before copying. It rejects conflicting existing outputs, arbitrary paths and all-failure evidence. Mixed failures remain in the denominator. Identical existing outputs can be reused. Hash consistency does not establish authenticity or task correctness.

The lightweight score-only lock was installed on Windows/Python 3.11.15; all three scorer CLIs load. It omits NeMo, CUDA and agent media dependencies and is not an inference environment. Linux compatibility must be verified on that host.

Keep the original inference manifest alongside later scoring reports. New scoring does not validate new agent code: an agent change requires fresh inference outputs.

## Evidence integrity

Every started supervised invocation records `manifest.json`, including failures/interruption, with timestamps, source/reference pins, input hashes, configuration, commands and actual result counts. Official scripts expose no seed control. Successful inference retains result JSON, response WAVs and run-scoped tool telemetry. Upstream zero exit status alone cannot hide missing/malformed results or an all-failure batch.

The pinned graders can silently fall back to exact matching after judge errors. `scripts/fdb_judge_audit.py` observes the scorer's SDK requests without altering official prompts, responses or logic. Sanitized audit files record request counts, model, timing, token counts and reply/error structure; no prompts, expected answers, response text or keys are included. Failed/malformed requests fail supervised grading. No observed requests produces `scored_with_incomplete_judge_observation`, not verified semantic scoring. Audit transport validation does not establish judge accuracy.

Only the organizer rerun is Samsung's official score. Publish reviewed summaries and permitted artifacts; keep credentials, bulk benchmark audio and sensitive raw logs private. Setup, tests, room activity and manual microphone checks are distinct from scored benchmark completion. See [evaluation scope](EVALUATION_QUICK_GUIDE.md).

## Container boundary

```powershell
docker build -f Dockerfile.fdb -t accessflow-fdb .
```

`Dockerfile.fdb` is a candidate frozen voice-worker image; build/runtime have not been verified. Mount the reference at `/fdb/v3`, supply secrets privately and share `/tmp` telemetry with the separate scorer. This image does not install/run the official scorer. The original Dockerfile is an offline regression image.
