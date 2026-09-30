# Private Kaggle FDB evaluation

This is Mridul's scorer/packaging work. It does not replace Atishay's physical
microphone checks. The selected agent still uses Groq Whisper STT, LiveKit
Inference planning and TTS; the official scorer uses local GPU Parakeet ASR and
an independent OpenAI `gpt-4o` judge.

## Fast path

1. Open the private GPU preparation job:
   https://www.kaggle.com/code/mridulnegi2005/accessflow-fdb-gpu-preflight
2. Keep the notebook private, enable Internet, select a GPU. The initial job is
   **prepare mode**: install separate Python environments, load the actual
   unchanged official NeMo model onto CUDA, transcribe synthetic silence, verify
   the released archive checksum and extract the 100 original recordings.
3. Inspect `accessflow-fdb/evidence/kaggle-status.json` and the install/health logs.
   A successful preparation is **not a benchmark score**. Dependency versions
   are a candidate profile until this actual host check succeeds. The recorded
   scorer freeze is a resolved environment snapshot, not a hashed install lock.
4. In Kaggle **Add-ons → Secrets**, create/attach these names:
   `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`,
   `ACCESSFLOW_GROQ_API_KEY`, `OPENAI_API_KEY`.
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

- Agent source: `91e3b8d76083135cdef38550c0360b7765c80c5f`.
- Official FDB source: `3e799c45a045256f47d5f1c9cda90157e2d2ec9e`.
- Runner: `scripts/kaggle_fdb.py`; notebook embeds the same runner.
- GPU candidate: Python 3.10, Torch/Torchaudio 2.6.0 CUDA 12.4, NeMo 2.4.0;
  agent environment: frozen repository Python 3.11 FDB extra.
- Official loader is unchanged. No expected-answer labels enter the agent.
- Kaggle GPU preparation is development verification; Samsung's rerun determines
  official scoring. Preparation does not establish a 300-second warm-up or
  scenario runtime acceptance, live microphone behavior or extension quality.
- The initial private job only requests installation/model/corpus preparation.
  Missing runtime/judge credentials are reported by name, never value.
- Scorer failure: inspect its private log and fix the declared compatibility
  profile; do not substitute transcripts, another judge or fabricated scores.

## Actual 30 September checkpoint

Initial private Kaggle run (version 1, run 354181534): GPU T4 x2, 201.1 seconds,
`gpu_setup_passed_runtime_not_evaluated`. The unchanged NeMo GPU loader and silence
transcription, frozen agent install and corpus preparation passed. It had no
runtime secrets attached and made no agent/judge requests. The initial job saved
environments in its output; the revised runner keeps installations under `/tmp`
and exports only evidence to reduce output size. This revision needs its own run.

The actual local worker registered successfully against the new LiveKit project
using the privately saved configuration, then was stopped. This verifies worker
authentication, not spoken inference. OpenAI billing shows $0.00 API credit;
no payment, upgrade or credited judge run occurred. Credentials stay in ignored
`.env.fdb.private` and private Kaggle Secrets; never include them in Git.

References: [Kaggle kernel configuration](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md),
[Kaggle Secrets](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md),
[FDB-v3](https://github.com/DanielLin94144/Full-Duplex-Bench/tree/main/v3).
