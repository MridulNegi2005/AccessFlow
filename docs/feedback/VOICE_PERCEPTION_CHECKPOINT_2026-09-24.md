# Voice/perception checkpoint — 24 September 2026

Branch: `atishay/perception`, after merging local `main` (`749fe23`) at `f84bea7`.
This is Atishay-owned component and demo evidence, not a Samsung submission run.

## Reproductions and changes

- Before the owned policy fix, four focused assertions failed: finalized “Stop speaking while I think” and “Stop the washing machine” both became task `stop`; partial “Cancel this booking” and “Stop the whole task now” also became task `stop`.
- The owned policy now reserves `stop` for a narrow, **final** task-cancel phrase. A final device command such as “Stop the washing machine” is a normal complete request. “Stop speaking” is held as `continue` with maximum uncertainty, because the current shared `TurnDecision` has no output-only scope. This prevents accidental task cancellation but **does not implement spoken output stop**. Mridul must add/approve that typed effect under C24-2.
- The configured demo reasoner test now gives image-only and image-plus-question paths different answers, waits for the question's observed `event_id`, and requires the final's `caused_by_event_id` to match it. The existing browser projection test separately rejects old, unattributed and duplicate finals. This is deterministic loopback/mock evidence, not Qwen or a confirmed tool effect.

## Actual local ASR; generated audio only

Model: installed `Systran/faster-whisper-base.en` snapshot `3d3d5dee26484f91867d81cb899cfcf72b96be6c`, Faster Whisper 1.2.1, CPU INT8 on Intel Core Ultra 5 125H, Python 3.12.10. The source is the pre-existing generated `tests/fixtures/audio/synthetic_pause_correction.wav` (SHA-256 `49B0B26FD1EBCAE0772B2559A4ABA3782444F59FAB7E7E7038122F06157C872B`). It is **not** a human microphone recording or a new held-out case.

Direct `WhisperModel.transcribe(..., beam_size=5, word_timestamps=True)` took 2.215 s after model construction. It emitted “Book Tuesday.” at 0.00–0.62 s and “Actually, Wednesday at 5.” at 2.64–5.04 s. Its word probabilities for Tuesday, Wednesday and `5` were approximately 0.945, 0.999 and 0.846. Those are backend decoder estimates, **not calibrated correctness confidence**. The same model returned zero segments for the 0.5-second generated tone in 1.495 s. These timings are single runs, not latency distributions.

The real `LocalPerception.observe(AudioEvent)` path on the correction clip took 3.356 s including adapter/model initialization and produced `faster-whisper/cpu-int8`, text `Book Tuesday. Actually, Wednesday at 5.`, `final=True`, source `correction-1`, revision 0 and **speech_start/speech_end both 0.0**. This verifies the present seam flattens useful segment timing/uncertainty and treats the complete WAV as final. It does not prove an official two-clip turn, semantic slot resolution or a booking.

The local browser served the demo with this ASR model at `http://127.0.0.1:8000/` and connected to its WebSocket. Start voice did not enter capture: Chromium reported microphone permission `prompt`, and the permission UI was not exposed to this test control. **No physical audio was captured or transcribed in this checkpoint.** A manual permission/speech pass remains required. `ollama` was not found on PATH, no configured vision/reasoner model environment variable was present, and nothing listened on port 11434; no live vision or Qwen result is claimed.

## C24 decision packet — both Atishay and Mridul must agree

| ID | Decision and example to agree | File split and independent next work |
|---|---|---|
| C24-1 official audio bridge | Two MP3 clips share utterance `u1`: clip 0 has `end_of_turn=false`; clip 1 has `end_of_turn=true` and corrects Tuesday to Wednesday. Define rooted admission, decoder owner, aggregate vs clip timestamps, byte/duration cap, finality/revision, interruption and cleanup. Do not finalize clip 0 or use organizer `_reference_text`. | Mridul: Samsung protocol/adapter, decoder/assembly, shared fields and boundary tests. Atishay: ASR/worker observations, revision tests and real-media measurements. Decoder ownership remains **unagreed**. |
| C24-2 speech clock and stop scope | Capture/activity timestamps need a declared clock conversion, including unknown endpoints. Final “Stop speaking” stops output only; final “Cancel this booking” cancels the task; “Stop the washing machine” is a device request; partial cancel text cannot stop the task. | Mridul: additive typed decision/interrupt contract, controller effects and timing metric. Atishay: acoustic facts, policy classification, browser capture and owned tests. Current policy's output-only `continue` is a safety interim, not completion. |
| C24-3 common runtime and causal replies | A newer spoken request `u2` arrives after an old image-only plan. The old final may be logged but must not render/speak for `u2`; a confirmed mock effect needs matching input, action and result IDs. Agree one configured factory/profile and dynamic tool manifest. | Mridul: reusable factory/configuration, manifest and authoritative IDs/effects. Atishay: demo adapter, browser projection and gated integration tests. The current empty-manifest mock demo is not the Samsung/Qwen runtime. |
| C24-4 image meaning and authority | Frame `f1` precedes the question, then `f2` replaces it; a contradiction with a user-confirmed slot requires clarification, not a write. Decide whether official frames wait for the next question while standalone demo frames may answer after debounce. | Mridul: readiness, conflict state, write guard and engine tests, including his four failing pending-frame probes. Atishay: frame/provenance observations, display and owned integration tests. The existing conflict xfail remains visible. |
| C24-5 media-to-task benchmark | For each consented recording/image, map media ID, SHA-256, format and label/exposure timestamp to a fresh task and effect oracle. A 60-case routing catalog is not 60 independently completed tasks. | Atishay: media provenance, ASR/activity/vision errors and exposure ledger. Mridul: executable task/effect oracles, official repeated runs, package and aggregation. No human set or new official run was produced here. |

## Checks and missing inputs

- `pytest tests/perception tests/demo -q`: 371 passed, 1 retained xfailed, 2 dependency warnings.
- Full `pytest -q`: 1203 passed, 2 skipped, 1 retained xfailed, 2 dependency warnings in 96.62 s.
- Focused reasoner correlation: 1 passed; `ruff` on changed owned paths, Node speech-lifecycle check and `git diff --check`: passed.
- The kit files named in the review (`WALKTHROUGH.md`, `docs/PROTOCOL.md`, `docs/SCORING.md`, `docs/SUBMISSION.md`) were absent at the documented `../participant-kit/participant-kit/` location and nearby Downloads searches. The merged readiness review was read, but this does **not** substitute for reading the kit. Obtain its location before claiming protocol-complete acceptance.
- Next: physical-mic permission and consented speech observation; an additive C24-1/2 contract decision; real vision backend availability; then common-runtime/effect integration and raw public media with Mridul.

## Capture permission-wait follow-up

The live local demo was refreshed after a browser-side capture fix. Before the fix, two `startMicrophone()` calls while `getUserMedia()` was unresolved made **two** permission requests and left the visible control saying “Start voice.” The owned Node regression failed at `2 !== 1`. After the fix, the browser visibly says **“Waiting for microphone permission”** and **“Recording has not started yet”** while the single request is pending; Start is temporarily disabled, and typed input remains available. A rejected permission request restores the control with one recoverable error. If a pending request is invalidated by a new task, disconnect or page exit, a later granted stream is stopped before recording begins; the deterministic test verifies one stopped track and no false error.

This is browser behavior and a simulated permission promise, **not** proof that the physical microphone worked. The in-app browser still did not surface an actionable permission dialog, so no raw human voice or audible playback was measured. No ASR, controller, Samsung protocol or shared-contract code changed in this follow-up.

An additional owned disconnect reproducer found that an already-started recording was not torn down when the WebSocket closed. The new `discardMicrophone()` path closes the recorder port, disconnects audio nodes, stops the physical tracks, closes the AudioContext and clears the unsent WAV. Session restart and page exit use the same teardown. A deterministic Node regression checks teardown calls, idempotency and disconnect/exit wiring. This is a simulated stream test; physical disconnect while recording is still unverified.

The same regression then reproduced a close race: if the WebSocket closed while `stopMicrophone()` awaited AudioContext shutdown, the old code encoded and staged a WAV after disconnect. A closed/closing socket now prevents that staging. The before-fix assertion observed one unwanted encode; it passes after the guard. This is still a simulated race, not a measured network or device run.

Final checks for this browser capture slice: `tests/demo tests/perception` **373 passed, 1 retained xfailed**; full repository **1205 passed, 2 skipped, 1 retained xfailed**, with two dependency deprecation warnings in 81.24 s. Repository Ruff, inline JavaScript parse and whitespace check passed.
