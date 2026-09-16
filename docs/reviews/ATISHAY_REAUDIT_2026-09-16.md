# AccessFlow — Atishay's follow-up audit

Date: 16 September 2026  
Reviewed shared checkout: `mridul/engine`, `919ed27`  
Earlier detailed report: [ATISHAY_AUDIT_2026-09-15.md](ATISHAY_AUDIT_2026-09-15.md)  
Mridul's separate findings/next work: [MRIDUL_SECOND_REAUDIT_2026-09-16.md](MRIDUL_SECOND_REAUDIT_2026-09-16.md)

## Assessment and scope

No implementation changes were found between `30ed402` and `919ed27` in `src/accessflow/perception/`, `src/accessflow/turn_policy/`, `demo/`, their test directories, or `src/accessflow/adapters/perception_worker.py`. The previous B findings therefore remain relevant to **this shared checkout**. This does not say that Atishay has done no work on another branch or machine; compare his current branch before making repairs.

This review changes no B implementation or tests. The complete repository currently passes **411 tests, no xfails**, and Ruff. That validates the existing cases, not missing microphone, endpointing or vision integration. No live ASR/vision, microphone capture, participant feedback or model calls were performed in this review.

The foundation remains useful: explicitly labeled demo mocks, injectable local perception, preserved observation source IDs and separate deterministic activity helpers. The next work is completing those interfaces and fixing their demonstrated edge cases, not replacing Mridul's engine.

## Ownership update — important change from the previous audit

The ownership disagreement about `src/accessflow/adapters/perception_worker.py` now has a documented user decision: **the worker is Atishay's deliberate exception to the general A-owned adapters directory**. `docs/CONTRACT_PROPOSALS.md` records this, and Mridul's latest message confirms that his agent was told not to touch it.

Accordingly, this report assigns the worker wiring to Atishay. The other A-owned adapters, corpus, controller, contracts, evaluation, root configuration and lockfile remain Mridul's. The previous audit's request to resolve the ambiguity is satisfied; do not keep reopening the directory-rule argument.

Atishay's normal owned areas remain perception, turn policy, demo, their tests, feedback/presentation and his handoff. Make additive interface/dependency proposals rather than editing shared contracts or the lockfile unilaterally.

## B0 — P1: complete the explicitly assigned vision worker integration

**File:** `src/accessflow/adapters/perception_worker.py:30–33,67–70`.

The parent passes vision flags, but the child parser accepts only `--model-path`; `_serve` calls `LocalPerception(model_path=...)` without the existing vision-provider argument.

Repeated offline reproduction:

```powershell
uv run --offline --frozen --extra dev python -m accessflow.adapters.perception_worker `
  --model-path audit-nonexistent-model --vision-provider ollama
```

Observed: exit 2, unrecognized arguments. This happens before loading a model. The temporary-edit vision experiment remains a feasibility result, not a working route in this checkout.

**Required change:** accept optional provider/model/URL configuration in the child; construct the agreed A-supplied provider and pass it to `LocalPerception(vision_provider=...)`; keep provider `none` as the default. Agree timeout propagation with Mridul if the parent must expose another flag—the current parent does not expose a `--vision-timeout` flag merely because proposal prose mentions one.

Do not replace the JSONL protocol, stdout isolation, cancellation behavior or A's provider implementation. Your existing perception constructor seam already works; use it.

**Acceptance:**

- Tests exercise the actual child parser/constructor route, not only direct provider calls.
- Default audio-only behavior and startup errors remain predictable.
- A configured PNG produces a sourced observation through the process adapter.
- Backend failure is an error, never an invented caption.
- Model/URL/deadline settings agree with recorded configuration; “requested” is not reported as “actually observed” before inference succeeds.
- Integration can be tested with an explicit provider double before a separate real vision run. Keep fake and real evidence distinct.

## Existing B findings — still open in this checkout

### B1 — P1: transcript revisions use different utterance IDs

`demo/index.html:70` increments the utterance counter and resets revision on every partial/final send. Two partials and a final are three different utterances, rather than replacements of one hypothesis. The code is unchanged from the previous script-level reproduction.

Allocate one ID for an active utterance, increment its revision for each replacement, and finalize that same ID. Allocate a new ID for the following utterance/session. Test partial → corrected partial → final, final without partials, and an interrupted/reset input. The frontend must not concatenate obsolete hypotheses.

### B2 — P1: no browser interruption route or controls

`demo/app.py:event_from_message` still accepts only transcript/audio/frame. A current probe with `kind='interrupt'` raises `ValueError`. There is no explicit stop-output versus stop-task control.

Translate the existing typed interruption event with its scope, timestamp and associated utterance, and expose understandable controls. The controller handles cancellation and committed effects; the UI must not invent rollback. Test while a fake reasoner/tool is slow and verify continued usability afterward.

The heuristic policy also has no explicit stop result. Do not solve that by canceling on every occurrence of the word “stop.” Distinguish stop speaking, cancel task, quoted content and ambiguous speech through the agreed semantic boundary.

### B3 — P2: audio timestamps are discarded

`demo/app.py:158–167` copies path, utterance ID and revision into `Audio`, but not speech start/end. A fresh probe supplies `12.5` and `14.5`; the resulting event contains **0 and 0**.

Preserve valid supplied timing and define its clock domain. Upload completion is not speech end. For recordings without original live timestamps, use an explicitly defined replay timeline or mark the measurement unavailable. Test nonzero values through message → input event → observation so default-zero bugs are visible.

### B4 — P2: media validation accepts header-only files

Current temporary-file probes confirm:

- A **24-byte PNG prefix** with width/height but no complete image passes perception and demo validation.
- A WAV truncated to its **44-byte header** passes `validate_wav` and reports 320 nonexistent audio frames.

Use bounded complete validation/decoding appropriate to supported inputs. Share helpers between upload and perception to avoid two divergent validators. Reject missing/truncated data, excessive dimensions/duration and unsupported formats before inference. Use a maintained decoder through an agreed dependency where appropriate; Mridul owns the lockfile change.

### B5 — P2: upload limits are late; malformed input can end the session

The full base64 payload is decoded before the 8 MiB check. The browser reads/encodes the entire file first. Session queues and aggregate media storage are not bounded by that per-file check. Decode/validation/disk work also executes directly in the receive coroutine.

Validate types and encoded length before allocation, keep server-side decoded/aggregate limits, bound queued work, and keep heavy processing off the event loop. Return recoverable structured input errors where safe instead of losing the session after one bad upload. Test malformed shapes, wrong base64 types, oversized/repeated uploads, interruption during processing and temporary-file cleanup.

Before connecting real perception, remove arbitrary client-provided local paths or replace them with explicit server-owned fixture IDs. Current mock handling does not demonstrate arbitrary file reading, so this is a real-backend integration guard, not a claimed existing exfiltration exploit.

### B6 — P2: `innerHTML` is unsafe for real response content

`demo/index.html:60` embeds serialized event JSON in an HTML string. JSON encoding does not escape HTML markup. The construction remains unchanged from the earlier probe that placed an unescaped image/event-handler tag into the sink.

Build DOM elements and use `textContent`. Test that model/user/tool strings containing markup display literally, create no nested executable elements and remain readable. This audit did not execute a browser exploit; current fixed mock response text limits the reachable content path. Fix the sink before wiring real responses.

### B7 — P2: activity classification changes with PCM bit depth

`energy_activity` compares raw RMS against 500 while `load_pcm` preserves 8/16/24/32-bit sample widths. A fresh same-relative-amplitude probe yields inactive for 8-bit and active for 16-bit. Valid centered 8-bit values cannot reach the default threshold at all.

Normalize to a documented canonical format or use threshold units relative to full scale. Define conversion into WebRTC VAD's required 16-bit format; accepting a WAV is not the same as making it VAD-ready. Test equivalent amplitude across widths, silence, clipping, stereo downmix and supported rates. Treat anti-aliasing/resampling quality as a separate experiment rather than assuming a linear resampler is adequate for all rates.

### B8 — P1 product milestone: acoustic timing still does not drive actual turn completion

`LocalPerception` transcribes a whole WAV and emits `final=True`. The current heuristic decides from transcript text/revision/final status. Activity/VAD/timing helper outputs are not integrated into that decision path.

This is valid whole-file ASR plumbing, not evidence of patiently waiting through live pauses. Define completed-file versus incremental capture semantics and propose additive observations if needed. Build B-owned policy replay with an injectable clock and labeled speech-end/activity evidence. Compare short/long silence baselines and the combined policy using the same recordings; include fluent speech so extra waiting is penalized.

Report premature completion, missed completion, additional wait after labeled speech end, task-relevant ASR errors and clarification count. Do not claim that model acknowledgment latency demonstrates better conversational timing.

### B9 — incomplete demo and measurement milestones

- The microphone button still sends a synthetic filename; it performs no actual recording. Implement capture plus real format conversion rather than renaming browser audio to WAV.
- The WebSocket server still hardcodes mock perception/reasoning, a final-flag policy and empty tool manifests. Provide an explicit factory/configuration seam for A's real agent while retaining a clearly labeled offline mode.
- Add connection-state handling, safe send readiness, session restart and recording/upload cleanup. Existing controls do not handle closed sessions well.
- Improve programmatic input labels and keyboard behavior; keep detailed JSON traces separate from concise screen-reader announcements.
- Prepare independent, provenance-tracked media cases and voluntary feedback. Do not upload/record participant voices without specific agreement, or claim clinical validation from a few demonstrations.
- Recheck Atishay's current machine before repeating the historical Python 3.11 link problem as a current blocker.

## Work order for Atishay when he resumes his own portion

| Slice | Owned scope | Independent test route |
|---|---|---|
| 1 | Assigned vision worker configuration/wiring | Actual child parser plus provider double; preserve audio-only path |
| 2 | Browser revision/timestamp/interrupt correctness | Script/adapter tests and fake-agent WebSocket session |
| 3 | Safe output, complete media validation and bounded errors/uploads | Disposable valid/invalid media and DOM tests |
| 4 | Audio normalization and timing-policy replay | Generated PCM/activity inputs labeled as synthetic, injected clock |
| 5 | Actual microphone and configurable demo | Fake agent first, then agreed A interface |
| 6 | Independent media evidence, matched timing, feedback/presentation | Real measurements with provenance and explicit limits |

These slices can begin without Mridul hosting a service or lending an API key. Shared integration should still happen in small increments rather than waiting until the final day.

## What Atishay should not repair

The new audio clarification **scenario/oracle** defect, corpus blocking I/O and dispatch, corpus evidence-to-write authority, corpus allowlist exposure, scoreboard classification, spent-probe packaging and A's current status documents are Mridul's responsibility. No new recording is needed to repair his clarification fixture. Do not modify the controller to make your UI/perception test pass.

The original clarification/image engine deadlock is fixed in the current shared checkout. Preserve the existing observation contract instead of adding a workaround that grants write permission from an image.

## Handoff acceptance and copy-paste instructions

Suggested owned checks:

```powershell
uv run --offline --frozen --extra dev pytest tests/perception tests/demo -q
uv run --offline --frozen --extra dev ruff check src/accessflow/perception src/accessflow/turn_policy demo tests/perception tests/demo
```

Agree the location of any new worker integration tests with Mridul; do not silently take over all `tests/engine/`. After merging, the full suite must run as well. Passing offline tests does not replace a live worker/ASR/vision/microphone measurement.

> Read `docs/reviews/ATISHAY_REAUDIT_2026-09-16.md` and compare it against your actual branch. The inspected shared checkout was `919ed27`; do not overwrite newer unmerged work. The worker file is now your explicit ownership exception, while other adapters, contracts, controller, corpus, evaluation and root lockfile remain Mridul's.
>
> Complete the actual worker provider route and preserve default audio behavior. Fix utterance revision identity, audio timestamps, interruption messages, safe rendering and bounded complete uploads with independent tests. Then normalize audio and build the calibrated timing-policy experiment. Use fakes to develop independently, and label every measurement as synthetic, injected, whole-file ASR, or actual live inference as appropriate.
>
> Do not fabricate recordings, interpret image evidence as authorization, copy action logic into the frontend, silently bypass failed perception, or claim pause-handling quality from final-transcript-only tests. Record exact changed files, contract version, tests, timing, provenance, dependency proposals and limitations. Coordinate A-side requirements through examples and proposals rather than editing Mridul's implementation.
