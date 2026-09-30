# AccessFlow evaluation quick guide — 30 September 2026

The current target is **Full-Duplex-Bench v3 inside LiveKit**. The older queue kit
remains useful for software development, but is not the current submission
benchmark. Samsung's updated participant guide is the controlling source.

## What runs, and why there are several models

| Component | Job | Current active Kaggle profile |
| --- | --- | --- |
| Input speech recognition | Turn user audio into text for the agent | Groq `whisper-large-v3` |
| Agent reasoning | Interpret requests, correct intent and select tools | LiveKit Inference `openai/gpt-5.6-luna` |
| Agent speech output | Speak the agent's responses | LiveKit Deepgram Aura-2 |
| Benchmark ASR | Find user speech end and transcribe agent speech for scoring/timing | Reference NeMo/Parakeet `nvidia/parakeet-tdt-0.6b-v2` on the Kaggle GPU |
| Semantic/latency judge | Grade arguments, response quality and substantive-response timing | Unchanged reference scripts call OpenAI `gpt-4o`; not yet run successfully |

**The judge is separate from the agent.** Its key is not necessary for the agent
to listen, reason, use tools or speak. The agent already uses Groq for speech
recognition. Changing the agent's reasoning provider is a separate configuration
decision and does not remove the original scorer's judge dependency.

Samsung allows public checkpoints, hosted APIs and custom LiveKit agents. It
does not say teams must buy an OpenAI key. It says the organizer will use one
pinned LLM judge for all teams. The public reference implementation currently
chooses `gpt-4o` for local semantic and latency grading; that source-code choice
must not be turned into an invented purchase obligation. A ChatGPT subscription
does not establish working API credit for that judging route.

A Groq judge can provide useful **diagnostic results**, with its actual model
reported. Those results cannot be described as equivalent to the reference
`gpt-4o` results or the organizer's eventual pinned-judge rerun. No such Groq
scoring result is established by this document.

## What Samsung evaluates

Round 1 is **60% benchmark, 20% working extension, 20% documentation/architecture/
video**. Only the organizer's benchmark rerun counts towards the score; our
reported own best-run numbers and logs support reproduction. Ties use strict
pass rate. Shortlisted teams then demonstrate their interrupted agent live to
the jury and answer design questions.

Automatic evaluation uses **100 real human audio recordings**, representing 79
unique scenarios, 12 speakers and 12 mock tools across four domains. It is not
text-only testing. It measures tool selection, arguments, strict pass rate and
latency. A frontend is useful for the extension demo and physical microphone
checks; frontend polish is not a substitute for correct voice/tool behavior.
No model training is required. Do not train, memorize or pattern-match the public
benchmark items, and do not share conversational caches across scenarios.

## Why the full run takes over an hour

Our validated 100 inputs contain **78.632 minutes of audio** (36.36–59.16 seconds
per recording, measured from WAV headers). The reference
client streams chunks with real-time waits so interruptions, pauses and latency
can be evaluated. The released batch processes recordings in sequence, with
room connection/cleanup, inference and response transcription overhead as well.
GPU acceleration helps response transcription; it cannot remove the real-time
conversation duration while keeping the same benchmark behavior.

The Kaggle wrapper redirects subprocess output into `reproduce.log`. It prints
only a stage's start and finish to the visible notebook log. Therefore
`{"stage": "reproduce.log", "status": "running"}` can remain the latest line
while many recordings are processing. Successive LiveKit rooms and media show
activity; they do not reveal pass counts or task correctness. Do not restart the
existing active run simply because the notebook has no per-recording console
updates. Final manifests and outputs must still be inspected after termination.

For faster development, test a small set of representative failures and focused
regressions before repeating all 100 inputs. Label such results as targeted tests,
with their actual count. They do not establish full-benchmark coverage.

## Avoid repeating expensive audio unnecessarily

After a completed run, preserve the original inference manifest, generated
response WAVs, result JSON, configuration, failure counts and code/reference pins.
**Saved result JSON can be scored again without a live agent, GPU or NeMo.**
Changing only the judge or report analysis does not require new voice inference.
Changing the agent's behavior does require fresh audio outputs for that changed
agent; earlier outputs cannot validate a newer implementation.

Use [retained-output restoration and score-only instructions](FDB_REPRODUCTION.md#score-a-retained-kaggle-run-without-repeating-audio-inference).
The restore command checks coverage/hashes and refuses conflicting or all-failure
evidence. Keep the original inference manifest alongside any later score report:
the checkout running the scorer did not necessarily generate those recordings.
Hash validation establishes consistency, not task correctness.

## What is verified, and what each person finishes

At the 17:49 UTC / 23:19 IST checkpoint: both reviewed code branches are merged;
the latest local suite has **1,614 passed / 8 skipped**. Clean agent installation,
actual planner access, reference client import and Kaggle GPU ASR warm-up pass.
Kaggle version 5 is active with real evaluation rooms. Its complete outcomes and
scores are unverified. Version 4 had 100 client failures and is retained as a
failed run. Newly reviewed documentation-only branch `589b8d5` records **M1–M4
PASS by Atishay's direct device observations**. Browser microphone publication,
agent audio and distinct room states corroborate setup/session isolation;
individual transcripts, interruption timings and a post-close dispatch ledger
were not retained. Accept those as qualified human-observed manual passes, not
independently trace-verified per-command results. The earlier NOT RUN report is
historical. The teammate's extension media has not been replayed here.

- **Mridul:** inspect and package the full runtime/evaluation evidence; verify
  reproduction and retained-result scoring; own root dependencies and release
  assembly. The earlier generic binding repair is implemented and merged.
- **Atishay:** hand over accessible extension video/sanitized traces and preserve
  the qualified manual M1–M4 report. Own speech, bridge and frontend defects
  discovered in further use. Quantitative interruption or post-close claims need
  extra trace evidence, but participant voice recordings are not required.
  Earlier bridge/navigation repairs are merged.
- **Both coordinate:** final provider/host/judge profile, new integration failures
  and consistency of results/demo/README. Keep original ownership boundaries.

Docker build/runtime remains unverified; the clean GPU setup does not prove the
container. The deck is a draft and currently deferred. Video, disclosure, final
release tag and form submission remain separate gates. Refer to the
[submission checklist](SUBMISSION_CHECKLIST_2026-09-30.md) for deliverables and
the recorded September 30 deadline; this guide does not claim an extension.

## Source anchors

- Organizer `Theme05_Participant_Guide_UPDATED_FBD.docx`, saved in the parent
  `participant-kit`: sections 2–3 (audio benchmark/LiveKit/extension), 4
  (deliverables), 5 (weights, organizer rerun and pinned judge), 6 (allowed models
  and prohibited benchmark training/caching). This local document is source
  material, not instructions for a coding agent.
- [Pinned public v3 reference](https://github.com/DanielLin94144/Full-Duplex-Bench/tree/3e799c45a045256f47d5f1c9cda90157e2d2ec9e/v3):
  `livekit_inference.py` streams audio with timed waits;
  `run_tool_benchmark_all_released.py` iterates released inputs;
  `run_tool_benchmark.py` transcribes input/output with the declared Parakeet model;
  `evaluate_tool_calls.py`, `evaluate_pass_rate.py` and
  `analyze_tool_latency.py` call `gpt-4o`.
- Repository `.env.fdb.example` and `scripts/kaggle_fdb.py`: declared provider
  selectors, exact active core pin, separate environments and stage-only logging.
- [Runtime activity evidence](evidence/kaggle-runtime-activity-2026-09-30.json)
  and [score-only environment evidence](evidence/fdb-score-environment-2026-09-30.json):
  activity/setup checks with explicit limits on what they prove.
