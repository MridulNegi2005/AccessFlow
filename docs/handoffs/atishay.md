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

**Read-only teammate update:** `origin/mridul/engine@81699c9` now contains A's
official MP3/end-of-turn bridge and configured-agent factory, but neither is
merged into this checkout. A's report retains a 23.688-second real public-frame
observation and a missed visual tail. Current local port 11435 has no listener;
no fresh B vision inference was run. A proposed optional bounded vision-output
setting, exact file split, test matrix and limits are in the feedback checkpoint.
Both teammates must agree the worker/provider/config seam and merge A through
main before B adopts the common runtime; no A file was edited here.

## 2026-09-24 — Direct ASR evidence probe

**Task:** Preserve timing and decoder uncertainty from the installed ASR backend while waiting for C24-1/2's shared contract decision.

**Owned change:** Added `src/accessflow/perception/asr_evidence.py` and `tests/perception/test_asr_evidence.py`. The opt-in CLI directly runs Faster Whisper on a supplied WAV, hashes the source, emits JSON segment/word offsets and raw decoder estimates, and explicitly declines to infer calibrated confidence or turn finality. It does not feed the agent or change `LocalPerception.observe`. Updated `docs/feedback/ASR_MEASUREMENTS.md` and the voice checkpoint.

**Backend/evidence:** Existing Faster Whisper 1.2.1 `Systran/faster-whisper-base.en` snapshot `3d3d5dee26484f91867d81cb899cfcf72b96be6c`, CPU INT8, Intel Core Ultra 5 125H; three checked-in **generated** WAV fixtures. The held-out generated repetition clip decoded `I want Tuesday, Tuesday, actually Wednesday at 5.` with two distinct Tuesday word offsets; inference took 1.676 s after 1.096 s model load. The pause/correction and tone results, hashes and other timings are in ASR_MEASUREMENTS. This probe uses word timestamps, so its outputs/timings need not exactly match the default live adapter path.

**Validation:** Dedicated injected-model tests 3 passed; owned demo/perception tests 376 passed, 1 retained xfailed, 2 dependency warnings; full suite 1208 passed, 2 skipped, 1 retained xfailed, 2 warnings in 85.82 s; Ruff clean.

**Failures/dependencies/next:** No physical microphone, human-speech or official MP3 evidence; local vision service unavailable and participant kit still missing at its documented path. Both Atishay and Mridul must decide C24-1/2 clock, clip assembly, uncertainty, revision and finality semantics before this data can affect the agent. Mridul's configured factory remains only on his unmerged branch, so C24-3 adoption awaits a reviewed integration; C24-4/5 gates remain open. Next independent B step is consented physical-mic capture and word/slot error logging once permission is available, plus actual pixel-grounded vision measurements when the backend is running. No A-owned code/config or shared contract changed.

## 2026-09-24 — Offline timing metric correction

**Reproduction:** Added an owned replay case with two acoustic pauses, a partial transcript available before them, and a final revision available only after recording ended. It failed before the change because the partial provisional endpoint was counted as a final-speech-end wait.

**Owned fix:** `src/accessflow/turn_policy/timing_replay.py` now computes final-end wait/match only from a revision marked final. Ungated acoustic candidates and the available partial revision remain observable; no `TurnDecision` or controller behavior changes. `tests/perception/test_timing_replay.py` covers a missed final and unknown wait.

**Validation:** Focused replay 8 passed; full suite 1209 passed, 2 skipped, 1 retained xfailed, 2 dependency warnings in 87.49 s; Ruff and diff check clean. This is deterministic offline timing evidence, not a real-device or official evaluation result.

**Open input:** The local browser reached microphone permission wait but recording did not start; user must allow access and provide a non-sensitive test utterance. Participant kit location remains unknown. C24-1/2 timing/finality and stop effect decisions remain joint with Mridul; no A files were edited.

## 2026-09-24 — Superseded-final replay measurement

**Reproduction:** Two owned parametrized cases failed before the fix. An earlier final revision matched an internal pause, then a corrected final arrived either before the trailing candidate or after recording. The report selected the older 0.8 s aggregate wait in both cases and missed the latter corrected final.

**Owned fix:** `src/accessflow/turn_policy/timing_replay.py` now associates aggregate wait/miss with the newest revision only if it is final. Historical acoustic candidates and the revision available at each pause are retained. A newer partial leaves aggregate wait unknown, even if an older final had a candidate. No shared contract, controller or browser behavior changed.

**Validation/limits:** `tests/perception/test_timing_replay.py`: 10 passed; full suite 1211 passed, 2 skipped, 1 retained xfailed, 2 dependency warnings in 85.98 s; Ruff and diff check clean. These are constructed offline timelines, not human microphone speech, official raw media, ASR accuracy or end-to-end interruption. C24-1/2 joint clock and finality semantics remain the integration gate; physical mic permission and participant kit path still require user input.

## 2026-09-24 — Installed ASR worker into actual Agent

**Task/evidence:** Exercised the installed Faster Whisper base.en CPU INT8 model through the actual `ProcessPerception` child worker on two checked-in generated WAVs; first call 4.921 s including startup/model load, second 1.650 s with the same child. A separate generated WAV reached the actual `Agent` controller in 4.678 s: its deterministic mock reasoner received `I want Tuesday, Tuesday, actually Wednesday at 5.`, the final was caused by the audio event, and zero tool calls/effects occurred. Child processes were closed. Fixture hashes, model snapshot, backend, transcripts and limits are in `docs/feedback/ASR_MEASUREMENTS.md`.

**Owned change/verification:** Added `tests/perception/test_live_worker_agent.py`, an opt-in regression requiring `ACCESSFLOW_TEST_WHISPER_MODEL_PATH`. It ran against the installed local snapshot and passed; without a declared local model it skips, with no download. With the model path set, full suite 1212 passed, 2 skipped, 1 retained xfailed, 2 dependency warnings in 89.57 s; Ruff and diff check clean. No A-owned adapter/controller/config code changed.

**Limits/next:** This proves actual local ASR-to-controller plumbing on generated audio, not human microphone capture, official MP3 admission, semantic end-of-turn, live reasoning, dynamic tools or a booking. The separate earlier manual controller run used the final-flag baseline and mock reasoner; the current opt-in regression uses `HeuristicTurnPolicy`. The real worker observation still has `final=True` and zero speech endpoints. Both Atishay and Mridul must settle C24-1/2 timing/finality and C24-3 factory/manifests before claiming the common real runtime; physical microphone permission, kit path and real vision remain open.

## 2026-09-25 — No-speech continuation and turn-policy regression

The user explicitly does not want to speak; no human audio was captured or uploaded. The localhost browser remained at permission `prompt`, and reload canceled its pending capture request, leaving the microphone off. An installed-model opt-in regression now passes generated held-out audio through the actual `ProcessPerception` subprocess, actual `Agent`, and Atishay-owned `HeuristicTurnPolicy`; it confirms a correction acknowledgment and final share the source audio event identity, with no fake tool effects. Focused test passed; full suite with `ACCESSFLOW_TEST_WHISPER_MODEL_PATH` set: 1212 passed, 2 skipped, 1 xfailed in 71.87 s. Ruff passed. No Ollama/model manifest or vision inference was available. Do not represent generated speech as human microphone evidence or as official Samsung media evaluation.

**Still requiring external/team input:** kit directory is not present at the expected repository-parent path; provide its location before official raw-audio/image protocol work. For C24-1/2, Atishay and Mridul must agree clip-vs-utterance timestamps, session-clock mapping, partial/final encoding, and how unavailable/uncertain estimates affect actions. For C24-3, agree runtime factory, model/reasoner selection, manifest source and the safety-gated mock write case; Mridul owns the engine/adapter/config pieces. C24-4/5 ownership and evidence criteria remain as in the dated review. Vision cannot be validated until an approved local/remote provider is available. No speech from the user is needed for continuing generated-fixture and synthetic-timeline tests.

## 2026-09-25 — Scope-safe cancellation and microphone run sheet

**Reproduction/fix:** An owned test first failed because `Cancel this booking` mapped to `TurnDecision(kind="stop")`; the engine handles that as global task cancellation. Narrowed the owned lexical rule so booking cancellation is a normal completed request, while explicit “Cancel this task”/“Stop the whole task” remains task stop. “Stop the washing machine” remains an ordinary request, and “Stop speaking” remains non-canceling pending the shared output-only-stop contract. Focused policy 22 passed; full suite 1215 passed, 3 skipped, 1 xfailed, 2 dependency warnings in 64.36 s; Ruff/diff clean. Opt-in ASR worker test skipped because no model path was configured in this suite run.

Added `docs/feedback/MICROPHONE_TEST_PROTOCOL.md` with one harmless correction script, browser permission/capture steps, explicit backend-label gate, evidence to report, and a separate interruption follow-up. This remains a user-run test; no human audio has been recorded. If the page reports `demo/mock audio`, stop before recording for an ASR claim and report the label. C24-1/2/3 coordination, real vision, official kit/media and the common configured runtime remain open.

## 2026-09-25 — Human microphone-to-ASR smoke check

**Evidence:** A user-provided browser screenshot shows the configured perception
label `local/Faster Whisper CPU INT8 audio`, the reasoner label
`demo/mock-reasoner`, and the recognized request “Set a reminder for Tuesday at
3, actually Wednesday at 5, tell me only the final time.” The mock response
echoed the input. This is one real microphone capture/upload and local-ASR
display check; it does not prove the agent resolved the time or created a
reminder.

**Limits:** No raw WAV, clip duration, device/browser identity, recognition
timings, live partials, turn-end timing or barge-in were captured. No real
action occurred. Uvicorn logs record connection events, not uploaded audio or
transcripts. The screenshot itself is the evidence and is not copied into the
repository; no personal audio is retained.

**Owned demo status label:** The pre-existing local edits expose perception
and reasoner backend names accessibly and say status is unavailable after
disconnect. Focused status-label regression and `tests/demo`: 150 passed, 1
retained xfailed, 2 warnings. Node answer-correlation, microphone
pending/disconnect and speech-lifecycle checks passed; Ruff on
`tests/demo/test_app.py` passed. The full repository suite was not run in this
slice. See `docs/feedback/MICROPHONE_TEST_2026-09-25.md` and the corrected
`docs/feedback/MICROPHONE_TEST_PROTOCOL.md`.

**Follow-on:** Added a pending C24-1/2 discussion draft to
`docs/CONTRACT_PROPOSALS.md` with concrete pause/continuation, repetition,
revision and stop-meaning examples, plus explicit clock/finality/uncertainty
questions. No shared schema or controller behavior changed. Rechecked live
vision availability: no local Ollama process/API; the participant kit is absent
from the expected path, so no live image or official raw-media run was started.

**Next:** Continue owned ASR uncertainty/turn timing, browser correlation and
failure-recovery acceptance. Streaming/barge-in and common-runtime integration
remain open; agree C24-1/2/3 with Mridul before changing shared signal/controller
semantics. No Mridul-owned code, contracts, configuration or external effects
were changed.

## 2026-09-25 — Polite-apology false correction

**Reproduction:** Three new policy cases failed before the fix for the ordinary
openers “I'm sorry, set a reminder for Wednesday” and “Sorry, set a reminder
for Wednesday”: the generic `sorry` token caused `possible_correction`. The
explicit in-utterance correction “Tuesday, sorry—Wednesday” correctly remained
classified as a correction.

**Owned fix:** Kept explicit correction markers and `sorry` used after an
existing phrase, but exempted a leading apology (“sorry” or “I'm/I am sorry”)
from correction matching. This is a lexical turn-policy change only; no shared
contract or controller semantics changed.

**Verification:** `tests/perception/test_turn_policy.py`: **25 passed**;
Ruff on the owned policy and test files and scoped diff check passed. This
improves local classification but is not human ASR or booking evidence.
The final combined owned regression set across demo, timing replay, policy,
audio and local perception finished **317 passed, 1 retained xfailed, 2
dependency warnings in 20.86 s**. C24-2 output-stop/timing semantics remain
jointly pending with Mridul.

## 2026-09-25 — Current-branch real-ASR Agent seam recheck

Reran `tests/perception/test_live_worker_agent.py` with the installed
Faster Whisper base.en CPU INT8 model through the actual `ProcessPerception`
child and `Agent`: **1 passed in 8.67 s**. The generated repetition fixture
(SHA-256 `d16355e7d1e702ebc309227e18bd9925a3ec7290cc7d454754d89dbaae55853f`)
retained two “Tuesday” tokens and “Wednesday”; acknowledgment/final causality
matched the audio event, with no fake tool effects and child cleanup. The
reasoner remains a deterministic mock; the timing is whole-test wall time, not
ASR latency. This is generated-audio plumbing evidence only. Focused offline
timing/audio/policy tests: **103 passed**. See
`docs/feedback/ASR_MEASUREMENTS.md`. Shared C24-1/2 semantics remain pending;
no Mridul-owned code or contract was changed.

## 2026-09-25 — Preserve actual-path ASR decoder evidence

**Changes:** `src/accessflow/perception/local.py` now retains raw Faster
Whisper segment/word metadata and exposes it to an optional immutable,
diagnostic-only `asr_evidence_sink`, correlated with event/source/revision.
Word timestamps are requested from Faster Whisper; estimates remain
uncalibrated, WAV-relative, and are not forwarded to `Observation` or used for
agent decisions. Empty decodes are reported to the sink before the existing
empty-text error; a failing sink is logged and does not suppress valid text.
Updated the model fake in the existing demo integration test to match the
actual Faster Whisper keyword signature. Increased only the scheduler margin
in two stale-frame timeout tests from 50 ms to 500 ms after the 50 ms test
expired before enqueue under full-suite load; production timeout behavior is
unchanged.

**Verification:** Full repository run on the final source: **1,218 passed, 4
skipped, 1 xfailed, 2 existing dependency warnings in 90.60 s**; Ruff across
the repository, four Node browser checks (answer correlation, speech lifecycle,
microphone pending and disconnect), and `git diff --check` passed. Fresh opt-in
model run on final source: `tests/perception/test_live_worker_agent.py`
**2 passed in 12.58 s** using installed Faster Whisper 1.2.1 base.en CPU INT8
and a generated WAV; the child/Agent leg used a mock reasoner and no tools.
The direct no-speech-like synthetic-tone probe returned no decoded segments,
but does not establish silence detection or noise rejection. No human audio
was recorded in this slice.

**Still open:** The sink is only on direct `LocalPerception`; Mridul owns the
process-worker transport. `Observation` still contains no decoder evidence,
and C24-1/2 must agree on raw-estimate, provenance, timebase and finality
semantics before shared integration or controller decisions. No participant
kit or local Ollama service was available on recheck, so official media and
live vision remain unverified. No Mridul-owned code/contracts/configuration
changed; branch changes remain uncommitted and unpushed.

## 2026-09-25 — Browser request/response correlation recovery

**Reproduction:** Added deterministic regressions showing that a multi-input
task could discard a valid final caused by an earlier input: the browser
required a terminal event to match only the last submitted source, including
when replaying a queued early final. A second regression showed that a late
engine `error` carrying an old `caused_by_event_id` could display over and end
a newer task.

**Owned fix:** Finals/clarifications and engine errors now require a cause ID
matching the latest known event for any source in the active browser task.
Queued terminal replies replay against that same task-local set. Errors without
a valid current-task cause are ignored; uncorrelated `demo_error` input and
transport messages remain visible. No engine, shared contract, adapter, or
configuration changes.

**Verification:** `tests/demo`: 150 passed, 1 retained xfailed, 2 existing
dependency warnings in 18.39 s. Node correlation regression and syntax check,
Ruff for the changed Python source test, and scoped `git diff --check` passed.
The regression failed before the fix under last-source-only matching. The full
repository suite was not rerun for this browser-only change. `uv run` could not
resolve the configured Python 3.11 minor-version link; tests ran through the
existing repository Python 3.12.10 virtual environment.

**Limits/open work:** This closes only the owned browser projection/recovery
slice of B24-3. It does not prove the configured live Agent runtime, real
reasoning, or an action. C24-1/2/3 decisions, shared runtime integration,
physical-mic timing/interruption evidence, live vision and official raw-media
evaluation remain open. No human audio was captured and no Mridul-owned files
were changed.

## 2026-09-25 — Final owned-tree validation checkpoint

**Verification:** On the current `atishay/perception` tree, the complete
repository suite passed: **1,221 passed, 4 skipped, 1 retained xfailed, 2
existing dependency warnings in 53.86 s**. Repository Ruff passed. Node answer
correlation, speech lifecycle, microphone-pending and microphone-disconnect
checks passed. With the already-installed Faster Whisper 1.2.1 base.en CPU INT8
snapshot selected explicitly, `tests/perception/test_live_worker_agent.py`
passed **2 tests in 8.90 s** on checked-in generated WAVs. This confirms local
ASR and event identity in the owned direct/child-worker tests; the Agent leg
still uses deterministic mock reasoning and no tools/effects. `git diff
--check` passed. Tests used the existing Python 3.12.10 virtual environment;
the pinned Python 3.11 `uv` minor link is unavailable on this host.

**Open acceptance gates:** no speech-triggered streaming/barge-in or measured
acoustic timing; shared C24-1/2/3 decisions and Mridul's configured runtime are
still required for common-agent integration. No Ollama endpoint was listening
on 11434/11435, so live vision/reasoning was not tested. The Samsung kit's
WALKTHROUGH/PROTOCOL/SCORING/SUBMISSION files were not found at the expected
participant-kit path or the searched local roots; official raw-media scoring
has not been run. The screenshot-backed human-microphone upload/ASR smoke is
documented separately and has no retained audio/timing evidence. No additional
speech was requested or recorded. Working changes remain uncommitted and
unpushed; no Mridul-owned source/contracts/configuration were changed.

## 2026-09-25 — PARTIAL configured-demo and error/stop checkpoint

See [`ATISHAY_DELIVERY_RESULTS_2026-09-25.md`](../feedback/ATISHAY_DELIVERY_RESULTS_2026-09-25.md)
for the 26-case checklist and narrow D1/D2/D3/D4 interface proposals. Merged
main `5dd2a56ce7f063335fb2fcb0fbfe4f127640e9a6` is an ancestor of this
branch. Browser error correlation and authoritative output-stop projection
are implemented, while two strict D1 Agent conformance tests still xfail.

The demo now has an explicit `ACCESSFLOW_DEMO_AGENT_MODE=configured` path to
Mridul's `build_configured_agent`, retaining its reasoner and policy, providing
a declared in-memory calendar mock manifest/executor, displaying backend
labels and projecting final observations without changing inference. Missing
backend settings never fall back to the mock demo. A fake-factory integration
test proves the adapter seam; a separate opt-in test reached installed Faster
Whisper through the browser WebSocket and common Agent with a mock reasoner,
then closed its native child after disconnect. This is not a completed real
reasoning/calendar/vision task.

Python 3.11.15 full suite: **1374 passed, 5 skipped, 3 xfailed, 2 dependency
warnings**; repository Ruff and four Node checks passed. Explicit installed
ASR selection ran three relevant tests successfully. Full Gate 1, twelve
real-model attempts, live automatic speech/end-session, image history and
four human-microphone cases remain open. No new human speech was requested or
recorded. No provider was configured in this shell and Ollama port 11434 was
closed; kit files were absent in the bounded local locations checked.

Additional deterministic follow-up: a scripted planner double through the
configured browser adapter and actual controller made no Tuesday effect from
partial speech and exactly one Wednesday 17:00 mock effect after a final
correction (`test_websocket_configured_correction_commits_only_wednesday_mock_effect`).
A separate controller/turn-policy test confirms spoken "Cancel this task"
invalidates a gated pending mock write while the session stays open. These
close deterministic V01/S04 only; neither tests a real planner or microphone.

## 2026-09-25 — PARTIAL live-voice checkpoint

Added an opt-in browser AudioWorklet live session in Atishay-owned demo code.
Configured process ASR can return provisional transcript previews while capture
continues; the browser uses a bounded quiet period to send a final WAV without
a Finish button. End session discards unfinished capture and stops local media
resources. The server routes previews to perception only, never to the Agent
as final observations. Deterministic JavaScript and fake-ASR WebSocket tests
cover revision order, resumed speech, final delivery, and cleanup.

The first full run had one stale HTML assertion for the old manual-send path;
that assertion was updated to check the new final-audio send path. The rerun
passed: 1376 Python tests, 5 skipped, 3 xfailed, 2 dependency warnings; Ruff,
five Node checks, and inline-page JavaScript syntax passed. No physical-mic
timing, real semantic endpointing, committed-effect closure, live model-quality
or image-history result is claimed. D2/D3 controller guarantees and D4 shared
registry/source semantics still require agreement with Mridul. This is a
checkpoint, not completion of the 26-case acceptance gate.

## 2026-09-25 — Installed-ASR preview and browser-state follow-up

Extended the opt-in configured WebSocket test to send pending speech, decode a
generated WAV as a provisional Faster Whisper preview, and then send a higher-
revision final WAV. The real local ASR preview preserved utterance/revision,
decoded the two Tuesday mentions and Wednesday correction, and made zero
mock-planner calls before final. It passed with the explicit installed model
path (1 passed, 2 existing dependency warnings); this is not a real reasoner
or physical-microphone result. A separate deterministic disconnect regression
holds a provisional preview in flight, then verifies cancellation, perception
closure and no final/observation output. It does not exercise an in-flight tool.

An in-app-browser mock smoke found that finishing a text request re-enabled
the unavailable live-voice button and replaced its honest help text. The
owned page now preserves the disabled state and configured-ASR guidance while
keeping End session enabled for an active session and fresh-session restart
enabled after closure. The new Node regression and browser recheck passed.
Initial local WebSocket upgrade failed because the `.venv` lacked the optional
runtime; local-only `websockets==17.1` enabled the check without changing the
project lockfile. The browser showed a mock echo, not a substantive answer;
no configured voice or physical-device browser state was tested.

Full Python 3.11 suite: 1377 passed, 5 skipped, 3 xfailed, 2 dependency
warnings in 114.80 s; Ruff and five Node checks passed. The D1 shared-stop
xfails, D4 shared image-history xfail, twelve actual-reasoner/vision attempts
and four agreed human-microphone cases remain open. Read-only local checks
found the installed ASR snapshot but no configured reasoning credential or
listening Ollama/vision service; the kit was absent from five bounded local
locations, not from the organizer generally. Mridul still owns shared D1/D2/D3
decisions and D4 registry/source guards; Atishay owns remaining browser,
perception and human-device conformance once those seams and providers exist.

## 2026-09-25 — PARTIAL D4 per-image perception correction

The owned `LocalPerception` vision worker now coalesces by frame ID, not every
frame in a session. Two separately identified images keep their own observations
even when Image 2 is admitted before Image 1 finishes. A failure from Image 1
is no longer hidden by Image 2's success. A same-ID replacement still suppresses
its old result/error. When one image is active and eight distinct images are
pending, an additional image gets an explicit queue-capacity error; the eight
accepted pending identities are not silently evicted. The demo perception
wrapper has a separate replacement-versus-distinct-ID regression.

The new two-image test initially passed because release raced ahead of Image
2 admission; a deterministic admission barrier exposed the intended failure
before the code change. The first broader run had five old newest-frame-only
test failures; those tests were revised to use same-ID replacement, preserving
their stale-result/timeout assertions, while distinct-ID behavior has new tests.
One demo-wrapper assertion was also still based on newest-only semantics and
was made a two-case replacement/distinct-ID check. Focused owned perception:
64 passed. Full Python 3.11 suite: 1381 passed, 5 skipped, 3 xfailed, 2
dependency warnings in 86.76 s; Ruff and five Node checks passed. Three
explicit installed-ASR opt-in tests passed separately in 28.45 s.

`test_conflicting_frames_require_resolution_before_write --runxfail` still
fails by a timeout waiting for both images in the shared reasoner view. This is
not proof of an unsafe write. Mridul must implement the bounded D4 registry,
admission ordinals, per-field source selection and write guards in shared
contracts/controller; the exact proposal is in `docs/CONTRACT_PROPOSALS.md`.
Atishay still must bind browser attachment display to accepted image IDs and
run I01-I04 through the integrated controller. No live vision model, official
media run or human microphone result was produced in this slice.

## 2026-09-25 — PARTIAL configured-process reconnect checkpoint

Added an opt-in L03 regression across two sequential configured WebSockets.
The first receives an actual Faster Whisper CPU INT8 preview from a generated
WAV, disconnects, and releases its native worker. The second receives a fresh
session ID and worker, decodes only its own final audio, and returns an
event-correlated mock-reasoner answer. Both workers close while the server
test loop remains alive. The first draft of the test shut that loop down before
the second worker's async reap completed; waiting inside `TestClient` corrected
the harness, without changing the shared process adapter or controller.

Full Python 3.11 suite: 1381 passed, 6 skipped, 3 xfailed, 2 dependency
warnings in 111.81 s; Ruff and five Node checks passed. Four explicit
installed-ASR opt-in tests passed in 36.88 s. L03 is PASS for this bounded
generated-audio/process-ASR route, not for physical microphone timing or an
actual reasoning/vision provider. D1 stop and D4 image-history xfails remain;
26-case aggregate Gate 1 fails, 12 actual-inference attempts and four agreed
human-microphone cases are still not run. Mridul's D1-D4 shared decisions and
controller work remain separate; no teammate-owned source was changed.

## 2026-09-25 — PARTIAL delayed-preview revision checkpoint

The owned live-voice capture now invalidates an in-flight preview when speech
resumes after a pause. A delayed old callback cannot put stale recognized
words back into the current turn; a later preview must use a newer revision,
and the final audio revision follows it. The deterministic browser harness
holds the old callback, resumes speech, verifies rejection before and after
the correction callback, and confirms one final WAV. This is V04 partial
evidence only: no physical microphone, actual delayed ASR response or shared
controller-authority race was tested. No Mridul-owned source was edited.

Final full Python rerun after this browser change: 1381 passed, 6 skipped,
3 xfailed, 2 dependency warnings in 107.04 s; five Node checks, browser
syntax, Ruff and diff check passed. An earlier full rerun had a `MemoryError`
and failed a one-second start wait in
`test_slow_image_provider_does_not_block_event_loop`; it passed alone and the
next full suite passed. Root cause was not established, so this failed run is
retained in the delivery report rather than erased.

## 2026-09-25 — PARTIAL repetition, End-session and PNG staging checkpoint

Added a configured browser/controller V03 regression: partial "two tickets"
followed by the repeated final phrase leaves the raw repetition visible to a
scripted reasoner and produces exactly one quantity-2 in-memory write, none
from partial speech. This proves deterministic effect handling, not actual
model quantity interpretation. Added L05 closure coverage for a gated mock
write: disconnect cancels the pending path without a late effect/final. The
browser End-session check now invokes the real handler and verifies pending
transport input is cleared, the socket/capture/playback close, and a late final
is ignored. Physical timing, native/remote work and committed-effect reporting
still need verification. The first gated-write test was rejected because its
scripted proposal omitted manifest dependencies; the corrected test reaches
the intended pending tool and passes without shared-code changes.

A read-only UI sidecar identified a real drop/picker mismatch: dropped PNGs
were previewed but the send route read only the file picker. The owned page
now stores the staged `File` and uses it for preview and upload. A new Node
regression covers dropped and picker PNGs. This does not implement D4 image
history: the page still stages one image and the shared registry/ordinal/source
projection is absent. The exact remaining receipt seam is proposed in
`docs/CONTRACT_PROPOSALS.md`; no Mridul-owned implementation was edited.

Full Python 3.11 suite: **1384 passed, 6 skipped, 3 xfailed, 2 dependency
warnings** in 111.29 s on the final run. Four explicit installed-ASR tests:
**4 passed** in 67.91 s (generated WAV, mock reasoner). Ruff, six Node checks, inline script
syntax and diff check passed. No configured reasoning provider was declared in
this shell; loopback 11434 did not confirm a vision service. Three bounded
local kit paths lacked `WALKTHROUGH.md`, not proof the kit is unavailable
elsewhere. Gate 1 still fails; Gates 2/3 remain not run. Next independent
Atishay work is receipt-bound attachment history once the authoritative D4
projection is agreed, plus physical-mic and real-inference runs when their
inputs/providers are available; Mridul owns shared D1/D2/D3/D4 behavior.

## 2026-09-25 — PARTIAL incomplete-correction endpoint guard

The owned live-voice capture now treats an ASR preview ending in a clear
continuation cue (for example, "Book Tuesday, actually") as unfinished. A
deterministic test first reproduced the old premature final after the normal
quiet threshold. The repaired path waits for resumed speech and a newer
preview; a completed correction still submits automatically. If the speaker
never continues, the turn emits a recoverable failed status after the bounded
wait and **no final WAV**. The Python suite now runs this Node regression.
This is a lexical safety guard, not general semantic endpointing or a
physical-microphone measurement. A long pause before any correction cue can
still end a fluent-sounding request; shared timing/finality and controller
authority remain D2/D3 work with Mridul.

The first full Python run on this change failed one unrelated-looking
Mridul-owned offline CLI corpus scenario: 3/4 fake cases, with the
device-correction case timing out after `missing_dependency` errors and zero
effects. The specific test passed alone and the no-parallel full rerun passed:
**1385 passed, 6 skipped, 3 xfailed, 2 dependency warnings** in 127.63 s.
The failure trace is summarized in the delivery report; its cause is not
established and no shared source/test was changed. Ruff, six Node checks and
live-voice script syntax passed. The separate installed-ASR opt-in rerun is
currently **failed**, despite earlier successful generated-WAV runs: a browser
preview became an error preview, and direct local perception exposed
`mkl_malloc: failed to allocate memory` with roughly 1 GB physical RAM free.
The diagnostic test hook was removed. The user assigned the memory bottleneck
follow-up to Mridul; do not rerun it in this workstream. This is not human
speech or an actual reasoning-model result.

## 2026-09-25 — PARTIAL receipt-bound image display

Owned browser code now retains a session-local list of PNGs only after a matching
server receipt. Each entry keeps its own source/event/revision, thumbnail and
observed or failed status; duplicate and old-session receipts are ignored. A
later text-only answer no longer displays the previously staged image. The
browser refuses a ninth local image before upload with an explicit error;
fresh session/unload revokes retained object URLs. End session leaves the
existing list visible while rejecting late changes. This is browser display,
not the D4 controller registry or a claim that an old image is selectable as
agent evidence. No Image 1/2/3 ordinal is invented: Mridul still needs to
project authoritative admission ordinal/receipt time and source status, then
we can bind the labels and field provenance.

Focused Node checks cover the ledger, rendered rows, current-request preview,
browser receipt/observation/error wiring and source-preserving picker/drop.
`tests/demo/test_app.py` passed **145 passed, 2 skipped, 1 xfailed, 2 warnings**;
the final standard full suite passed **1387 passed, 6 skipped, 3 xfailed, 2
warnings** in 65.41 s. Seven Node checks, Ruff, script syntax and diff check
passed. Installed-ASR was not rerun in this slice at about 1 GB free physical
memory, per user direction; Mridul will handle the previously recorded native
allocation failure.
Gates 1–3 remain incomplete as described in the delivery report.

## 2026-09-25 — PARTIAL bounded long-turn voice previews

The owned live capture used to stop requesting ASR previews after three. A
deterministic continued-speech test failed with only three previews; the
browser now allows later revisions within a bounded default of 12 previews
and 60 seconds per turn. Quiet completion (2.2 s), failure timeout (5.5 s),
preview interval (1 s), preview count and turn duration are validated timing
options. A long or preview-exhausted turn fails with a specific recoverable
message and **no final WAV**. A long/oversize turn also requires a fresh quiet
period before continuous speech can start another request, preventing a
suffix-only action. A configured longer quiet interval is tested.
This improves independent D2/V05 behavior but does not establish acoustic
endpoint quality, controller action authority or real microphone timing.

The post-guard standard full suite passed **1387 passed, 6 skipped, 3 xfailed,
2 warnings** in 69.82 s; seven Node checks, Ruff and live-voice syntax passed. The
memory-limited installed-ASR opt-in was not run per user direction. Mridul
owns that resource issue and the shared D1/D2/D3/D4 decisions; human-mic and
actual reasoning/vision gates remain unverified.

## 2026-09-25 — PARTIAL fixed Gate 2 development inputs

Predeclared four distinct real-inference paths and twelve attempt IDs in
`docs/feedback/GATE2_PREDECLARED_2026-09-25.json`. The two new WAVs under
`tests/perception/fixtures/gate2/` are generated by the owned PowerShell
script, not human recordings. The single-image PNG and two inline PNGs are
existing development assets; I inspected the visible `ERR-42`, `WED 5` and
`DEVICE B` labels. The owned preflight test verifies exact input hashes,
formats, four cases and twelve unique slots without invoking inference.
All attempts remain **NOT RUN**. Gate 2 still needs configured real reasoning
and vision, the installed-ASR resource issue is for Mridul per user direction,
and G2-04 also needs his D4 source-bound image registry. No owned test or
synthetic label is being counted as a model answer.

The current Python 3.11 standard suite passed **1388 passed, 6 skipped,
3 xfailed, 2 warnings** in 76.63 s; seven Node checks and Ruff passed.
The fixture preflight passed again after the WAVs moved into the owned
test area. See `docs/feedback/ATISHAY_DELIVERY_RESULTS_2026-09-25.md`.
