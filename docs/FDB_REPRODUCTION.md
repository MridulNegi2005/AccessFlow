# FDB-v3 reproduction — 30 September 2026

This is the current Theme 5 target. The older queue kit and `SAMSUNG_PACKAGE.md`
are historical development paths, not the final FDB evaluation interface.

Mridul owns the dependency lock, supervisor and packaging. Atishay owns the
LiveKit worker, bridge, speech and tool adapter. Both must verify the integrated
worker and scorer on the same evaluation host.

## Verified and still open

The optional `fdb` dependency set is now in `pyproject.toml` and `uv.lock`.
`uv sync --frozen --extra dev --extra audio --extra fdb` installed successfully
on this Windows/Python 3.11 machine. The lock retains existing core pins.
Current A software suite: 1,504 passed / 6 skipped / two existing dependency
warnings in 72.61 seconds. Sixteen offline supervisor tests pass. Ruff passes.

In a temporary combined checkout of B `bafbbcf` and A `5c8243b`, the suite has
1,525 passing tests / 6 skips / one obsolete B contract assertion failing.
Atishay must replace
`test_current_contract_cannot_bind_a_single_unmatched_search_result` after
pulling the A change. The two newly repaired B control/persistence paths have
passing regression tests. This is not a final green merged-tree claim.

An offline worker `check` with dummy credentials and the real pinned mock registry
passed dependency/import/signature checks. It made no model/LiveKit request and
does not prove credentials, audio, registration or task accuracy.

The supervisor's actual local doctor invocation failed because this A checkout
does not yet contain the unmerged B worker. The released recording directory and
NeMo are also absent here. No required keys are present in the tested process.
No full score or physical microphone result is claimed. Atishay's runtime and
recordings on his own machine are not automatically available here.

## Install the agent

Use Python 3.11, Git and `uv`. First integrate the reviewed owner changes and
resolve the obsolete B assertion. From a clean repository checkout:

```powershell
uv sync --frozen --extra fdb
```

The optional lock uses Atishay's exact direct pins:
`livekit-agents[groq,silero]==1.8.3` and `python-dotenv==1.2.3`.
Normal text/offline development does not need this extra. Speech transcription
uses Groq; this worker does not require local Faster Whisper or Gemma weights.

## Prepare the unchanged official reference

```powershell
git clone --filter=blob:none --no-checkout https://github.com/DanielLin94144/Full-Duplex-Bench.git C:\FDB-reference
git -C C:\FDB-reference sparse-checkout set --cone v3
git -C C:\FDB-reference checkout --detach 3e799c45a045256f47d5f1c9cda90157e2d2ec9e
```

Sparse checkout avoids irrelevant older-version `node_modules` paths that exceed
Windows filename limits. Do not modify the official scripts or benchmark labels.
Use the [data link in the pinned official README](https://github.com/DanielLin94144/Full-Duplex-Bench/blob/3e799c45a045256f47d5f1c9cda90157e2d2ec9e/v3/README.md).
Download the released ZIP, extract `fdb_v3_data_released` under `C:\FDB-reference\v3`.
The supervisor requires 100 nonempty 48 kHz PCM `input.wav` files, each in the
released `{example_id}_{24-hex-speaker-id}` directory with its metadata file.
It checks and hashes recordings, but never supplies expected answers to the agent.

## Configure privately

Copy `.env.fdb.example` to the official clone's `v3/.env.local` and fill it there.
Keep this file outside the AccessFlow repository. Existing environment variables
take precedence. Review candidate models and account access before the full run.

The candidate profile matches B's reported working setup: Groq Whisper Large v3
input, LiveKit planning, LiveKit Deepgram Aura-2 output. Optional Groq planning
uses `FDB_PLANNER_PROVIDER=groq` and `FDB_GROQ_MODEL`, not the navigation worker's
selector. Do not silently fall back to another provider or combine different
profiles into one score. LiveKit provider usage is billed/configured through
its project. Groq's documented input-token-per-minute limit can affect planning.

`OPENAI_API_KEY` is for the official semantic judge and latency analyzer,
independently of the agent's planner. An exact-match tool diagnostic is labeled
as such; the pinned latency analyzer still requires this key.

## Prepare the scorer separately on the same host

Use the Python 3.10 environment described in the pinned official README. It
needs LiveKit client dependencies, NumPy, `nemo_toolkit[asr]`, pydub,
ffmpeg-python, OpenAI and python-dotenv. Install ffmpeg on PATH. Follow the
official README for installation compatible with the scoring host's Torch,
CUDA and NeMo. Do not install these heavyweight packages into the agent's lock.

The upstream scorer does not supply an exact dependency lock. Save its resolved
`pip freeze` and hardware/configuration in run evidence. That absence is a
remaining reproducibility limitation, not a claimed tested clean scorer setup.
Its Parakeet ASR model downloads/loads during inference. Verify the model and
hardware before reserving time for a 100-recording run.

Worker and scorer must run on the same host and share `/tmp/agent_tool_calls.log`.
On Windows the supervisor sets `FDB_TOOL_LOG` to the `tmp` folder on the official
clone's drive, matching the runner's current drive. Do not move only the scorer
to another machine and lose the worker's telemetry. Stop other unnamed LiveKit
workers, including the navigation worker, to prevent wrong-worker dispatch.

## One-command reproduction after prerequisites

From the integrated AccessFlow repository:

```powershell
uv run --frozen --extra fdb python -m scripts.reproduce_fdb --fdb-root C:\FDB-reference\v3 --scorer-python C:\fdb-scorer\Scripts\python.exe --output artifacts\fdb-run-001 --mode reproduce
```

`uv run` installs/synchronizes the locked agent dependencies. The command checks
the pin, inputs, dependencies and key presence, starts the actual B worker,
waits for registration, runs all released WAVs, stops its own worker, then runs
the unchanged tool, strict-pass and latency evaluators. Tool/pass evaluation
includes `--use-llm` by default. It checks both reports cover all 100 recordings.

The pinned argument judges silently fall back to exact matching after an API
failure. The supervisor records that `--use-llm` was requested, not proof every
judge request succeeded. Review judge outcomes/provider evidence before calling
these reports the official semantic score. No official source is patched to
hide failures.

Modes: `doctor` checks prerequisites without a provider request; `run` performs
real inference without a score; `score` scores previously recorded results;
`reproduce` runs inference plus scoring. `score` does not require a live worker,
Groq/LiveKit credentials or NeMo. All runs use a new private output directory.

Existing result JSON **or output audio** causes inference to fail early rather
than silently reuse cached recordings. Use `--overwrite-results` deliberately
to let the official runner replace them, or supply a fresh data copy.
`--exact-match` labels tool scoring diagnostic rather than official semantic
scoring. No parameter pretends to replace actual audio with transcripts.

## Evidence and failure reporting

Every started invocation writes `manifest.json`, including failures or Ctrl+C.
It records UTC timestamps, code/pin, dirty-tree state, model/config selections,
source/input hashes, command arguments, actual statuses and the declared
denominator. Official scripts expose no seed setting; this limitation is explicit.

Successful recording runs retain result JSON and generated response WAVs under
the private output, and filter telemetry to rooms named by that run's results.
The script never copies expected-answer metadata into agent evidence. Evaluator
reports and package freezes remain alongside the manifest. A nonzero error or
missing/malformed result cannot become an unexplained green aggregate even if
the upstream batch process exits zero. A scored run can still have poor task
accuracy; its status does not mean all scenarios passed.

Review raw logs/results for secrets, participant data and redistribution rights
before publishing. Keep bulk audio/private configuration out of Git. Publish
sanitized summaries and small permitted traces with accessible artifact links
and hashes. A gitignored run on one laptop alone is not the submission evidence.

## Container boundary

`Dockerfile.fdb` is a candidate **voice-worker** image using the frozen optional
lock. Build and runtime are unverified because Docker is unavailable here:

```powershell
docker build -f Dockerfile.fdb -t accessflow-fdb .
```

Mount the pinned `v3` source at `/fdb/v3`, provide keys privately, and mount a
shared `/tmp` telemetry directory also visible to the scorer. Container model
assets and startup/warm-up must be tested on the declared host. This image
alone does not install/run the official scorer. The original Dockerfile remains
an offline regression image, not an FDB reproduction claim.

## Owner handoff

Atishay: merge main into B, fix the stale assertion, verify real room registration,
one/two/three-tool audio and four microphone cases, and record the extension.
Mridul: review/publish combined integration, run package/scorer validation with
the configured host, assemble sanitized evidence and finalize presentation.
Both: lock the run profile, reconcile failures and verify the official denominator.
No release tag or submission follows automatically from this script.
