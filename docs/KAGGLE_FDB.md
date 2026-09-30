# Private Kaggle FDB evaluation

This is Mridul's scorer/packaging work. It does not replace Atishay's physical
microphone checks. The selected agent still uses Groq Whisper STT, LiveKit
Inference `openai/gpt-5.6-luna` planning and `deepgram/aura-2` TTS. The unchanged
public reference uses local GPU Parakeet ASR and an independent OpenAI `gpt-4o`
judge. Samsung's guide requires a single pinned judge for its organizer rerun,
but does not explicitly require participants to purchase OpenAI credit or name
that judge in its policy text. Our direct OpenAI key is for reference grading,
not the running agent's LiveKit planner. Groq grading, if used for development,
must be labelled a different diagnostic judge rather than the reference score.

## Current running job — 30 September 2026, 23:26 IST

Version **5**, run **354197763**, started **16:42:57 UTC** and remained RUNNING
at the latest check. The actual agent source pin is
`1030321a0dcbafcf97db5fbbad86423b57ba35b5`. Client import and GPU ASR warm-up
passed. At **17:56 UTC**, the paginated LiveKit snapshot showed 72 current-run
evaluation rooms with 144 participants (70 closed, two active), with the latest
room starting at 17:55:38 UTC. Those room counts are not saved-result or pass
counts. Final outputs, task passes and scores remain
unverified. Do not restart or cancel this job to change logging.

The 100 originals contain **78.6 minutes of real-time audio**, processed
sequentially. Each LiveKit client publishes paced 20 ms chunks; room setup,
post-input silence and NeMo input/output ASR add time. A full run taking longer
than an hour is expected. More GPU memory does not speed up the real-time input
clock. The wrapper's `command()` writes all child stdout/stderr into private
`reproduce.log` and prints only stage start/end. The displayed final running
stage therefore lacks a per-recording counter; it does not establish a freeze.
Retain terminal results and inspect the supervised manifest before any claim.

## Fast path

1. Open the private GPU preparation job:
   https://www.kaggle.com/code/mridulnegi2005/accessflow-fdb-gpu-preflight
2. Keep the notebook private, enable Internet, select a GPU. The canonical runner
   defaults to **prepare mode**; the current UI-launched version 5 explicitly
   selects **run mode**. Preparation installs separate Python environments, loads the actual
   unchanged official NeMo model onto CUDA, transcribe synthetic silence, verify
   the released archive checksum and extract the 100 original recordings.
3. Inspect `accessflow-fdb/evidence/kaggle-status.json` and the install/health logs.
   A successful preparation is **not a benchmark score**. Dependency versions
   are a candidate profile until this actual host check succeeds. The recorded
   scorer freeze is a resolved environment snapshot, not a hashed install lock.
4. In Kaggle **Add-ons → Secrets**, create/attach these names:
   `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`,
   `ACCESSFLOW_GROQ_API_KEY`, and `OPENAI_API_KEY` for full reference judging.
   `run` requires the first four runtime names; it can proceed without the
   judge key. The active version has all five attached, but no paid judge call
   is being made in its run-only mode.
   The API access token used to upload the notebook is not one of these secrets.
   Do not paste any credential into notebook code or outputs.
5. Import `notebooks/AccessFlow_FDB_Kaggle.ipynb` for an interactive run. Use `run`
   to gather agent outputs without the OpenAI judge when credits are unavailable.
   This is explicitly unscored. After
   preparation and attaching credentials, explicitly change its mode to
   `reproduce`, then run the final cell. This starts the cloud agent, streams all
   100 released audio inputs and runs the three official scorers. It consumes
   provider quota/credits; there is no automatic provider fallback.
6. Download the evidence folder before ending the session. Retain failure logs,
   manifests, GPU details, dependency freeze, result JSON/audio and judge audit.
   Inspect the final supervised manifest: process completion alone is not proof
   that all recordings or judge requests succeeded. Keep raw evidence private;
   publish only reviewed summaries without credentials or private voice data.

## Reproducibility and scope

- Current runner/active version 5 agent source:
  `1030321a0dcbafcf97db5fbbad86423b57ba35b5` (Linux venv fix, transport observation
  and all-failure rejection). Later repository/documentation commits are not
  evidence that this active run uses later agent code.
- Official FDB source: `3e799c45a045256f47d5f1c9cda90157e2d2ec9e`.
- Runner: `scripts/kaggle_fdb.py`; notebook embeds the same runner.
- GPU candidate: Python 3.10, Torch/Torchaudio 2.6.0 CUDA 12.4, NeMo 2.4.0;
  agent environment: frozen repository Python 3.11 FDB extra.
- Official loader is unchanged. No expected-answer labels enter the agent.
- Kaggle GPU preparation is development verification; Samsung's rerun determines
  official scoring. Preparation does not establish a 300-second warm-up or
  scenario runtime acceptance, live microphone behavior or extension quality.
- The historical initial private job requested only installation/model/corpus preparation.
  Missing runtime/judge credentials are reported by name, never value.
- Scorer failure: inspect its private log and fix the declared compatibility
  profile. Separately labelled alternative-judge diagnostics are permitted for
  development; never silently substitute them for unchanged reference scoring.

## Actual 30 September checkpoint

Initial private Kaggle run (version 1, run 354181534): GPU T4 x2, 201.1 seconds,
`gpu_setup_passed_runtime_not_evaluated`. The unchanged NeMo GPU loader and silence
transcription, frozen agent install and corpus preparation passed. It had no
runtime secrets attached and made no agent/judge requests. The initial job saved
environments in its output; the revised runner keeps installations under `/tmp`
and exports only evidence to reduce output size. Versions 4 and 5 use the revised
output location; version 5's final outcome remains pending.

The actual local worker registered successfully against the new LiveKit project
using the privately saved configuration, then was stopped. This verifies worker
authentication, not spoken inference. OpenAI billing shows $0.00 API credit;
no payment, upgrade or credited judge run occurred. Credentials stay in ignored
`.env.fdb.private` and private Kaggle Secrets; never include them in Git.

Version updates through the CLI did not retain notebook secret attachments in
this session. After any update, open Add-ons → Secrets and verify all five
checkboxes are attached to that version; save/run through the UI. Version 3
stopped before agent launch because no secrets were attached. Version 4 was
requested through the UI with all five checkboxes visibly selected.

A separate actual single planner request through the saved LiveKit settings
succeeded: `openai/gpt-5.6-luna`, 5.31 seconds, 56 prompt tokens, 11 completion
tokens, valid JSON. This verifies inference access, not speech or benchmark
performance. OpenAI judge funding remains a separate issue.

References: [Kaggle kernel configuration](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md),
[Kaggle Secrets](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md),
[FDB-v3](https://github.com/DanielLin94144/Full-Duplex-Bench/tree/main/v3).

Version 4 finished with 100 failed client calls and zero completed recordings.
The corrected profile includes the separate `livekit-api==1.2.1` distribution
and imports the actual official client before model warm-up. Core pin `1030321`
also retains swallowed client stderr with secret redaction and fails an
all-failure batch. A green Kaggle job badge does not establish a working run.
See `reviews/KAGGLE_RUNTIME_SETUP_2026-09-30.md` for reproduction and evidence.

After downloading a completed private run, use
`python -m scripts.restore_fdb_evidence --evidence <official-run-directory> --fdb-root <fresh-v3-directory>`
to validate and restore generated outputs. Then run the supervisor in `score`
mode when working reference judge credentials are available. This avoids
repeating real-time inference and does not require GPU/NeMo for saved-result
judging. It is a local reference dependency, not a verified Samsung purchase
requirement. An alternative judge requires its own explicitly diagnostic path.
The full commands and original-inference provenance requirements are in
`FDB_REPRODUCTION.md`. Current failed version 4 is correctly refused.

For later repairs, use owned regression tests and a small isolated audio subset
before repeating all 100. The unchanged released-layout runner supports
`--root_dir` for a selected-input directory; our supervised final-run command
still requires the complete 100 and refuses reused outputs. See
[targeted development and retained-output scoring](FDB_REPRODUCTION.md) for
the verified CLI boundaries, worker/telemetry prerequisites and provenance
rules. A subset pass does not replace the final complete reproduction.
