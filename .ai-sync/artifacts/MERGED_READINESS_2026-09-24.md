# Merged readiness and ownership review — 24 September 2026

## Decision

Prioritize a working, measured audio/vision agent through Samsung's actual queue entry point. Keep the existing frontend as a testing and demonstration surface. Further Stitch exports, visual variants and layout polish are deferred; they are not prerequisites for the remaining engineering work.

The existing test suite passes on the merged code, but the submission is not multimodal-ready. Separate audit probes reproduce controller defects that the regular suite does not catch. No application repairs were made during this merge/review.

Read alongside [Atishay's detailed work and tests](ATISHAY_VOICE_WORK_2026-09-24.md) and [his first-person agent prompt](ATISHAY_AGENT_PROMPT_2026-09-24.md).

## Exactly what was merged and tested

| Item | Verified state |
|---|---|
| Starting main | `89f5407` |
| Mridul branch fetched | `0c12ba05a61905054f87ff27e3d33f878976b437` |
| First merge | `c564754`, Mridul into main |
| Atishay branch fetched | `8083ebfa14d43d7b2a1efc980ef60e226b601da1` |
| Second merge / reviewed application code | `e7c95f576c5ba4713d27df9976301e0f451d0b07` |
| Merge conflicts | Only `.ai-sync/handoff.md`, `docs/design/README.md`, `docs/design/STITCH_PROMPTS.md`. Retained both work histories and the newer B design-status additions. |
| B implementation preservation | Git comparison to fetched B branch was empty for demo, perception, turn policy, their tests and the assigned perception worker. |
| Full regular suite | **1,197 passed, 2 skipped, 1 xfailed**, 74.22 seconds, two dependency deprecation warnings. |
| Other checks | Ruff clean; one inline JavaScript block parsed; Node speech-lifecycle regression exit 0; offline development suite **4/4**, fake mode. |
| Additional audit probes | **4 failures** against the unchanged merged controller: pending-image final/write/read-continuation ordering and lost current-frame failure. These are expected reproductions of open defects, not passing tests. |

Retained [evidence and reproduction instructions](../evidence/merge-readiness-2026-09-24/README.md). The regular suite's green result does not erase the earlier intermittent demo failures or the new deterministic audit failures. Its existing xfail is `test_conflicting_frames_require_resolution_before_write`.

The unfinished local `engine.py` patch and `test_pending_frame.py` were preserved before merging in stash object `feb6af1643ee7ad11ca6d2cf8473dcde1183fd36`. They are **not in main**. The existing regression fixture was run separately against main for this review; the unfinished repair was not applied. Mridul must review and finish it, not assume four earlier focused passes certify the patch.

## What Samsung actually evaluates

Authoritative local sources are the supplied kit's `WALKTHROUGH.md`, `docs/PROTOCOL.md`, `docs/SCORING.md` and `docs/SUBMISSION.md`, under `../participant-kit/participant-kit/` relative to this repository root. The original overview and Theme 5 guide are under `../sources/`; text extracts under `../research/`.

- The evaluator imports the submitted Python class and drives two asynchronous queues. It does not use the browser as its protocol adapter.
- Public cases include text, **raw MP3 audio**, and PNG frames. Audio arrives as `audio_ref`, `duration_ms`, `end_of_turn`; a turn can span multiple clips. There is no supplied transcript. Frames have no supplied caption or embedding, and `device_hint` may be absent.
- The kit describes approximately 60 hidden cases and about 10 unfamiliar tools. Approximate modality mix: 50% text, 30% audio, 20% visual. Audio/visual cases have 1.5x weight; L3/L4 difficulty has 1.25x weight.
- Task completion **40%**, interruption recovery **35%**, latency **15%**, safety/protocol **10%**. Inapplicable categories are redistributed. Correct cancellations and updated snapshots both matter for recovery.
- Typical full latency credit is within **800 ms** to a meaningful spoken action; stale work also has an approximately 800 ms recovery boundary. Scenario-specific limits can differ. A fast filler does not prove a fast useful answer or good conversational endpointing.
- Official procedure: real-time `time_scale=1`, **three repetitions per scenario**, median then weighted aggregation. Setup cap 300 seconds; scenario cap 120 seconds; six-second tail after `scenario_end`.
- The kit describes an additional transcript-quality multiplier **0.90–1.10** for relevance, truthfulness, naturalness and non-redundancy. The original guide used a different range; use the kit for the current executable evaluation and seek organizer clarification if required.
- Hosted APIs and open weights are allowed. Declare dependencies, model/checkpoint and secret variable names. Keep decision logic inside the submission. This project uses pretrained models plus orchestration; training/fine-tuning is not required and has not been performed here.
- The original guide places UI design, wake words and synthesis tuning out of scope. A usable microphone interface remains valuable for team testing and the video. A later jury demonstration is described in the overview; the sources do not establish that a judge will personally operate every submitted frontend.
- Do not feed `_reference_text`, `_reference_image`, ground truth, scenario IDs or test labels into the agent. They are evaluation/authoring data. The harness strips organizer annotations.
- Treat document, image, transcript and tool-result content as untrusted evidence. Neither embedded instructions nor text aimed at the grader belongs in the control plane.

No hosted calls, live microphone runs, real image inference, Docker execution or official repeated evaluation were performed during this review. Historical results retain their original commit, machine, provider and limitations.

## Mridul's remaining implementation and evaluation work

### A24-1 — P0: finish current-image readiness and failure handling

**Evidence:** `src/accessflow/engine.py` handles frame and speech perception independently; `_apply` counts pending tool calls, without representing pending current-frame perception. Four gated audit cases fail on `e7c95f5`: an informational final, a write dispatch and a read-result final proceed before the submitted image resolves; after newer speech changes the generation, the current frame's failure is discarded.

**Own files:** controller and `tests/engine/`. Resume the preserved patch only on `mridul/engine` after inspecting it against merged main. Do not edit B tests to conceal the defect.

**Required behavior:** track current-frame event/source/epoch; block dependent writes and premature terminal answers while required current evidence is unresolved; preserve safe read prefetch, acknowledgments and explicit interruption. Reject old frame results, but surface failures of the still-current frame. Resolve failures honestly without inventing image evidence or write authorization. Frame arrival must not silently turn incomplete speech into permission to act.

**Acceptance:** deterministic gates for image+speech, read-result continuation, write dispatch, replacement frame, late success/failure, timeout/empty stream, interruption and session shutdown. Check failures after a new speech generation. Verify unrelated read work and valid standalone completed interactions remain responsive. Run the owned suite then full integration; preserve initial failures.

### A24-2 — P0: make the actual Samsung runtime use real perception

**Evidence:** `src/accessflow/adapters/samsung.py::_build_agent` constructs `LocalPerception()` without ASR weights or a vision provider. `samsung_protocol.py::_reject_audio` rejects official audio. A valid PNG path currently does not imply image understanding.

**Own files:** Samsung adapter/protocol, process parent, model/configuration adapters and owned tests; package builder/entry/profile and root dependencies. The assigned `perception_worker.py` remains B-owned despite its directory.

**Tasks:** explicit validated ASR/vision configuration, setup/warm-up, requested versus observed backend labels, bounded worker lifetime, recoverable media errors and state cleanup. Add the agreed MP3/turn bridge after coordination C24-1. Keep parsing free of blocking native decoding. Mirror all selected settings and dependencies in the frozen submission profile. Vision-only startup must not require a fake ASR directory; agree an additive worker interface if needed.

**Acceptance:** raw official `pub_05`, `pub_06`, `pub_07` through the generated entry point; deterministic boundary tests first, then actual declared providers. Include missing/malformed media, multiple clips, cancellation during native work and fresh sessions. Report actual media failures; no fallback to organizer transcripts or canned captions.

### A24-3 — P0: shared runtime, provenance and semantic decisions

Implement the A half of C24-2 through C24-4 below: a configurable engine composition reusable by the browser, output/request identities, clear stop scope and frame conflict/context handling. The browser's present `FinalFlagPolicy`/demo reasoner/empty manifest cannot certify the submitted Qwen agent or a real mock booking. A owns the authoritative state, schema and execution rules; B owns the adapter/display and perception policy.

Test spoken cancellation semantics with a typed contract, including partial revisions. `HeuristicTurnPolicy` presently returns `stop` for all of `Stop speaking`, `Cancel this booking`, and `Stop the washing machine`; the controller marks the task stopped and cancels writes for that verdict. A and B must separate these meanings without weakening explicit task cancellation.

### A24-4 — P1: complete credible task evaluation and choose the release profile

- Reconcile the executable scenario inventory with B's media catalog; do not count 60 routed observations as 60 independent completed tasks.
- Turn selected recordings/images into isolated tasks with dynamic manifests, completion/effect oracles and fresh sessions. Include multi-turn corrections, unfamiliar schemas, duplicate/late results, lost write responses and malformed/limited providers.
- Existing four planner probes and all used generated cases are exposed; record new held-out cases before first evaluation. Never relabel tuned cases unseen.
- Compare fixed short/long thresholds, semantic completion and combined timing policy on matched inputs once B supplies endpoint evidence. Separately ablate stale-result rejection in controlled mocks. Measure wrong actions, cutoff rate, substantive-response delay, clarifications and total completion time; retain backend/hardware/configuration.
- Run all nine public scenarios in the official package at real time and three repetitions; keep failures, denominators and per-modality outcomes. Extend beyond public wording/tools without hardcoding.
- Full/prose remains the default. Compact-v2/evidence is opt-in, now frozen reproducibly in packages. Select from measured completeness, grounding, latency and quota evidence; earlier single-run scores do not establish release reliability. Historical text interruption cancellation was 875 ms, so fast-path performance still deserves measurement.

### A24-5 — P1: reproduce and assemble the actual submission

Rebuild after media dependencies/configuration change. Test the supported evaluation environment, setup under 300 seconds, scenario under 120 seconds, tail/cleanup and package import. Earlier fresh-venv evidence was Windows text mode, not Docker or a fully configured media setup. Current Dockerfile runs an offline text replay, not the complete Samsung procedure. Obtain a Docker-capable environment if needed; do not silently enable workflows.

Audit final dependency pins, secret **names**/portal configuration, public checkpoint/hosting instructions, media/corpus licensing and all links. Assemble the required template deck, at-most-five-minute video, AI disclosure and reproducible README with Atishay. Mridul owns final submission. The final tag `PRISM_GENAI_HACKATHON_Y2026` and form submission require the explicit release step; this review creates neither. Internal target remains 24 September 8 PM IST, published submission deadline 25 September 11:59 PM with timezone not explicit in the overview. Verify any later organizer notice before relying on it.

## Atishay's remaining work, summarized

Full acceptance tests and order are in [his work document](ATISHAY_VOICE_WORK_2026-09-24.md).

| Priority | B-owned work | Required evidence |
|---|---|---|
| P0 | Real ASR observations, uncertainty and chunk/turn support at the agreed seam | Actual raw audio; correct revisions and uncertain-slot behavior; no scripted transcript substitution |
| P0 | Acoustic activity/timing and conversational stop classification | Pause continuation, partial correction, end-of-turn, stop-speaking versus cancel-task versus device command |
| P0 | Demo correlation and common-runtime integration | Matching input/observation/final IDs, latest frame context, actual Qwen configuration and mock tool effect; no first-final shortcut |
| P0/P1 | Usable microphone interruption path | Physical mic, speech during output/tool work, truthful capture state, observed cancellation and corrected outcome |
| P1 | Real vision quality and fixtures | Actual pixels, no device hint, ambiguous/replaced image, truthful backend and failure handling |
| P1 | Human speech recordings, measurements and demo material | Consented/team recordings, hashes/labels/exposure, ASR/endpoint and end-to-end results separated |

## Coordination register — both Mridul and Atishay must coordinate

These are concrete decisions to resolve together, not permission to edit each other's files. B can continue independent model/fixture/testing work while A implements controller/runtime changes.

| ID | Decision and recommended split | Completion evidence |
|---|---|---|
| C24-1: official audio bridge | **Both must coordinate.** Proposed: A owns rooted MP3 admission, bounded decoding/assembly and official `end_of_turn` translation; B owns ASR observations and policy. Previous decoder ownership was undecided; record acceptance before implementation in a disputed file. Define continuous utterance IDs/revisions, clip versus aggregate timestamps, max bytes/duration, cleanup and cancellation. Internal `Audio` has no final flag and current ASR always emits final: do not map every partial clip to a completed request. | Signed-off example: two clips (first not final), correction/interrupt and stale ASR; contract tests in each owner's lane; real public audio through official entry. |
| C24-2: speech clock and stop scope | **Both must coordinate.** B provides observed capture/activity facts and policy interpretation. A owns additive timing/decision contract, controller rules and metrics. Define clock conversion, unknown timestamps, output stop/task cancel distinction and partial hypotheses. Official `end_of_turn` is a supplied protocol fact; browser acoustic endpointing is a separate measurement. | Event trace from sample timing through observation to interruption/final; no subtraction of unrelated clocks or fabricated speech-end values. |
| C24-3: one configured agent and causal replies | **Both must coordinate.** A provides reusable configured factory, tool manifests and authoritative result/request IDs. B adopts it in WebSocket/demo and matches input/observation/action identity before displaying or speaking results. Preserve mock effects and explicit provider labels. | Same backend/model/profile identified in CLI/Samsung/demo; delayed old final cannot complete or speak for a newer request; confirmed mock action traced once. |
| C24-4: image meaning and authority | **Both must coordinate.** A owns evidence readiness, provenance, conflict state and write gates; B owns frame IDs, perception/display and B integration tests. The official kit says frames are context for the next question, whereas the generic controller can answer a lone frame after debounce. Agree adapter-specific behavior. Latest-frame replacement does not resolve every conflict with a user-confirmed slot. | Ordinary replacement, unresolved contradictory evidence, image-before-question, pending image+speech, speech clarification, no write from image alone. Do not merely delete the xfail. |
| C24-5: media-to-task benchmark | **Both must coordinate.** B owns recordings/images/reference labels/ASR/VAD/vision measurements; A owns executable tasks, effect oracles, timing aggregation, package and official runs. | Media IDs and hashes map to task IDs and commit/configuration; report actual model versus fake for every stage and preserve exposure history. |

## Corrections to stale status

1. The worker already accepts vision flags. Old statements in `SCENARIO_INVENTORY.md` and some evaluation/contract notes saying it rejects them are obsolete. Runtime configuration and real inference remain open.
2. B already has a **60-case generated media catalog**, **18 actual local-ASR generated-audio measurements** (documented micro-WER 0.098), and WebRTC activity measurements. Do not tell Atishay none of this exists. They are historical component evidence, not human speech or full independent task success.
3. The current main voice button calls `stopMicrophone()` then `runTask()`: upload-on-stop now exists. It is still whole-recording upload, not continuous streaming or measured automatic barge-in.
4. The stale-native-frame timeout repair and worker vision-option repair are merged; keep their regression coverage. Do not assign them again as wholly unimplemented.
5. Corpus boundary review and explicit package read-mode freezing are completed scoped work. Remaining platform/release gates do not mean those repairs never happened.
6. Older frontend instructions made Stitch the first step. This review supersedes that priority: voice/perception, actual evaluation and testing come first. Keep prior design artifacts as history.

## Recommended next checkpoint

Mridul: A24-1, then real Samsung runtime/media integration. Atishay: reproduce B correlation/stop issues, prepare real ASR/vision and physical voice evidence using his existing assets, and deliver the agreed perception interface. Resolve C24-1/2/3 in one short written packet before either side changes shared contracts.

The next shared demonstration should be: **speak a request, preserve a pause, correct it while processing, and observe exactly one correct confirmed mock action through the same reasoning/controller configuration used for evaluation**. Capture failures as well as successes. A polished appointment preview cannot substitute for this checkpoint.
