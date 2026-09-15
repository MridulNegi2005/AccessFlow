# Atishay workstream handoff

Date and branch: 2026-09-15 / atishay/perception
Completed: Perception foundation, deterministic turn-policy baseline, replaceable PNG vision seam, minimal fake-agent demo, opt-in local audio demo path, opt-in local Ollama vision path, session path isolation, local model configuration guard, synthetic audio provenance fixtures, PCM/activity baseline, local ASR seam, dependency-free PCM backend, optional VAD/timing candidates, session-scoped browser media upload, microphone WAV capture, held-out generated-case evaluation, feedback-session template, demo recording script, template-neutral presentation outline and multimodal end-to-end evidence implemented in owned paths; shared fakes/interfaces remain unchanged.
Contract version used: 0.1
Tests run and results: repository virtualenv pytest -q — 142 passed, 4 strict xfailed;
Configured vision environment wiring is covered through a loopback HTTP provider at the WebSocket route; the final retains image evidence with the later spoken question.
perception run — 67 passed; demo run — 59 passed, 4 strict xfailed; held-out fixture check included;
Ruff and git diff --check clean for owned paths.
Live-model/backend results: Local Faster Whisper base.en CPU INT8 measured on the development and three generated held-out cases; a real local ASR plus injected-vision Agent composition completed in 3.222 seconds with both observations in one view; fresh Chrome also routed the speech fixture through faster-whisper/cpu-int8 before accepting a PNG in the same session, and the WebSocket route retains the latest transcript revision alongside the frame; the mock final exposed both prior modalities; the opt-in WebSocket demo route completed a checked-in WAV with the cached model and emitted a local-backend acknowledgment; an isolated Chrome run without a fake audio-device flag used the present Microphone Array and completed getUserMedia, AudioWorklet capture, WAV upload and the mock final; no human speech accuracy, live vision quality or endpoint-quality claim.
Configured vision failure is covered at the WebSocket boundary: backend_failure is emitted and a later text request completes in the same session.
The loopback OllamaVisionProvider regression exercises the real local HTTP request with local ASR in one Agent context; it verifies protocol payloads and provenance, not live model quality.
In-flight frame coverage also proves a delayed stale frame result cannot enter the current reasoner view after a newer frame arrives.
The image boundary now rejects structurally incomplete or CRC-invalid PNG uploads before vision inference and removes rejected materializations.
Known failures: Default 3.11 uv target link is broken on this machine; human speech accuracy and endpoint quality, live vision quality, image-only controller integration, hosted backend, completed user feedback session and demo recording are not implemented. Functional browser, physical-device and injected multimodal smoke are recorded, but image-only response, changed-frame replacement and conflicting-frame resolution await engine integration; pixel inspection, live ASR/vision quality and non-mock reasoning remain unverified.
Dependency or contract proposals: Local experiment uses optional webrtcvad-wheels 2.0.14; propose adding it to the shared audio extra after review. Browser smoke also required local-only websockets 17.1 for Uvicorn WebSocket support; propose adding a WebSocket runtime through the shared dependency owner. No lockfile or contract change was made.
Next independent task: Review the injected multimodal evidence, conduct the voluntary feedback session, then coordinate the engine integration slice for the four strict controller gaps.
AI tools/prompts/outputs and human modifications: Record each milestone in AI_USE_LOG.md.

The demo now removes invalid WAV materializations after post-header validation and reports injected ASR separately from Faster Whisper in its backend label; focused tests cover both behaviors.
The combined configured-backend WebSocket regression calls DemoPerception.from_environment with both modality settings, substitutes only the ASR implementation for deterministic text, and preserves source IDs and an informational final; the protocol service remains test-only evidence.
The WebSocket recovery regression also proves an ASR backend_failure does not end the session: a later PNG and spoken request complete with retained image context.
A fresh served WebSocket run combined the cached Faster Whisper base.en CPU INT8 backend with the configured OllamaVisionProvider over a loopback protocol service in 1.326 seconds; the final retained both recognized speech and image evidence. This remains mixed evidence with mock reasoning and no live vision-quality claim.
PNG validation now also checks the concatenated IDAT zlib stream for a complete, non-trailing decode; CRC-valid compressed corruption is rejected before vision inference.

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