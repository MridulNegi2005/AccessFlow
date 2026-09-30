## Current runtime checkpoint — 30 September 2026, 23:26 IST

Both owners' reviewed code is merged; latest local suite is 1,614 passed,
8 skipped, with two existing warnings. Private runtime credentials and actual planner access are verified.
The corrected Kaggle scorer passes official client import and GPU ASR warm-up;
real evaluation audio reaches agent rooms. Full output is still pending.
Version 4 failed all 100 clients before the missing livekit-api fix, so no score
or end-to-end pass is claimed. Version 5, run 354197763, uses agent commit
`1030321a0dcbafcf97db5fbbad86423b57ba35b5`; it started at 16:42:57 UTC and
remained RUNNING at the latest check. The 17:56 UTC paginated LiveKit snapshot
shows 72 current-run evaluation rooms and 144 participants, with 70 rooms closed
and two active; latest room start was 17:55:38 UTC.
This establishes ongoing activity, not successful tasks or a final score.
Reference judging and final output inspection remain open. Latest Atishay
documentation reports Atishay-observed M1–M4 microphone passes; the complete
per-command timing and post-close action evidence has not been independently
retained here. Treat that as reported acceptance rather than a fully reproduced
measurement. Use [Kaggle setup](KAGGLE_FDB.md) and
[current runtime evidence](reviews/KAGGLE_RUNTIME_SETUP_2026-09-30.md).
All earlier missing-worker/key/dependency statements below are dated history.

### Samsung's policy versus the public scorer dependency

The supplied `participant-kit/Theme05_Participant_Guide_UPDATED_FBD.docx` says
Samsung re-runs the submission with semantic judging enabled and a single
pinned judge. Only that organizer re-run counts toward the benchmark score.
The guide does **not explicitly require participants to buy OpenAI credit**,
and it does not identify that pinned judge as `gpt-4o` in the policy text.

Separately, the unchanged public reference at
`3e799c45a045256f47d5f1c9cda90157e2d2ec9e` calls `gpt-4o` through the
OpenAI SDK in `evaluate_tool_calls.py`, `evaluate_pass_rate.py` and
`analyze_tool_latency.py`. That makes working OpenAI API access a dependency
of an unchanged local full semantic/latency run. It is not proof of a Samsung
purchase obligation. The current account has zero API credit; no purchase was
made. An OpenAI ChatGPT subscription is not the configuration used by these
scripts.

The running **agent** uses Groq Whisper Large v3 for speech input, LiveKit
Inference `openai/gpt-5.6-luna` for planning and `deepgram/aura-2` for speech
output. Its LiveKit planner does not use our separate direct OpenAI judge key.
Provider choices and accounts for the agent and judge must stay distinct.
A Groq judge can supply a separately labelled development diagnostic; it
cannot be presented as an equivalent reference score or Samsung's official
score. No successful Groq judge run is claimed in this checkpoint.

## Historical combined integration — 30 September 2026

Main now includes the reviewed Atishay ee5c70c snapshot and all Mridul changes
through d007d81. Independent exact-source verification: 1,589 passed, 6 skipped,
two existing warnings (103.73s), Ruff, seven Node checks, demo syntax and diff
checks passed. Worker imports/actual pinned registry passed offline with
placeholder credentials only. Protected Mridul implementation/config/tests are
unchanged by the teammate integration. No merge-blocking regression found.

Latest Atishay notes report successful recorded one/two/three-tool paths and a
navigation clip. Raw evidence remains on his machine and was not independently
replayed here. Physical mic M1–M4, full 100-recording official judged scoring and
clean scoring-host reproduction remain separate gates. His mic browser was
still Connecting. NeMo/judge readiness requires both owners. Earlier unmerged
and stale-assertion notes below are historical, not current blockers.

Read reviews/MERGE_VERIFICATION_2026-09-30.md and
handoffs/ATISHAY_FINAL_VOICE_HANDOFF_2026-09-30.md. Presentation deferred by user.

# FDB-v3 reproduction — 30 September 2026

## Historical actual-corpus checkpoint

The released data is now present privately in the local pinned clone. All 100
originals pass hashes/headers and actual normalization by the official reader;
seven are 16 kHz, so the former 48 kHz-only preflight was corrected. Original
formats are recorded; inputs are not rewritten. Current A: 1,544 pass/6 skip,
56 focused checks and Ruff pass. See reviews/RELEASED_CORPUS_CHECK_2026-09-30.md.
Earlier missing-data checks below are historical. Scoring now fails for the
missing OpenAI judge key; B worker/integrated live/scorer evidence remains open.

This is the current Theme 5 target. The older queue kit and `SAMSUNG_PACKAGE.md`
are historical development paths, not the final FDB evaluation interface.

Mridul owns the dependency lock, supervisor and packaging. Atishay owns the
LiveKit worker, bridge, speech and tool adapter. Both must verify the integrated
worker and scorer on the same evaluation host.

## Historical packaging verification and blockers

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

A later presence-only check found a Groq key in the ignored repository `.env`;
it found no LiveKit or OpenAI judge settings there. No key value was printed.
The supervisor deliberately loads the official clone's `.env.local`, not the
repository `.env`. A local Groq key alone cannot run the official voice/scoring
pipeline. Standalone CPU Silero VAD loading took 0.187 seconds with the actual
installed SDK; this is not a full worker warm-up or microphone/performance test.

## Install the agent

Use Python 3.11, Git and `uv`. Both owner changes and the obsolete B assertion
fix are already integrated. From a clean repository checkout:

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
The supervisor requires 100 nonempty valid PCM `input.wav` files, each in the
released `{example_id}_{24-hex-speaker-id}` directory with its metadata file.
It checks and hashes recordings, but never supplies expected answers to the agent.
It preserves original sample rates/widths/channels; the official reader uses
ffmpeg to normalize publishing audio. The actual archive has 93 inputs at 48 kHz
and seven at 16 kHz despite the README's general 48 kHz description.

## Configure privately

Copy `.env.fdb.example` to the official clone's `v3/.env.local` and fill it there.
Keep this file outside the AccessFlow repository. Existing environment variables
take precedence. Review candidate models and account access before the full run.

The current verified configuration selects Groq Whisper Large v3 input,
LiveKit `openai/gpt-5.6-luna` planning and LiveKit `deepgram/aura-2` output.
Optional Groq planning
uses `FDB_PLANNER_PROVIDER=groq` and `FDB_GROQ_MODEL`, not the navigation worker's
selector. Do not silently fall back to another provider or combine different
profiles into one score. LiveKit provider usage is billed/configured through
its project. Groq's documented input-token-per-minute limit can affect planning.

`OPENAI_API_KEY` is for the unchanged public reference's semantic judge and latency analyzer,
independently of the agent's planner. An exact-match tool diagnostic is labeled
as such; the pinned latency analyzer still requires this key.

Alternatively supply `--env-file C:\private\accessflow-fdb.env` to the supervisor
or bootstrap. The file is read, never copied or printed. Precedence is process
environment, explicit file, clone `.env.local`, then declared defaults. Values
are read literally, without `${...}` interpolation. The supervisor controls the
reference/telemetry paths even if a settings file tries to override them.

## Prepare the scorer separately on the same host

Use the Python 3.10 environment described in the pinned official README. It
needs LiveKit client dependencies, NumPy, `nemo_toolkit[asr]`, pydub,
ffmpeg-python, OpenAI and python-dotenv. Install ffmpeg on PATH. Follow the
official README for installation compatible with the scoring host's Torch,
CUDA and NeMo. Do not install these heavyweight packages into the agent's lock.

The upstream scorer does not supply an exact dependency lock. Save its resolved
`pip freeze` and hardware/configuration in run evidence. That absence is a
remaining reproducibility limitation. The Kaggle candidate profile has now
passed actual installation, dependency checks, official client import and GPU
model warm-up; full evaluation outcomes are still pending.
Its Parakeet ASR model downloads/loads during inference. Verify the model and
hardware before reserving time for a 100-recording run.

## One install/configure/evaluate command

On the prepared scoring host, provide Python, `uv`, ffmpeg, the unchanged pinned
reference, released data and private configuration. The agent environment is
installed from `uv.lock`; it remains separate from the compatible scorer.
With a **host-tested hashed scorer requirements lock**, run:

```powershell
python scripts/bootstrap_fdb.py --fdb-root C:\FDB-reference\v3 --scorer-python C:\FDB-scorer\Scripts\python.exe --scorer-lock C:\FDB-scorer\requirements.lock --env-file C:\private\accessflow-fdb.env --output artifacts/fdb-final-run --mode reproduce
```

This installs the frozen agent, installs scorer dependencies with hash checking,
loads private settings and runs supervised inference plus the official scoring.
No worker or credential file is supplied by fake-mode fixtures. On Linux replace
the paths and use the scorer environment's `bin/python`. The default agent
environment is the ignored `.venv-fdb/`; `--agent-env` may select a dedicated
subdirectory of the repository. Inputs, keys, scorer and evidence must stay
outside it. Existing evidence and non-environment directories are protected.

If the scorer is already prepared, replace `--scorer-lock ...` with the explicit
`--reuse-scorer`. This mode does **not** install or validate a frozen scorer
installation. A validated scorer lock/host is still a final reproducibility gate;
one has not been invented from the unpinned upstream README. The actual Kaggle
resolved installation is recorded separately from a hash-locked installation.
Change `--mode` to
`doctor` for preflight without any evaluation/API call.

Historical fresh-agent check on this machine: 85 frozen packages installed into a
previously absent environment; core import and Silero VAD load passed. The doctor
then failed for the absent unmerged B worker. It used the existing development
interpreter only as a placeholder scorer and did not prove Python 3.10/NeMo
compatibility. `docs/evidence/fdb-clean-install-2026-09-30.json` records the lock,
resolved packages and failed preflight. This is not full clean-host evaluation.

Worker and scorer must run on the same host and share `/tmp/agent_tool_calls.log`.
On Windows the supervisor sets `FDB_TOOL_LOG` to the `tmp` folder on the official
clone's drive, matching the runner's current drive. Do not move only the scorer
to another machine and lose the worker's telemetry. Stop other unnamed LiveKit
workers, including the navigation worker, to prevent wrong-worker dispatch.

The private local FFmpeg probe used `artifacts/tools/ffmpeg/bin/ffmpeg.exe`,
checksum-verified from the linked builder. To use it in a local scoring terminal,
prepend that folder to **that terminal's** PATH; do not change system/user PATH.
The submission host needs its own supported ffmpeg installation. This local
binary is ignored and is not part of the distributable application.

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
failure. Our supervisor now observes the actual judge requests and rejects
failed or malformed replies, as described below. Merely requesting
`--use-llm` or obtaining an upstream zero exit code does not establish a verified
semantic score. No official source is patched to hide failures.

Modes: `doctor` checks prerequisites without a provider request; `run` performs
real inference without a score; `score` scores previously recorded results;
`reproduce` runs inference plus scoring. `score` does not require a live worker,
Groq/LiveKit credentials or NeMo. All runs use a new private output directory.

Existing result JSON **or output audio** causes inference to fail early rather
than silently reuse cached recordings. Use `--overwrite-results` deliberately
to let the official runner replace them, or supply a fresh data copy.
`--exact-match` labels tool scoring diagnostic rather than official semantic
scoring; its latency analyzer still calls the LLM judge. No parameter pretends
to replace actual audio with transcripts.

## Why a full run is slow, and how to test a repair

The 100 released recordings contain approximately **78.6 minutes of input
audio**. The unchanged released-layout runner processes them sequentially.
The LiveKit client publishes 20 ms chunks with a corresponding 20 ms sleep,
then sends 1.5 seconds of silence; it also waits for room setup. Input and output
NeMo ASR, file conversion and provider requests add overhead. A faster GPU can
reduce local ASR time, but cannot eliminate the real-time input duration while
preserving pauses, corrections and interruption timing. An hour-plus run is
therefore expected; elapsed time alone is not evidence of a hang.

The notebook wrapper redirects the supervisor's stdout and stderr to
`accessflow-fdb/evidence/reproduce.log` and prints only stage start/end events.
Seeing `reproduce.log: running` hides per-recording progress from the notebook
console. LiveKit rooms demonstrate activity, while the retained results and
manifest determine actual outcomes. Do not restart the active version 5 merely
to improve logging.

After a defect is identified, first run its owned deterministic regression
tests, then a small **separate development audio subset** before committing to
another full run. The unchanged released-layout CLI supports `--root_dir`
(not `--example` or `--pid`). A dedicated private directory containing only the
selected original `{example_id}_{speaker_id}` folders can be used with:

```powershell
C:\FDB-scorer\Scripts\python.exe C:\FDB-reference\v3\run_tool_benchmark_all_released.py --provider accessflow --root_dir C:\FDB-development-subset
```

This low-level command does **not** start or supervise the worker, load our
private configuration or apply our full-run evidence guards. First configure
the declared environment and run exactly one matching worker on the same host,
using the correct shared telemetry path. Use a separate project/session and
evidence location if the full evaluation is active; do not dispatch a second
worker into its rooms. Record selected inputs, hashes, agent commit, profile
and outcomes; inspect the result JSON because the upstream batch can catch
errors. This is a development procedure verified from the pinned CLI/source,
not a newly executed subset run or a full benchmark claim.

The AccessFlow supervisor intentionally requires all 100 originals and rejects
existing outputs for fresh inference unless `--overwrite-results` is explicitly
requested. It has no subset switch. The separate `run_tool_benchmark.py` exposes
`--example`/`--pid` and supports both legacy and flat input discovery, but its
metadata loading differs: the released-layout runner additionally merges
per-folder `metadata.json`. Those filter flags are not accepted by
`run_tool_benchmark_all_released.py`; use its verified `--root_dir` route above
for an isolated released-data subset. Keep the complete unchanged
100-input run for final reproduction. Changing agent code requires new inference
for claims about that new version; rescoring retained outputs tests the judge,
not an agent repair.

## Evidence and failure reporting

### Score a retained Kaggle run without repeating audio inference

Download the completed private job's evidence. Preserve its original
`official-run-.../manifest.json` alongside all generated outputs. Prepare the
same pinned official v3 checkout and checksum-verified released corpus locally.
Then restore its outputs (replace the example paths with the downloaded run):

```powershell
uv run --frozen --extra fdb python -m scripts.restore_fdb_evidence --evidence artifacts/kaggle-run/accessflow-fdb/evidence/official-run-... --fdb-root artifacts/fdb-reference/v3
```

The command checks the reference pin/clean v3 source, all 100 original input
hashes, every copied output hash and complete result/status coverage before
writing. It refuses different existing outputs; use a fresh released-data
checkout rather than deleting evidence. Identical outputs are safely reusable.
Reference text may have Git's LF/CRLF checkout difference; input and output
bytes must match exactly. No expected-answer metadata or arbitrary manifest
paths are copied. Mixed failed recordings remain in the 100-recording denominator;
an all-failure run cannot be restored as a working recorded run.

For saved-output scoring on Python 3.11, create a separate lightweight scorer:

```powershell
uv venv --python 3.11 artifacts/fdb-score-env
uv pip install --python artifacts/fdb-score-env/Scripts/python.exe --require-hashes --requirements requirements/fdb-score.lock
```

This installs only the judge SDK/dependencies. The universal lock was installed
and checked on Windows/Python 3.11.15 (18 packages). All three actual official
scoring CLIs load, and preflight validates the 100 original recordings. This is
installation/import evidence, not a completed judge run or a tested Linux lock.
On Linux the interpreter is `artifacts/fdb-score-env/bin/python`. Do not use
this score-only lock for inference: it omits NeMo, CUDA, media and agent packages.

With a funded private judge configuration, score the restored outputs:

```powershell
uv run --frozen --extra fdb python -m scripts.reproduce_fdb --fdb-root artifacts/fdb-reference/v3 --scorer-python artifacts/fdb-score-env/Scripts/python.exe --env-file .env.fdb.private --output artifacts/fdb-score-retained --mode score
```

Scoring saved JSON does not require GPU/NeMo, LiveKit, Groq or a live agent. The
separate scorer needs the official scoring scripts' OpenAI and python-dotenv
dependencies. Keep the original inference manifest with the new score manifest:
the score-only supervisor's checkout commit is not evidence that the current
agent generated those older outputs. Restoration verifies consistency and
provenance hashes, not task correctness or authenticity of an untrusted manifest.
The complete run and judge request checks still determine the score status.
Installation evidence: `evidence/fdb-score-environment-2026-09-30.json`.

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

The pinned evaluators can catch judge errors and silently fall back to exact
argument matching. The supervisor now runs the three scoring scripts through
`scripts/fdb_judge_audit.py`, using the supplied **scorer** Python. It observes
their synchronous OpenAI SDK requests without changing prompts, arguments,
responses, models or score logic. Official tracked sources stay unchanged.
Inference is not wrapped, and the observer never runs inside the voice agent.

Each scorer produces a `*_judge_audit.json` beside its original report. Audits
contain request counts, model selection, timing, SDK version, token counts when
present, reply-structure status and exception type. They exclude prompts,
expected answers, response text, exception messages and credentials.
Request failure or malformed reply marks the supervisor failed, retaining the
upstream reports for diagnosis. Even a successful upstream exit cannot hide it.
An evaluator with no requests is explicitly unobserved; the aggregate is labeled
`scored_with_incomplete_judge_observation`, not verified semantic scoring.
`--exact-match` wraps only the latency judge and remains a tool diagnostic.

This observation verifies transport/reply structure, **not** judge accuracy or
complete scenario coverage. The official denominator is checked separately.
Three offline probes against the unchanged pinned evaluators reproduced their
fallback/missing-latency behavior after mocked authentication errors, and the
observer detected all three. See `docs/evidence/fdb-judge-audit-2026-09-30.json`.
Those probes made zero network calls and are not an official benchmark score.

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

Atishay: the reviewed implementation and stale assertion are already integrated.
The latest documentation reports Atishay-observed M1–M4 passes; hand over
accessible extension media and existing non-sensitive microphone/tool records.
Stronger quantitative timing or post-close claims require supporting traces;
participant voice recordings are not required. Fix only owned voice/bridge/extension defects
exposed by the run.
Mridul: inspect the current full-run outputs, validate packaging/reference
judging when available and assemble sanitized reproducible evidence. Presentation
remains deferred by the user's request.
Both: lock the run profile, reconcile failures and verify the official denominator.
No release tag or submission follows automatically from this script.
