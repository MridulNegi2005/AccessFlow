# Atishay workstream handoff

## 2026-09-23 — AccessFlow frontend redesign

**Task:** Implement the approved Input Dock + Answer Stage visual direction in the owned browser demo.

**Changes:** Replaced the visible stacked developer UI with an ivory input dock and charcoal answer stage. Added multiline text entry with debounced partial revisions; WAV selection and microphone recording staged until Run; PNG selection/drop with local thumbnail/removal/full preview; response/clarification rendering with truthful backend provenance; follow-up chips/composer; optional browser speech and Stop; and a New task session reset. Removed visible raw JSON event cards, manual partial-send, the large backend banner, separate upload buttons, and Stop task control. Kept the existing event/session contract, media budget, WAV encoder, speech interrupt, and one-session behavior. Added a final-only demo observation notice for display/correlation; no shared contract or controller changed.

**Status:** Full suite 810 passed, 1 existing xfailed, 2 dependency warnings; Ruff, inline JavaScript syntax, and diff checks passed. Isolated Edge visual QA completed at 1440×1024, 834×1194, and 390×844 for empty and mock text states; generated PNG upload, preview focus/activation, loaded full-image dialog, and overflow behavior were checked. No deployment or push.

**Next:** Manually accept physical microphone permission, screen-reader/browser combinations, speech playback, and live/non-mock backend behavior. See `demo/FRONTEND_REDESIGN_SPEC.md` for tested scope and limitations.

Date and branch: 2026-09-16 / atishay/perception
Completed: Perception foundation, deterministic turn-policy baseline, replaceable PNG vision seam, minimal fake-agent demo, optional loopback Ollama JSON reasoner, opt-in local audio demo path, opt-in local Ollama vision path, session path isolation, local model configuration guard, synthetic audio/image provenance fixtures, PCM/activity baseline, local ASR seam, dependency-free PCM backend, optional VAD/timing candidates, session-scoped browser media upload, microphone WAV capture, held-out generated-case evaluation, weighted 60-case scenario inventory with hash-checked assets, feedback-session template, demo recording script, template-neutral presentation outline and multimodal end-to-end evidence implemented in owned paths; shared fakes/interfaces remain unchanged.
Contract version used: 0.1
Tests run and results: repository virtualenv pytest -q — 257 passed, 4 strict xfailed;
Configured vision environment wiring is covered through a loopback HTTP provider at the WebSocket route; the final retains image evidence with the later spoken question.
perception run — 133 passed; demo run — 108 passed, 4 strict xfailed; contract/engine — 16 passed;
held-out fixture check included;
Ruff and git diff --check clean for owned paths.
Live-model/backend results: Local Faster Whisper base.en CPU INT8 measured on the development and three generated held-out cases; a real local ASR plus injected-vision Agent composition completed in 3.222 seconds with both observations in one view; fresh Chrome also routed the speech fixture through faster-whisper/cpu-int8 before accepting a PNG in the same session, and the WebSocket route retains the latest transcript revision alongside the frame; the mock final exposed both prior modalities; the opt-in WebSocket demo route completed a checked-in WAV with the cached model and emitted a local-backend acknowledgment; an isolated Chrome run without a fake audio-device flag used the present Microphone Array and completed getUserMedia, AudioWorklet capture, WAV upload and the mock final; no human speech accuracy, live vision quality or endpoint-quality claim.
Configured vision failure is covered at the WebSocket boundary: backend_failure is emitted and a later text request completes in the same session.
The loopback OllamaVisionProvider regression exercises the real local HTTP request with local ASR in one Agent context; it verifies protocol payloads and provenance, rejects explicit incomplete responses, and does not claim live model quality.
In-flight frame coverage also proves a delayed stale frame result cannot enter the current reasoner view after a newer frame arrives.
The image boundary now rejects structurally incomplete or CRC-invalid PNG uploads before vision inference and removes rejected materializations.
The demo also has an optional loopback Ollama JSON reasoner selected by `ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL`; it bounds request context with valid JSON that preserves newest evidence, rejects explicit incomplete responses, bounds response size, strictly parses `PlanProposal`, and leaves the mock reasoner as the default. WebSocket regressions cover a recoverable reasoner failure and configured vision plus reasoning providers together: frame evidence and a later spoken request reach the configured reasoner and return an informational final, while the browser status labels both perception and reasoning backends. The local service was unavailable during verification, so live reasoning quality remains unmeasured.
Known failures: Default 3.11 uv target link is broken on this machine; human speech accuracy and endpoint quality, live vision quality, image-only controller integration, hosted backend, completed user feedback session and demo recording are not implemented. Functional browser, physical-device and injected multimodal smoke are recorded, but image-only response, changed-frame replacement and conflicting-frame resolution await engine integration; live ASR/vision quality and non-mock reasoning remain unverified. A current-head 1280x1600 headless Chrome capture shows no visible clipping, overlap or broken text in the inspected viewport; live interactive device behavior remains open.
Dependency or contract proposals: Local experiment uses optional webrtcvad-wheels 2.0.14; propose adding it to the shared audio extra after review. Browser smoke also required local-only websockets 17.1 for Uvicorn WebSocket support; propose adding a WebSocket runtime through the shared dependency owner. No lockfile or contract change was made.
Next independent task: Run live vision/reasoning scoring for the remaining scenarios, conduct the voluntary feedback session, then coordinate the engine integration slice for the four strict controller gaps.
AI tools/prompts/outputs and human modifications: Record each milestone in AI_USE_LOG.md.

The demo now removes invalid WAV materializations after post-header validation and reports injected ASR separately from Faster Whisper in its backend label; focused tests cover both behaviors.
The combined configured-backend WebSocket regression calls DemoPerception.from_environment with both modality settings, substitutes only the ASR implementation for deterministic text, and preserves source IDs and an informational final; the protocol service remains test-only evidence.
The WebSocket recovery regression also proves an ASR backend_failure does not end the session: a later PNG and spoken request complete with retained image context.
A fresh served WebSocket run combined the cached Faster Whisper base.en CPU INT8 backend with the configured OllamaVisionProvider over a loopback protocol service in 1.326 seconds; the final retained both recognized speech and image evidence. This remains mixed evidence with mock reasoning and no live vision-quality claim.
PNG validation now also checks the concatenated IDAT zlib stream for a complete, non-trailing decode; CRC-valid compressed corruption is rejected before vision inference.
The browser send path now checks WebSocket readiness and reports a labeled connecting error instead of throwing
when an input is submitted before the session opens.

## 2026-09-14 - Codex Atishay speech-cue modality boundary

**Task:** Prevent image captions from being interpreted as spoken correction or backchannel cues in the shared turn policy.

**Changes:** The owned heuristic policy now returns a high-uncertainty continue decision for image observations before speech cue matching. Added a regression covering correction and backchannel words in captions; text and audio policy behavior remains covered by the existing tests.

**Status:** Full suite 105 passed, 3 strict xfailed; focused policy suite 9 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay malformed multimodal payload recovery

**Task:** Keep the demo WebSocket session usable when a browser message contains a non-object multimodal payload.

**Changes:** Added explicit object checks for the browser message and its payload before typed event construction. The WebSocket route now converts malformed payload shape into a recoverable demo/input error; coverage verifies a later transcript still completes in the same session.

**Status:** Full suite 107 passed, 3 strict xfailed; focused transport regressions 2 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay truthful unknown-audio label

**Task:** Prevent the demo status label from claiming Faster Whisper for an injected audio backend that provides no backend identity.

**Changes:** Unknown injected audio backends now use the explicit local/unknown-audio label. The existing Faster Whisper fixture declares its identity, and focused coverage checks both truthful paths.

**Status:** Full suite 108 passed, 3 strict xfailed; focused label regressions 3 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay malformed vision response shape

**Task:** Keep malformed but syntactically valid Ollama JSON responses classified as backend failures.

**Changes:** The owned Ollama vision provider now rejects non-object JSON roots with a stable invalid JSON shape error instead of leaking an attribute error. Focused coverage uses list and null response bodies.

**Status:** Full suite 110 passed, 3 strict xfailed; focused vision suite 8 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay malformed vision JSON route recovery

**Task:** Verify malformed model JSON remains recoverable through the configured multimodal WebSocket route.

**Changes:** Added a loopback service returning a JSON list, exercised it through the configured OllamaVisionProvider and demo route, and verified the emitted backend_failure is followed by a successful transcript final in the same session.

**Status:** Full suite 111 passed, 3 strict xfailed; focused route and provider regressions 9 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay provider timeout boundary

**Task:** Verify provider timeouts normalize into the stable multimodal backend-failure boundary.

**Changes:** Added focused OllamaVisionProvider coverage for a TimeoutError from the transport opener; the provider raises the same classified RuntimeError used by route-level recovery.

**Status:** Full suite 112 passed, 3 strict xfailed; focused vision suite 9 passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-14 - Codex Atishay WebSocket session reset isolation

**Task:** Verify a fresh demo WebSocket session does not inherit prior multimodal context.

**Changes:** Added a two-connection regression that sends image and audio evidence in the first session, then checks the second session's transcript final contains neither prior modality.

**Status:** Full suite 113 passed, 3 strict xfailed; focused session regression passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay pre-decode upload limit

**Task:** Reject oversized encoded browser media before base64 decoding or session-file materialization.

**Changes:** Added a base64 length bound derived from the 8 MiB raw-media budget and a regression proving an oversized PNG payload is rejected without creating a file.

**Status:** Full suite 114 passed, 3 strict xfailed; focused upload regressions passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay configured vision-timeout route recovery

**Task:** Verify a configured vision transport timeout becomes backend_failure and does not end the multimodal WebSocket session.

**Changes:** Added a route regression using the actual OllamaVisionProvider with a timeout opener, then verified a later transcript final in the same session.

**Status:** Full suite 115 passed, 3 strict xfailed; focused provider and route timeout regressions passed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.


2026-09-15: Timestamp provenance follow-up on atishay/perception. The owned demo adapter now preserves
supplied event timestamps, forwards audio speech_start/speech_end, and carries frame timestamps into
image observations. The browser adds a capture-clock timestamp to every outgoing event. Full validation:
117 passed, 3 strict xfailed; demo 51 passed plus 3 strict xfailed; perception 50 passed. No protected
files changed.


2026-09-15: Added vision quota recovery evidence and a strict contradictory-frame reproducer on
atishay/perception. Quota failures emit backend_failure and allow later transcript recovery through
WebSocket. Conflicting frames remain a protected controller gap; an additive provenance/conflict
proposal is recorded. Full validation: 119 passed, 4 strict xfailed; demo 51 passed plus 4 strict
xfailed; perception 52 passed. No protected files changed.


2026-09-15: Aligned browser capture timing with the event envelope while retaining payload timestamp
compatibility. Existing provenance regressions pass. Full validation: 119 passed, 4 strict xfailed;
no protected files changed.


2026-09-15: Added passing in-flight cross-modal retention coverage: delayed audio survives frame
arrival and both observations reach one reasoner view. Full validation: 120 passed, 4 strict xfailed;
demo 52 passed plus 4 strict xfailed; perception 52 passed. No protected files changed.


2026-09-15: Added direct invalid-PNG materialization cleanup coverage; rejected bytes leave no session
file. Full validation: 121 passed, 4 strict xfailed; demo 53 passed plus 4 strict xfailed; perception
52 passed. No protected files changed.


2026-09-15: Added truthful unknown-vision labeling for identity-free injected adapters. Full
validation: 122 passed, 4 strict xfailed; demo 54 passed plus 4 strict xfailed; perception 52
passed. No protected files changed.


2026-09-15: OllamaVisionProvider now preserves structured HTTP quota details, including a 429 JSON
error body, through the provider failure boundary. Full validation: 123 passed, 4 strict xfailed;
demo 54 passed plus 4 strict xfailed; perception 53 passed. No protected files changed.


2026-09-15: Added WebSocket-level HTTP 429 vision quota recovery evidence. The actual provider error body
is normalized to backend_failure and the same session completes a later transcript. Full validation:
124 passed, 4 strict xfailed; demo 55 passed plus 4 strict xfailed; perception 53 passed. No protected
files changed.


2026-09-15: Added perception responsiveness evidence for slow image inference. A worker-backed vision
provider allows an async heartbeat to complete while the provider is blocked; full validation: 125
passed, 4 strict xfailed; demo 55 passed plus 4 strict xfailed; perception 54 passed. No protected
files changed.


2026-09-15: Added slow-ASR worker responsiveness evidence alongside the slow-vision regression. Both
replaceable perception providers leave an async heartbeat usable while blocked. Full validation: 126
passed, 4 strict xfailed; demo 55 passed plus 4 strict xfailed; perception 55 passed. No protected
files changed.


2026-09-15: Hardened browser rendering of untrusted multimodal output by replacing innerHTML with
textContent-backed DOM nodes. The existing UI regression now proves model and transcript payloads are
rendered as text. Full validation remains 126 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Moved browser media decoding and WAV/PNG validation off the WebSocket receive loop with
asyncio.to_thread while preserving the synchronous event adapter API. Focused media/recovery tests and
full validation remain green at 126 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Added owned perception guards for blank or non-string ASR and vision output. Malformed
provider results now raise a classified runtime failure before an empty observation is emitted. Full
validation: 128 passed, 4 strict xfailed; demo 55 passed plus 4 strict xfailed; perception 57 passed.
No protected files changed.

2026-09-15 verification: DemoReasoner now bounds prior multimodal context to 16,384 characters,
retains the newest evidence when truncation is required, and has regressions for recency, exact
capacity and request completeness. Full suite: 129 passed, 4 strict xfailed; perception 57 passed;
demo 56 passed, 4 strict xfailed.

2026-09-15 verification: Added provider and WebSocket recovery coverage for syntactically invalid
vision JSON bytes. The failure is classified as backend_failure and the same session accepts a later
transcript. Full suite: 131 passed, 4 strict xfailed; perception 58 passed; demo 57 passed, 4 strict
xfailed.

2026-09-15 verification: Tightened injected vision provenance labeling so a model-only object is not
presented as Ollama without an explicit ollama/ backend identity. Full suite: 132 passed, 4 strict
xfailed; perception 58 passed; demo 58 passed, 4 strict xfailed.

2026-09-15 verification: Added an opt-in finite LocalPerception timeout for audio and image provider
calls, with modality-specific timeout errors and WebSocket recovery coverage. The timeout bounds the
async caller; synchronous work already running in to_thread remains non-forcibly-cancellable. Full
suite: 141 passed, 4 strict xfailed; perception 66 passed; demo 59 passed, 4 strict xfailed.

2026-09-15 verification: Guarded LocalPerception observer cancellation so the child awaitable is
cleaned up even during initial scheduling, with a regression for an already-running audio worker.
Full suite: 142 passed, 4 strict xfailed; perception 67 passed; demo 59 passed, 4 strict xfailed.

2026-09-15 verification: Added WebSocket recovery evidence for a vision failure followed by a valid
frame and WAV in the same session. The final informational response retained both recovered
modalities with source IDs and truthful backend labels. Full validation: 143 passed, 4 strict
xfailed; demo 60 passed plus 4 strict xfailed; perception 67 passed. No protected files changed.

2026-09-15 verification: Added independent bounded LocalPerception workers for audio and image, with
same-session frame and same-utterance revision coalescing, stale-result suppression, session-scoped
keys, and idempotent DemoPerception shutdown cleanup. Full validation: 149 passed, 4 strict xfailed;
demo 61 passed plus 4 strict xfailed; perception 72 passed. No protected files changed.

2026-09-15 verification: Completed the bounded-worker failure matrix. Stale vision exceptions and
timeouts are suppressed after a newer frame, while the current frame and later WAV remain usable in
one WebSocket session. Full validation: 152 passed, 4 strict xfailed; demo 62 passed plus 4 strict
xfailed; perception 74 passed. No protected files changed.

2026-09-15 verification: Isolated bounded perception admission per session so concurrent sessions cannot
replace one another's pending frames. The two-session regression preserves each session's newest source
ID while same-session obsolete work is coalesced. Full validation: 153 passed, 4 strict xfailed; demo
62 passed plus 4 strict xfailed; perception 75 passed. No protected files changed.

## 2026-09-15 - Codex Atishay serialized WebSocket multimodal path

**Task:** Close the remaining owned transport and composition evidence gaps for multimodal input.

**Changes:** All demo outbound messages now pass through one sender task, so controller output cannot
overlap a media status or recoverable input error. Added a forced concurrent-send regression. Added a
WebSocket regression using the real LocalPerception model-path branch with a deterministic factory and
the real OllamaVisionProvider HTTP path; it verifies paired WAV/PNG provenance, timestamps, revision,
backend labels and an informational final.

**Status:** Full suite 155 passed, 4 strict expected failures; demo suite 64 passed, 4 strict expected
failures; perception suite 75 passed. Ruff, compilation and git diff --check clean. No engine, contract,
dependency or lockfile change. The deterministic ASR factory and loopback HTTP service are protocol
evidence; live model quality and non-mock reasoning remain unverified.

## 2026-09-15 - Codex Atishay concurrent WebSocket session isolation

**Task:** Verify session-scoped multimodal memory while browser connections overlap.

**Changes:** Added a route regression that keeps two WebSockets open together, sends an image only to
one session, and confirms the other session's fresh transcript final contains no inherited image context.

**Status:** Full suite 156 passed, 4 strict expected failures; demo suite 65 passed, 4 strict expected
failures; perception suite 75 passed. No engine, contract, dependency or lockfile change.

## 2026-09-16 - Codex Atishay multimodal shutdown admission

**Task:** Prevent late perception work from entering after session shutdown.

**Changes:** LocalPerception now closes admission before validation can register a session worker, and
closed workers reject a race that already captured a worker reference. DemoPerception ignores post-close
observations, and the demo sender exits cleanly when a WebSocket peer has closed. Parameterized audio and
image validation-race tests plus post-close demo tests cover the boundary. The configured WebSocket
composition regression now carries text, WAV and PNG together; the timing-policy seam was a strict expected
failure at this checkpoint and its additive proposal was recorded. It was subsequently promoted in the owned
policy layer while shared engine/controller integration remains pending.

**Status:** Full suite 162 passed, 5 strict expected failures; demo suite 68 passed, 4 strict expected
failures; perception suite 78 passed. Ruff, compilation and git diff --check clean. No engine, contract,
dependency or lockfile change.

2026-09-16 verification: Added route-level cleanup coverage for valid uploaded WAV and PNG files. Both are
present inside the live session directory and the temporary directory is removed after disconnect. Full suite:
163 passed, 5 strict expected failures; demo 69 passed plus 4 strict expected failures; perception 78
passed. No protected files changed.
2026-09-16 verification: The configured composition regression now sends two revisions for one WAV
utterance and verifies that the latest transcript and timing remain beside the text and PNG evidence.
No protected files changed.
2026-09-16 verification: The concurrent WebSocket isolation regression now carries image and audio in the
first open session and confirms the second session's fresh text has neither inherited modality.
2026-09-16 verification: Added configured WebSocket recovery coverage for a failing audio revision followed
by a corrected revision for the same utterance while a PNG remains in context. Full suite: 164 passed,
5 strict expected failures; demo 70 passed plus 4 strict expected failures; perception 78 passed.
2026-09-16 verification: Configured multimodal evidence now verifies distinct generated event IDs for the
retained text, corrected audio and image observations. No protected files changed.
2026-09-16 verification: Promoted the owned turn-policy timing seam to accept optional ActivitySummary metadata and
added focused coverage proving pause timing keeps partial speech open and never overrides final-transcript completion.
Shared engine/controller wiring remains the pending additive proposal. Full suite: 166 passed, 4 strict expected
failures; demo 70 passed plus 4 strict expected failures; perception 80 passed. No protected files changed.
2026-09-16 verification: Made the conflicting-frame strict example deterministic by waiting for frame one to reach
the reasoner before sending frame two. It remains an expected controller integration failure rather than a rapid-frame
coalescing artifact. No protected files changed.
2026-09-16 verification: Corrected the conflict reproducer to use two valid content-distinct PNG uploads and assert
the injected Tuesday/Wednesday captions. With --runxfail it reaches the expected write-safety assertion, isolating
the controller conflict-state gap. No protected files changed.
2026-09-16 verification: Reviewed origin/mridul/engine at 919ed27 in a disposable overlay with current owned
demo/perception paths. Targeted active-frame replacement and image-only informational tests pass upstream; the
conflict case is blocked before planning because the prior frame is removed. The pending additive seam must compare
or record superseded visual evidence before replacement. No protected files changed.
2026-09-16 verification: Opened the existing browser media, console and microphone captures directly. The shown
viewport has no visible clipping, overlap or broken text. The captures are dated 13–14 September, so fresh
current-HEAD full-page visual inspection remains open. No protected files changed.
2026-09-16 verification: The bounded audio worker now retains pending work per utterance key, preventing a newer
revision from starving an unrelated queued utterance. Full suite: 175 passed, 4 strict expected failures.
2026-09-16 verification: A real local Uvicorn/WebSocket session accepted WAV, PNG and transcript inputs in one
session; the final transcript retained both audio and image evidence. No protected files changed.
2026-09-16 verification: Browser sends now queue in order while the WebSocket connects, with a bounded queue and
clear closed/full transport errors. Full suite: 175 passed, 4 strict expected failures. No protected files changed.
2026-09-16 verification: Current-head served run used cached Faster Whisper base.en CPU INT8 plus a loopback Ollama
vision endpoint. The speech fixture was transcribed and the final transcript retained both audio and image evidence;
reasoning remained mock and no live quality benchmark is claimed.
2026-09-16 verification: Browser transcript controls now preserve one utterance ID across partial and final
hypotheses, increment revisions for each follow-up submission, and close the active utterance after the final
hypothesis. Focused demo tests and JavaScript syntax validation passed; no protected files changed.
2026-09-16 verification: Browser media IDs now come from a page-scoped monotonic allocator, preventing rapid WAV, microphone and PNG submissions from reusing source identities. Lazy send payloads also prevent rejected connecting-queue actions from consuming transcript revisions or media IDs; the direct browser queue/revision harness passed. No protected files changed.
2026-09-16 verification: Shielded threaded browser media materialization from receiver cancellation and drained active materialization tasks before temporary-session cleanup. Added a focused disconnect/cancellation regression; full suite: 176 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Hardened PNG validation against oversized declared dimensions by grouping scanline accounting, bounding decoded payloads at 64 MiB before decompression, and removing the unbounded zlib flush. Added a huge-dimension regression; full suite: 177 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: PNG validation now requires a valid palette before IDAT for indexed-color images and bounds palette entries by bit depth. Added a structural regression; full suite: 178 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Fresh current-head Uvicorn/WebSocket smoke accepted the checked-in WAV and a valid PNG in one session, then returned a mock final retaining both audio and image context. No protected files changed.
2026-09-16 verification: Tightened PCM target-rate, energy-activity, WebRTC VAD and pause-threshold validation to reject booleans, wrong numeric types and non-finite values with stable ValueErrors. Added focused cases; full suite: 187 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Energy activity now validates AudioBuffer sample-rate and sample-width metadata before frame timing calculations. Added invalid-metadata regressions; full suite: 188 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Captured the current demo head through local headless Chrome at 1280x1600. The full page showed no visible clipping, overlap or broken text; live interactive device behavior and live model quality remain separate evidence gaps. No source or protected files changed.
2026-09-16 verification: Added explicit labels for the transcript, WAV and PNG browser controls. A refreshed current-head 1280x1600 headless Chrome capture remained legible with no visible clipping or overlap. No protected files changed.
2026-09-16 verification: Energy activity now rejects PCM buffers with trailing partial samples instead of silently dropping bytes. Added focused coverage; full suite: 189 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Current-head Chrome CDP interaction drove text partial/final submission, checked-in WAV upload and generated PNG upload. The page showed connected/media acknowledgments and retained both prior modalities with zero console or page exceptions. No source or protected files changed.

## 2026-09-16 - PCM width normalization for activity and VAD

**Task:** Close the audio normalization gap identified in Workstream B finding B7 while preserving
the existing width-preserving `load_pcm` API.

**Changes:** Energy RMS values now use signed 16-bit full-scale units for 8-, 16-, 24- and 32-bit
PCM. The WebRTC adapter converts supported PCM widths to bounded little-endian signed 16-bit frames
before invoking its detector. Unsupported widths and malformed partial samples remain rejected.

**Status:** `tests/perception/test_audio.py` passes 38 tests; full suite passes 620 tests with one
retained expected conflict example; Ruff passes. This is deterministic offline evidence with an
injected detector. Held-out speech quality, live acoustic timing validation and live vision remain
unverified. Commits: `051f5f2`, `e021882`.

## 2026-09-16 - Browser interruption route

**Task:** Close the owned demo interruption gap using the existing typed `InterruptEvent` contract.

**Changes:** `event_from_message` now validates and translates `speech` and `task` interruption messages,
including optional utterance IDs, timestamps and envelope sequence. The browser now exposes separate Stop
speaking and Stop task controls, with the active utterance ID attached when available. Invalid scope and
field types return recoverable adapter errors. The engine and shared contracts were unchanged.

**Status:** Demo interruption coverage and the full suite pass: 102 demo tests with one retained expected
conflict example, 630 full tests with one retained expected conflict example; Ruff passes. No live browser
device or human feedback session was used. Commits: `cddcfc1`, `3f603a6`.

## 2026-09-16 - Bounded browser media intake

**Task:** Close the demo-side aggregate upload and pending-input gap from Workstream B finding B5.

**Changes:** The WebSocket session now owns a thread-safe 16 MiB aggregate media budget in addition to
the existing 8 MiB per-file bound. Reservations are made after base64 decoding and released when media
validation or materialization fails, so invalid input cannot consume the session budget. The incoming
event queue is bounded at 16 items; validation and disk work remain in the worker thread.

**Status:** Demo coverage is 105 passed with one retained expected conflict example; the full suite is
633 passed with one retained expected conflict example, and Ruff passes. Tests cover cross-modality budget
accounting, overflow without a new file and reservation release. No engine, contracts, adapters, lockfile
or live device behavior changed. Commits: `31fc5b7`, `660088a`.

## 2026-09-16 - Recoverable browser parse and critical PNG validation

**Task:** Close two bounded input-validation gaps found during the Workstream B continuation review.

**Changes:** The demo WebSocket now converts malformed JSON into a structured demo/input error and
keeps the session available for later valid events. The owned PNG validator now rejects unknown critical
PNG chunks before any vision provider call; ancillary chunks remain accepted. No engine, contract,
adapter, lockfile or script changes were made.

**Status:** The demo suite passes 106 tests with one retained expected conflict example; the focused
perception-local suite passes 45 tests. The full suite passes 635 tests with one retained expected
conflict example, and Ruff plus diff checks pass. Live vision quality remains unverified. Commits:
650e172, ee66a5.

## 2026-09-16 - Browser media failure cleanup

**Task:** Close the remaining cleanup edge in bounded browser media intake.

**Changes:** A materialized upload path is now removed for unexpected validator or disk exceptions,
while the thread-safe session budget reservation is released. Expected validation failures retain their
stable adapter messages. Added a regression that raises from the validator and proves both cleanup and
budget release.

**Status:** Demo coverage passes 107 tests with one retained expected conflict example; the full suite
passes 636 tests with one retained expected conflict example, and Ruff plus diff checks pass. Live vision,
device behavior and human feedback remain unverified. Commit: 9477b1b.

## 2026-09-16 - Accessible demo event announcements

**Task:** Close the remaining demo accessibility issue where the detailed JSON trace was also a live
screen-reader region.

**Changes:** The visible event stream now uses ria-live="off", while a visually hidden polite region
announces concise connection, error, clarification and final-response messages. The existing 	extContent
rendering and controller behavior remain unchanged. Source coverage checks the live-region split and
announcement helper.

**Status:** Full suite passes 636 tests with one retained expected conflict example; Ruff passes. A fresh
local browser smoke at 850px width rendered the page with body scroll width 835px, no horizontal overflow,
and no browser console errors or warnings. The temporary server and tab were stopped after inspection.
Commit pending after the evidence-only documentation update.

## 2026-09-16 - Bounded live announcements

**Task:** Keep the new screen-reader announcement region concise for untrusted model or input text.

**Changes:** Added a 240-character content bound with whitespace compaction for final responses,
clarifications and input errors. The complete event JSON remains in the visible trace for inspection.
A browser smoke sent a 1,200-character transcript and read back a 256-character announcement including
its prefix and ellipsis; the console remained clean.

**Status:** Full suite passes 636 tests with one retained expected conflict example, Ruff passes, and
git diff --check passes. Commit: b60f32a.

## 2026-09-16 - Activity frame timeline validation

**Task:** Close the timing-helper input invariant gap identified during the perception review.

**Changes:** ActivityFrame now validates finite non-negative timestamps, strictly positive duration,
non-negative integer RMS and boolean activity. Timing summaries and pause candidates reject frames whose
timestamps move backward, preventing negative or misleading silence measurements. This remains a timing
fact layer; no turn completion or controller behavior changed.

**Status:** Focused audio coverage passes 45 tests; the full suite passes 643 tests with one retained
expected conflict example. Ruff and diff checks pass. Held-out speech quality, live acoustic hardware
timing and live vision remain unverified. Commit: 3aec3b2.

## 2026-09-16 - Browser send close-race handling

**Task:** Keep browser transport errors recoverable when a WebSocket closes between readiness checking
and sending.

**Changes:** Added a small serialized-send boundary that catches send exceptions, emits a stable
transport error and returns failure to callers. Pending messages now stop draining after a failed send
without announcing a false connected state. Normal transcript sending was checked in a fresh browser
smoke; no controller or event contract changed.

**Status:** Full suite passes 643 tests with one retained expected conflict example; Ruff and diff checks
pass. The browser smoke produced a final response with no console errors or warnings. Commit: a5ece4b.

## 2026-09-16 - Browser session restart control

**Task:** Close the demo session-recovery gap after a WebSocket disconnect.

**Changes:** Added an explicit Restart session button. It stops an active microphone stream before
reloading the page, which clears the event trace and client counters and establishes a fresh WebSocket
session. A browser smoke created a final event, activated Restart session, and verified the new page
contained only the two fresh connection status events.

**Status:** Full suite passes 643 tests with one retained expected conflict example; Ruff and diff checks
pass. Browser smoke had no console errors or warnings and no horizontal overflow. Commit: 85f4b81.

## 2026-09-16 - Bounded browser output queue

**Task:** Close the slow-client response accumulation gap in the demo WebSocket route.

**Changes:** Added a 16-item outgoing queue bound to match the existing incoming bound. A browser that
stops reading responses now applies backpressure through the route instead of allowing unbounded output
accumulation. Added a focused implementation regression; normal client behavior is unchanged.

**Status:** Full suite passes 644 tests with one retained expected conflict example, Ruff and diff checks
pass. No engine, contract, adapter, lockfile or model/network behavior changed. Commit: 10d2069.

## 2026-09-16 - Offline timing-policy replay

**Task:** Advance the acoustic timing milestone without treating prerecorded activity as live turn
completion or changing the controller.

**Changes:** Added `turn_policy.timing_replay`, which replays the recorded held-out fluent and pause
VAD timelines against timestamped transcript revisions. The 0.4-second acoustic baseline exposes an
internal premature candidate, the 2.0-second baseline misses the held-out endpoints, and the combined
replay emits a trailing candidate only after the matching final revision is available. Stale and
mismatched revisions and all-silence input cannot emit candidates. The result contains endpoint
measurements only; it does not construct a `TurnDecision`, authorize tools or mutate session state.

**Status:** Focused timing/audio/policy coverage passes 87 tests; all perception coverage passes 190
tests; demo coverage passes 132 tests with one retained conflict xfail; the full suite passes 690 tests
with one retained xfail and two dependency deprecation warnings. Ruff passes. Commits: `378d178`,
`5fd2f91`, `fce7e62`. Live endpoint quality and live vision quality remain unverified.

## 2026-09-17 - Native lifecycle and assigned vision worker

**Task:** Reproduce and close the native-work timeout/close defect, then complete the explicitly assigned process-worker vision wiring.

**Changes:** A gated transcriber reproduced three timed-out awaits leaving three active native calls with peak concurrency three after `aclose()`. `LocalPerception` now holds one native-work permit per session worker until the underlying thread returns, detaches timed-out wrappers without canceling the thread, and tracks outstanding native tasks through completion. Independent sessions retain independent audio/image concurrency. The assigned JSONL worker now accepts `none` or `ollama`, model, base URL and timeout options, builds the A-side `OllamaVisionProvider`, preserves its `ollama/<model>` identity, and closes the perception backend at EOF. The default path constructs the same audio-only perception object as before.

**Status:** Owned perception coverage: 217 passed. Demo coverage: 143 passed, 1 retained conflict xfail. Full merged suite: 807 passed, 1 xfailed, 2 dependency deprecation warnings. Ruff and git diff --check pass. Commits are local: `f50bd60` and `430103a`; not pushed per instruction.

**Evidence mode:** Native lifecycle evidence uses an injected gated thread and records actual active calls and peak concurrency: fixed result is one native call, peak one, one tracked after close, then zero after release. Vision-worker evidence uses an actual child process and a deterministic loopback HTTP `/api/chat` service; it verifies model, image payload, observation provenance and backend identity. No live ASR, live vision, live reasoning or microphone session was run.

**Notes:** C1-C4 remain coordination items; no controller, shared contract, other adapter, evaluation, engine-test, corpus or root configuration file was changed. A separate frame-conflict xfail remains untouched. Next work requires the four written decisions and their exact file splits before implementing B-side changes.

## 2026-09-17 - Verified continuation checkpoint

**Task:** Revalidate the merged branch after the native lifecycle and worker slices, then correct stale Workstream B status wording.

**Changes:** Confirmed `origin/main` was integrated without conflicts and that the current branch retains the newer lifecycle and worker implementations. Updated `docs/STATUS.md` so the owned Workstream B required-work list records both slices as completed.

**Status:** `tests/perception`: 217 passed; `tests/demo`: 143 passed, 1 xfailed; full suite: 807 passed, 1 xfailed, 2 warnings; Ruff and `git diff --check` pass. Branch is clean and ahead of `origin/atishay/perception` by 9 commits. No push, CI, release tag or protected-file edits.

**Notes:** Remaining B17-3 through B17-7 work is gated by written C1-C4 decisions. Sol was consulted for an architecture review and remains the single persistent advisor; no additional reviewer was started.

## 2026-09-17 - Live vision availability recheck

**Task:** Check whether live vision/reasoning evidence could proceed without fabricating a result.

**Changes:** Rechecked the executable, loopback Ollama endpoint, vision-model setting and hosted key. Recorded the result in `docs/feedback/VISION_MEASUREMENTS.md`.

**Status:** `ollama` is missing, `127.0.0.1:11434` is unavailable, no vision model is configured and no Groq key is present. No live benchmark was started. The branch remains clean before this documentation checkpoint; no source or protected files changed.

**Notes:** Deterministic loopback child-process evidence remains protocol/provenance evidence only. Live vision quality and C1-C4 decisions remain open.

## 2026-09-17 - Monotonic browser media admission budget

**Task:** Reproduce and close the owned media-budget refund path that allowed repeated invalid PNG validation work within one WebSocket session.

**Changes:** A deterministic CRC-valid PNG with an invalid filter byte was rejected repeatedly while the old budget returned to zero. `_SessionMediaBudget` now accounts decoded bytes monotonically for the session: every non-empty, per-file-valid decoded upload consumes quota even when media validation or materialization fails. Cleanup still removes failed temporary files, and pre-decode shape/base64/size failures consume no quota. Updated the old refund assertion and added a regression proving the aggregate limit rejects the third invalid PNG before validation.

**Status:** Focused budget tests: 4 passed. Demo suite: 144 passed, 1 xfailed, 2 warnings. Full suite: 808 passed, 1 xfailed, 2 warnings. Ruff and diff checks pass. Committed as `127a2c8`; no push or protected-file edits.

**Evidence:** Deterministic local invalid-PNG probe and test double only; no live service or user media. This bounds repeated decoded upload validation by session quota but does not claim a separate decompressed CPU budget.

## 2026-09-17 - Media admission security diff review

**Task:** Review the committed monotonic media-admission fix and its direct upload/materialization path.

**Result:** A bounded Codex Security diff scan reviewed `demo/app.py` for decoded-byte accounting, rejected-upload cleanup and cancellation-adjacent materialization behavior. It found zero reportable findings. Daybreak access was not granted, so this remains a local static review backed by deterministic tests; it does not claim live service evidence or a separate decompressed CPU budget.

**Scan:** `263348fe-a430-4ba6-bee6-f91882c33126`, commit `127a2c8`, base `5acfaeb`. No source or protected-file changes were made by the scan.

## 2026-09-17 - C1-C4 coordination packet

The remaining B17-3 through B17-7 changes are still pending written agreement with Mridul.
The smallest proposals and ownership split are:

- **C1 — image evidence and action authority.** Trace: spoken request `Book Wednesday` → frame
  `F1` → replacement frame `F2`; ordinary replacement keeps only `F2`, while a declared conflict
  produces `correction_pending` and no call/effect → spoken clarification resolves the evidence →
  exactly one authorized write. Decision needed: whether a new frame supersedes the prior frame by
  default, and how a user-fixed slot conflict is represented and resolved. Mridul owns the shared
  provenance/conflict contract, controller guard and engine tests; Atishay owns frame metadata,
  perception/UI translation and `tests/demo/` integration coverage.

- **C2 — speech timing and stop scope.** Trace: capture start → partial speech → acoustic pause →
  continuation or final; separately, `stop speaking` interrupts output while `cancel this booking`
  cancels the task, and a device command remains a device command. Decision needed: the clock domain,
  speech-end evidence and continued-pause rule, plus typed output-stop versus task-cancel scope for
  partial hypotheses. Mridul owns the additive contract, controller interpretation and timing
  harness; Atishay owns capture/activity evidence, turn policy and browser input events/tests.

- **C3 — one configured agent path.** Trace: CLI provider/model/endpoint/deadline → process worker
  and browser use the same configured factory → shared reasoner/provider protocol and tool manifest
  → deterministic mock tool call → effect result with backend labels. Decision needed: the canonical
  provider/reasoner interfaces, factory ownership and manifest source. Mridul owns the shared factory,
  execution contract and A-side configuration; Atishay owns demo wiring, the assigned perception
  worker and their child-process/browser tests.

- **C4 — media catalog into task evaluation.** Trace: media ID and SHA-256 provenance → isolated
  task mapping → ASR/vision observation → planner decision → terminal/effect oracle; consumed media
  remains consumed and is never relabeled unseen. Decision needed: which media IDs map to independent
  executable tasks, the terminal/effect oracle and exposure bookkeeping. Mridul owns executable
  scenarios, evaluation metrics and oracle packaging; Atishay owns media assets, capture/ASR/vision
  provenance, fixtures and labels.

No implementation is implied by this packet. Until each decision is accepted, the frame-conflict
xfail remains in place, stop policy remains unchanged, whole-file upload remains labeled as lacking
speech-endpoint evidence, the demo reasoner remains separate, and media replay remains routing/
observation evidence rather than completed task evaluation.

## 2026-09-23 - Stale-frame timeout boundary

**Task:** Reproduce and repair the intermittent stale-frame timeout reported on 22 September
without allowing overlapping native work.

**Changes:** Kept one native permit held by each underlying provider thread until its completion
callback. Documented the existing two-phase timeout semantics: provider execution retains the
historical `timeout_s` deadline, while permit admission has an independent bounded wait using
the same configured value. Queue expiry now reports that phase explicitly. Replaced the stale
frame test's fixed 50ms/10ms sleeps with an observed permit-acquisition gate, and added a
separate queue-expiry regression proving the second provider is never called while stale native
work remains in flight. Updated the repeated audio timeout assertion for the same distinction.

**Status:** The repaired stale-frame success test passed 20/20 repeated isolated runs; the
focused `test_local.py` module passed 58 tests; `tests/perception` passed 218 tests; the full
suite passed 809 tests with 1 retained xfail and 2 warnings; Ruff and `git diff --check` passed.
The original failure was scheduler-sensitive deadline timing, not inactivity or evidence that
native work could safely overlap. No engine, contract, adapter, dependency or media files were
changed. Live provider latency remains unverified.

## 2026-09-24 — voice-first frontend implementation

**Task:** Continue the approved Stitch-first AccessFlow design through the owned demo
implementation, while preserving the existing protocol and reporting the export gap.

**Changes:** Replaced the previous task-form presentation with the approved ivory voice
console / charcoal answer workspace; added compact typed input and conditional supported-media
submission; made stopping microphone capture submit its bounded WAV automatically; drove the
capture waveform from smoothed microphone RMS; added truthful status/provenance and a read-only
`/?preview=1` sample mode that opens no WebSocket. Kept the existing JSON envelope, event order,
IDs/revisions, queue/size limits, safe text rendering and separate speech-interrupt semantics.
Added the current change inventory, Stitch export log and supersession note for the earlier
frontend variant. No shared contract, engine, adapter, root config/lockfile or `docs/STATUS.md`
change.

**Status:** Full suite: 810 passed, 1 existing xfailed, 2 dependency warnings. Repository Ruff,
`git diff --check` and inline-JavaScript parse passed. Browser checks used the local Edge page
with demo/mock backends at 1536×1024, 1440×900, 1280×720, 768×1024 and 390×844; no horizontal
overflow. The mock text request rendered through the real local WebSocket; preview mode was
read-only and had no WebSocket; staged PNG, conditional send affordance and removal were checked.
No push, commit, deployment or publication.

**Limitations / coordination:** Physical microphone permission, real capture energy, live ASR,
streaming/endpointing, automatic barge-in, TTS playback and assistive-technology combinations
were not verified. The Stitch project was used for prompts 1–5, but the approved source PNGs
were not attached and native exports were not saved because this task exposes no browser surface.
Exact steps are in `docs/design/stitch/README.md`. Atishay and Mridul need to coordinate on
structured action identity/write outcomes, answer/frame causality and shared speech timing;
until then, unsupported meeting cards remain plain text and no success is fabricated.

### 2026-09-24 continuation — anchor previews and browser QA

The accessible Stitch project was inspected: `01-photo-answer` and
`02-meeting-correction` show the intended subjects but are 1280×1033 and 1280×1025,
not the requested 1536×1024. The approved PNGs and full `DESIGN.md` were not attached;
the file chooser did not complete. Two ZIP export attempts yielded no verifiable file.
The exact remaining manual review/export steps are in `docs/design/stitch/README.md`.

Added a clearly labeled, original illustrative dog PNG and static route; `/?preview=photo`
(also `1`) now shows the dog-photo composition and `/?preview=meeting` one corrected
Wednesday 5 PM draft. Both are deterministic, disable input actions and open no
WebSocket. The live demo still renders ordinary backend responses, not a fabricated
calendar card. At 390×844 the meeting card now stacks its fields, avoiding the
day/time collision; both previews loaded without horizontal overflow. At 1536×1024
both compositions were inspected. A normal text request completed through the local
demo/mock WebSocket, and the browser recorded no errors.

Verification from repository root: `.venv\Scripts\python.exe -m pytest -q` →
**811 passed, 1 existing xfailed, 2 dependency warnings**;
`.venv\Scripts\python.exe -m pytest tests/demo/test_app.py -q` →
**126 passed, 1 xfailed**. Ruff, inline JavaScript parsing and `git diff --check`
passed. `demo/app.py`, `demo/index.html` and `tests/demo/test_app.py` are the only
newly edited code/test paths in this continuation. No shared engine/contracts,
adapters, root config or lockfile were changed. Atishay and Mridul need to
coordinate structured action identity/write outcomes before live meeting-card
projection; causal media-answer and speech-interruption contracts remain open.

Delivery: `f0ca543` was pushed to `origin/atishay/perception` and the remote ref
verified. The two unrelated untracked review notes were not included. Stitch's
per-frame Download emitted no browser download event; Copy as PNG showed a
success toast but this session could not read image bytes from its clipboard.
No native Stitch asset was saved or claimed, and nothing was deployed.

### 2026-09-24 continuation — frontend interaction hardening

**Task:** Close browser-visible photo and long-answer defects and harden optional read-aloud
state without touching shared engine contracts.

**Changes:** The image dialog opens the image currently displayed, including the labeled
design sample, rather than depending only on a staged user upload. Its maximum image
height now fits within the dialog at a short desktop viewport. Long first sentences
over 120 characters remain intact in body copy beneath a short generic heading. TTS
utterances have a generation/identity guard; replacement or cancellation invalidates
old start/end/error callbacks before they can change the speaking UI. Stop speaking,
starting a new request, starting microphone capture, disabling read-aloud and session reset use the same
invalidation path. Added an owned Node.js lifecycle regression, run by pytest when
Node.js is available; no root dependency was introduced.

**Status:** Local `demo/mock` WebSocket answer checked in the in-app browser; the long
answer rendered with complete body text and no horizontal overflow. The sample-photo
button was reproduced failing before the fix, then opened a loaded full-size image
afterward. The dialog was visually inspected at 1280×720 and 390×844, with no inner
scrolling or horizontal overflow in those checks. Browser error/warning logs were
empty. `pytest tests/demo/test_app.py -q`: 127 passed, 1 existing xfailed.
Full `pytest -q`: 812 passed, 1 existing xfailed, 2 dependency warnings. Ruff,
inline JavaScript parse and diff check passed.

**Notes:** Browser TTS visibly entered its speaking state, but audible playback,
physical microphone behavior, live ASR/barge-in and all screen-reader combinations
remain unverified. Native Stitch exports remain unavailable; this is not design-stage
completion. Atishay and Mridul need to coordinate causal answer/frame identity,
structured meeting operation outcomes and shared speech timing before live action-card
projection. The two unrelated untracked review files remain untouched.

### 2026-09-24 continuation — browser answer causality

**Task:** Prevent an old image/text final from replacing the active follow-up.

**Owned change:** `demo/app.py` now exposes the already-existing observation
`event_id` in demo-only observation notices. `demo/index.html` registers each
request source, maps final observations to event IDs, buffers answers during
sequential media sends, and projects only a final/clarify whose
`caused_by_event_id` matches the latest dispatched source. Late, duplicate and
unattributed finals are ignored. Added `tests/demo/answer_correlation_check.cjs`
and WebSocket identity assertions in `tests/demo/test_app.py`.

**Evidence:** Local `demo/mock` text request visibly completed through the real
WebSocket after restarting the demo server. The 390×844 CSS-pixel layout had no
horizontal overflow in this browser check. Focused demo: 128 passed, 1 existing
xfailed; full suite: 813 passed, 1 existing xfailed, 2 dependency warnings.
Ruff, Node syntax and diff check passed. Stitch photo frame Download was clicked,
but no native file was verified. `docs/design/ATISHAY_DESIGN_QA.md` is blocked
pending normalized same-state comparison. Physical mic, real audio/model output,
native Stitch exports and live meeting-card updates remain unverified.

**Coordination:** Atishay and Mridul need to coordinate on authoritative
structured action identity/write outcomes and any shared speech timing rules.
Demo final-answer causality now uses the engine's existing ID field, with no
Mridul-owned engine/contracts/config change. The two pre-existing untracked
review notes remain untouched.

### 2026-09-24 continuation — merged voice/perception checkpoint

**Branch and preservation:** Fetched `origin/main` at `749fe23`, committed the prior
owned frontend changes as `bee5d6f`, fast-forwarded local `main` and merged it into
`atishay/perception` at `f84bea7` without conflicts. The two previously untracked
review notes were byte-identical to tracked copies in main; a named stash remains
as a redundant backup. No direct main push, reset or force-push.

**Owned changes:** Narrowed `HeuristicTurnPolicy` task-stop classification to final
task-cancel phrases; partial cancellation and output-only “Stop speaking” no longer
stop the whole task, and “Stop the washing machine” remains a complete device
request. Output-only spoken stop is still not implemented because the shared
decision lacks that scope. Strengthened the demo's configured-reasoner test so
image-only and combined answers differ and the accepted final must be caused by
the observed spoken question. No A-owned controller, contract, Samsung adapter,
configuration, lockfile or evaluation path was edited.

**Before-fix and checks:** Four new policy assertions failed before the owned fix;
they now pass. `tests/perception tests/demo`: 371 passed, 1 retained xfailed;
full suite: 1203 passed, 2 skipped, 1 retained xfailed, 2 dependency warnings.
Changed-path Ruff, Node speech-lifecycle and diff checks pass. The one focused
configured loopback reasoner correlation case passes. See
`docs/feedback/VOICE_PERCEPTION_CHECKPOINT_2026-09-24.md` for exact ASR timings,
fixture hash, limitations and the C24-1 through C24-5 decision packet.

**Actual model/device evidence:** Installed Faster Whisper base.en CPU INT8
transcribed the existing generated correction clip through both direct model
and `LocalPerception.observe`; the adapter emitted the correct text but flattened
segment timing and uncertainty, with final=True and zero speech endpoints.
The demo connected with that model, but the browser's physical microphone
permission stayed `prompt`; no live capture or human speech transcription occurred.
No live vision, Qwen or official raw-media run occurred. The Samsung kit files
were missing at the documented local path, so kit-dependent acceptance is still
unverified. Asked for the kit location and manual microphone permission/speech.

**Next:** Both Atishay and Mridul must agree C24-1/2/3 first (MP3/turn finality,
clock/stop scope, common runtime/identities); C24-4/5 remain explicit joint
decisions. Atishay can independently continue physical-mic observations, ASR
metadata/uncertainty fixtures and real vision availability checks. Do not call
the current mock browser result a confirmed effect or a Samsung submission pass.

### 2026-09-24 continuation — browser microphone permission wait

**Reproduction:** A deterministic owned Node harness called `startMicrophone()`
twice while the browser's permission promise was unresolved. Before the fix it
observed two `getUserMedia()` requests instead of one. The live local page also
gave no visual feedback while the permission remained pending.

**Owned fix:** `demo/index.html` now exposes a truthful waiting state, admits
only one pending permission request, recovers on denial, and invalidates pending
starts when a task begins, the WebSocket closes, the session restarts or the
page exits. A late-granted stream is stopped before recording. The new
`tests/demo/microphone_pending_check.cjs` is invoked by `test_app.py` and covers
duplicate start, pending UI, rejection and late-grant cleanup.

**Evidence and limits:** The focused test passes after the reproduced failure;
the live local page visibly showed “Waiting for microphone permission” with
Start disabled. `tests/demo tests/perception`: 372 passed, 1 retained xfailed;
Ruff and diff check passed. This is simulated permission and UI evidence, not
a physical-microphone recording or transcription. C24-1/2/3 coordination and
Samsung raw-media evaluation remain open; no Mridul-owned files changed.

**Disconnect teardown follow-up:** A separate owned Node reproducer found no
recording teardown on WebSocket close. The demo now discards an active capture on
disconnect, restart or page exit: stops tracks, disconnects nodes, closes the
AudioContext and clears unsent audio without invoking an upload. The simulated
helper/wiring regression passes; a physical disconnect during human speech is
still an open manual acceptance case.

**Close-race follow-up:** A second deterministic assertion failed before the
fix because `stopMicrophone()` encoded/staged audio after the socket closed
while AudioContext shutdown was pending. The stop path now drops that WAV if
the session is closing/closed. No actual voice or network interruption timing
was measured.

**Final validation for this owned capture slice:** 373 demo/perception tests
passed with one retained xfail. Full suite: 1205 passed, 2 skipped, 1 retained
xfail and 2 dependency warnings in 81.24 s. Ruff, inline JavaScript parse
and whitespace check pass. No physical-microphone permission was granted.
