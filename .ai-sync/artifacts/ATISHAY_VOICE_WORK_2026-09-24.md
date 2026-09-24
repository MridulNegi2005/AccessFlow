# Atishay: voice, perception and testing handoff — 24 September 2026

## Your objective and scope

Make real user audio and images reach the agent correctly, keep conversational timing and interruption usable, and prove this with reproducible tests. Preserve the current UI. **Do not spend the next work sessions on Stitch exports, more variants, animations or redesign.** Functional capture, playback stop, error recovery, accessibility and truthful backend/status display remain in scope.

Reviewed merged application commit: `e7c95f5`, including your branch `8083ebf` after Mridul's `0c12ba0`. Read [the combined readiness review](MERGED_READINESS_2026-09-24.md) for Samsung rules, Mridul's work and exact merge evidence. This is a forward handoff, not a claim that your earlier work was unnecessary or that all remaining work belongs to you.

### Ownership

- Yours: `src/accessflow/perception/`, `src/accessflow/turn_policy/`, `demo/`, `tests/perception/`, `tests/demo/`, feedback/presentation artifacts and your handoff. `src/accessflow/adapters/perception_worker.py` is also assigned to you by the existing agreement.
- Mridul's: shared contracts/interfaces, controller, model/execution adapters, process parent, Samsung protocol/runtime, evaluation harness/oracles, root configuration, lockfile, packaging, Docker and release.
- Read his code to understand behavior. Do not repair his engine, add a duplicate planner in JavaScript, modify his tests, edit the lockfile or change shared schemas unilaterally.
- Propose dependencies and shared-contract examples for Mridul. Continue owned component tests independently with explicit fakes until his integration is ready.

## Evaluation priorities you need to understand

Samsung supplies raw MP3 recordings and PNG frames as well as text. Automated evaluation does **not** mean text-only, and the browser is not the submission entry point. Approximate hidden weighting is 30% audio and 20% visual, each 1.5x; task completion and interruption recovery together account for 75% of base score. Latency accounts for 15%, safety/protocol 10%. Typical first meaningful speech and stale-work cancellation targets are around 800 ms, with scenario-specific rules. Official runs use real time, three repetitions, per-scenario median, 120-second scenario cap and 300-second setup cap.

The guide excludes UI design, wake words and synthesis tuning from the core task. Keep enough interface to test a real microphone, inspect results and record the demonstration. The jury/video is a reason for a usable demo, not more decorative work.

Use pretrained ASR/vision/reasoning models; no new speech-model training is required. Do not claim model training from prompt/code changes. Local or hosted models are allowed when declared and reproducible. Never infer ASR/vision capability merely from the selected reasoning model's name. No paid fallback or hidden backend switch.

The kit is locally at `../participant-kit/participant-kit/` from Mridul's repository root; locate your own copy. Read its `WALKTHROUGH.md`, `docs/PROTOCOL.md`, `docs/SCORING.md`, `docs/SUBMISSION.md`. Do not modify organizer harness/scoring files. An agent must not read author annotations or ground-truth transcripts to solve a case.

## Preserve and build on completed work

- WAV/PNG validation, bounded native-worker lifecycle, stale-revision handling, process vision-option support, generated fixtures, acoustic measurements and the UI are useful existing work.
- Your documented 18 generated-audio ASR runs completed with micro-WER 0.098; the 60-case catalog and mixed replay exist. The latter used real ASR but injected vision and mock reasoning, in one session without state-changing tools. That is **component/routing evidence**, not 60 completed independent tasks.
- The main voice button now uploads after stop. It is no longer accurate to say every voice request needs a separate Run click. `demo/index.html::stopMicrophone` still assembles a complete WAV and `voice-toggle` then calls `runTask`; it does not send ongoing audio chunks.
- Default browser perception/reasoning are mocks; optional local models are separate configurations. `demo/app.py::websocket` currently constructs `FinalFlagPolicy`, `FakeTools`, and `Start()` with no tool manifests. A live-looking card cannot establish a Qwen booking.
- Existing vision protocol tests use loopback providers. The latest committed vision availability notes do not report a live model run. Recheck your current machine; do not assume the old installation state is still current.

## B24-1 — P0: ASR uncertainty and actual turn boundaries

**Source evidence:** `perception/local.py::_transcribe_with_whisper` joins segment strings and discards the remaining ASR information. `LocalPerception.observe(AudioEvent)` emits `final=True`. The shared `Audio` payload has no partial/final field, so official multi-clip turns cannot be represented faithfully just by wrapping each clip in an AudioEvent.

**Work:** retain useful recognition uncertainty/alternatives when the selected backend supplies them, without inventing calibrated confidence from a transcript. Preserve repeated words and explicit corrections. Distinguish empty/silent/distractor input, uncertain critical values, partial hypotheses and final user requests. Compare actual transcription against labels; a fluent wrong city/date is still wrong.

**Both Mridul and Atishay must coordinate (C24-1/2):** propose an additive observation/audio contract with provenance, revision, finality, timing and uncertainty semantics. A owns that shared contract and the official MP3 boundary; decoder ownership was previously pending and must be recorded. B owns perception and timing. Do not secretly assume this handoff authorizes changes to A's adapter.

**Independent work now:** test existing ASR on your recordings and generated catalog, capture available ASR metadata in owned experiment reports, prepare callback/worker fixtures and concrete event examples. If the current public contract cannot carry required information, keep experiments separate and send the smallest failing contract example.

**Acceptance cases:** ambiguous destination needing clarification; Tuesday then Wednesday at five; repeated words with no semantic correction; two clips in one turn with only the last final; changed hypothesis for the same utterance; silence/noise; missing/corrupt clip; timeout; late ASR from an interrupted/replaced utterance; fresh session. No tool decision may be based on `_reference_text` or an expected label.

## B24-2 — P0: integrate timing and distinguish stop meanings

**Source evidence:** `HeuristicTurnPolicy.update` accepts an optional `ActivitySummary`, but the engine calls it without timing. The current acoustic reports are not an integrated endpoint detector. A direct probe returns the same `stop` verdict for `Stop speaking`, `Cancel this booking` and `Stop the washing machine`; A's controller treats that verdict as task stop.

**Work:** provide actual activity/pause facts, preserve timestamps and hypothesis revisions, and distinguish continued speech, completed turn, correction and backchannel. An acoustic pause is evidence, not automatic completion. Preserve your native-worker bounds: cancelling an await does not stop a native thread.

**Both must coordinate (C24-2):** B owns policy classification/activity capture; A owns shared decision fields and their controller effect. Agree capture clock versus session clock, unknown endpoints, output-only stop, task cancellation, ordinary device commands and partial stop hypotheses. Existing explicit Interrupt scope is useful, but does not fix semantic transcript classification by itself.

**Acceptance cases:** fluent short utterance; internal 0.5/1/2-second pauses followed by continuation; repetitions; trailing silence; cough/background speech; short backchannels; final and partial self-corrections; three stop meanings above. Test matched input with short/long silence baselines. Report premature completion and extra wait separately; measure actual speech end, acknowledgment and substantive response separately. These pause durations are test examples, not fixed product thresholds or official requirements.

## B24-3 — P0: correlate demo replies and adopt the real runtime

**Source evidence:** the browser sets `finalObservationSeen` when a matching source observation arrives, then accepts any later `final`/`clarify`; it does not check that terminal's `caused_by_event_id` against the intended request. `tests/demo/test_reasoner.py` still exits on the first final/error and compares a final's causal ID with itself. This is insufficient proof of correlation. Historical intermittent combined-context failures remain relevant even though this merge's full suite passed.

**Work:** reproduce with controlled gates, not timing sleeps. Make image-only, old request and current combined answers different in the fake provider. Correlate input acceptance, observations and terminal actions through explicit identities; preserve other messages while waiting. A media-received status is not proof of finished vision. Do not drop legitimate clarification/error handling behind an observation flag, and do not speak a stale answer.

**Both must coordinate (C24-3/4):** A supplies common runtime factory/manifests and correct causal outputs. B wires WebSocket/capture/playback and tests. Mridul has separately reproduced controller pending-frame defects and owns their repair. Do not compensate by editing his engine or weakening your combined-context assertions.

**Acceptance cases:** old final arrives after new observation; frame finishes before a follow-up; follow-up supersedes pending image reasoning; image remains pending while speech finishes; image failure followed by recovery; multiple rapid requests; disconnect/reconnect/session reset. Check the final associated with the intended request and actual combined prompt, not just any terminal output.

**Common-runtime gate:** demonstrate declared real ASR plus the agreed reasoning model/profile, dynamic mock tool manifests, one confirmed mock effect and readable result. Record each backend independently. The empty-manifest demo and deterministic meeting preview cannot satisfy this gate.

## B24-4 — P0/P1: physical microphone and interruption loop

There are two milestones. **First**, make current capture/upload work reliably with a real microphone and actual transcription; report it truthfully as upload-on-stop. **Second**, add the agreed bounded ongoing capture/activity path so the user can interrupt by speaking during output or slow work, without waiting for the first operation to finish or manually staging another completed file. This second milestone needs C24-1/2/3, not a UI-only claim of real-time behavior.

Do not delay official raw-audio acceptance to build a full-duplex browser. The kit supplies clip boundaries and explicit interruption events; a continuously listening browser is a product/testing milestone, not a separate stated submission-interface requirement. Keep these two acceptance paths distinct while sharing the agent underneath.

Keep capture and Stop available when appropriate during reasoning; maintain bounded queues, byte/duration limits and cleanup. Existing button-based playback cancellation remains useful as a fallback. Ignore stale speech-synthesis callbacks, preserve output-only stop semantics, and consider speaker echo/noise before treating microphone activity as intentional user interruption. No custom synthesis/wake-word project is needed.

**Actually perform and record:**

| Test | What to verify |
|---|---|
| First permission and denied permission | Correct physical prompt/device path and recovery; a mocked rejected promise is a separate test. |
| Ordinary speech | Captured bytes, real transcript, actual answer, device/browser/model and measured timing. |
| Long pause + continuation | No premature complete task; measure extra wait on fluent control cases too. |
| Tuesday → Wednesday at five | Final slot is Wednesday 17:00 or an honest clarification for unresolved ambiguity; exactly one valid mock effect when authorized. |
| Speak during TTS | Measured output stop; new speech received; no lost correction or unwanted task cancellation. |
| Speak during slow read/write | Fast local signal; obsolete work cancelled/ignored by A; final confirmed effect matches latest authorized request. |
| Headphones versus speakers | Report echo/noise behavior and limitations; do not claim acoustic echo cancellation without evidence. |
| Disconnect while recording/processing | Mic tracks/AudioContext/worklet/temp files and session state clean up; no old action shown in fresh session. |
| Playback muted/unsupported | Text and microphone controls still usable; no fake audible-playback claim. |

Log click-based stop separately from automatic speech-triggered interruption. Existing Node TTS tests verify callback state, not actual sound or barge-in.

## B24-5 — P1: real vision, frame replacement and uncertainty

Run a real replaceable vision backend on actual images, including unfamiliar device ports/screens, no hints, ambiguous/cropped images and changed frames. Preserve `event_id`, `frame_id`, backend/model and revision association. Do not use file names, generated labels or captions as pixel evidence.

**Both must coordinate (C24-4):** official frames are context for a following question. Decide when a standalone image response is appropriate in the generic demo versus official adapter, how newer frames replace older ones and when conflict with spoken/confirmed slots requires clarification. A owns authoritative conflict/write guards; B supplies observations and owned integration tests.

The worker supports vision flags; that old bug is fixed. Vision-only startup still involves the A parent's model-path requirement and your worker's required `--model-path`. Propose additive support rather than using a dummy directory. If a real ASR model is installed, the existing combined worker can be exercised without waiting for a vision-only improvement.

**Acceptance:** successful pixel-grounded answer; ambiguous evidence clarified; failure/timeout recoverable; newer frame wins over delayed old result; conflicting evidence does not authorize a write. The kit describes an image-embedding hybrid-search bonus: discuss a real embedding backend/schema with A after basic image understanding works; a made-up vector is not acceptable.

## B24-6 — P1: extend evidence, do not recreate existing assets

Keep the generated 18-audio/12-image catalog and exposure history. Add a small, varied, consented team-recorded set first; include fluent speech as well as pauses, repetitions, corrections, ambiguous names, background noise and interruption. Preserve actual WAV/audio format, duration, hardware/browser, model/checkpoint, SHA-256 and reference labels. Do not claim generated speech represents clinical populations. Feedback sessions are optional if unavailable; lack of them must be reported, not simulated.

Existing generated held-out cases that have already been run are exposed. Mark new cases held out only before the first scored use and record when labels/results become visible. Keep private raw recordings out of a public repository unless specifically authorized; anonymized written feedback and team demo recordings can be sufficient.

**Both must coordinate (C24-5):** send media IDs/hashes and timestamp/label semantics to Mridul; he creates independent executable task/effect oracles. Report separately: ASR word/slot errors; activity/endpoint errors; image grounding; real reasoner task completion; cancellation/wrong/duplicate effects. The official path must run on raw media with the same declared configuration, not only in your local perception experiment.

## Work order and commands

1. Save your local work, fetch origin, inspect branch/log/status and integrate the new main into your own `atishay/perception` branch with an ordinary merge. Do not reset/force-push or push main. Ask for resolution only for a real conflicting ownership decision; do not wait to run independent owned tests.
2. Read this packet and resolve the C24-1/2/3 examples with Mridul. Reproduce B24-2/3 in owned tests while checking available ASR/vision configuration.
3. Deliver real microphone-to-ASR and vision observations, timestamp/uncertainty reports and raw-media fixtures. Then attach to A's agreed common runtime and exercise correction/interruption/effects.
4. Run official public audio/visual cases together, preserving every attempt. Keep polishing deferred until the evidence gates above are met.

From the repo root, after checking the pinned environment:

```powershell
uv sync --frozen --extra dev
uv run --frozen --extra dev python -m pytest tests/perception tests/demo -q
uv run --frozen --extra dev python -m ruff check .
node tests/demo/speech_lifecycle_check.cjs
uv run --frozen --extra dev python -m pytest -q
```

These offline commands do not install/configure an ASR model or prove live quality. Add the already-declared `audio` extra when needed; propose new dependencies to Mridul rather than changing the lockfile. For the current demo, set `ACCESSFLOW_DEMO_WHISPER_MODEL` to an actual installed model directory, verify startup backend labels, then run `uv run uvicorn demo.app:app --host 127.0.0.1 --port 8000`. Do not interpret the default mock response as a transcription. The optional existing Ollama demo reasoner is not automatically the Qwen submission runtime.

After A delivers a configured generated Samsung package, run from that package (with registered secret values only in the environment):

```powershell
python run_local.py --scenario scenarios/pub_05_audio_asr_ambiguity.json --agent agent.agent:ParticipantAgent --time-scale 1 --json audio-ambiguity.json
python run_local.py --scenario scenarios/pub_06_audio_disfluency.json --agent agent.agent:ParticipantAgent --time-scale 1 --json audio-correction.json
python run_local.py --scenario scenarios/pub_07_visual_port_lookup.json --agent agent.agent:ParticipantAgent --time-scale 1 --json visual-port.json
python eval_submission.py . --reps 3
```

Use fresh output directories per attempt, never overwrite failures. These run real configured inference and consume provider quota; coordinate the shared account and never add billing/fallback silently. The current package's media gaps mean these are target acceptance commands, not a claim they pass today.

## Definition of your next handoff

For every slice: exact owned files/commit, before-fix reproduction, commands/results, model/backend/hardware, recording provenance, observed timings, remaining failures, and any A/C24 dependency. Include traces showing the intended request's final and actual mock effect where applicable. Update your handoff and feedback records, then make a small reviewable branch commit.

Do not close B work because the frontend looks finished, all injected tests pass, or a provider is merely configured. Conversely, do not claim you are blocked from all work while recordings, live component checks, gated reproductions and ownership proposals remain available. Leave Mridul's controller/runtime tasks explicitly assigned to him.
