# Atishay workstream handoff

Date and branch: 2026-09-14 / atishay/perception
Completed: Perception foundation, deterministic turn-policy baseline, replaceable PNG vision seam, minimal fake-agent demo, opt-in local audio demo path, opt-in local Ollama vision path, session path isolation, local model configuration guard, synthetic audio provenance fixtures, PCM/activity baseline, local ASR seam, dependency-free PCM backend, optional VAD/timing candidates, session-scoped browser media upload, microphone WAV capture, held-out generated-case evaluation, feedback-session template, demo recording script, template-neutral presentation outline and multimodal end-to-end evidence implemented in owned paths; shared fakes/interfaces remain unchanged.
Contract version used: 0.1
Tests run and results: uv run --python 3.12 --extra dev pytest -q — 112 passed, 3 strict xfailed;
Configured vision environment wiring is covered through a loopback HTTP provider at the WebSocket route; the final retains image evidence with the later spoken question.
perception run — 50 passed; demo run — 46 passed, 3 strict xfailed; held-out fixture check included;
Ruff and git diff --check clean for owned paths.
Live-model/backend results: Local Faster Whisper base.en CPU INT8 measured on the development and three generated held-out cases; a real local ASR plus injected-vision Agent composition completed in 3.222 seconds with both observations in one view; fresh Chrome also routed the speech fixture through faster-whisper/cpu-int8 before accepting a PNG in the same session, and the WebSocket route retains the latest transcript revision alongside the frame; the mock final exposed both prior modalities; the opt-in WebSocket demo route completed a checked-in WAV with the cached model and emitted a local-backend acknowledgment; an isolated Chrome run without a fake audio-device flag used the present Microphone Array and completed getUserMedia, AudioWorklet capture, WAV upload and the mock final; no human speech accuracy, live vision quality or endpoint-quality claim.
Configured vision failure is covered at the WebSocket boundary: backend_failure is emitted and a later text request completes in the same session.
The loopback OllamaVisionProvider regression exercises the real local HTTP request with local ASR in one Agent context; it verifies protocol payloads and provenance, not live model quality.
In-flight frame coverage also proves a delayed stale frame result cannot enter the current reasoner view after a newer frame arrives.
The image boundary now rejects structurally incomplete or CRC-invalid PNG uploads before vision inference and removes rejected materializations.
Known failures: Default 3.11 uv target link is broken on this machine; human speech accuracy and endpoint quality, live vision quality, image-only controller integration, hosted backend, completed user feedback session and demo recording are not implemented. Functional browser, physical-device and injected multimodal smoke are recorded, but image-only response and changed-frame replacement await engine integration; pixel inspection, live ASR/vision quality and non-mock reasoning remain unverified.
Dependency or contract proposals: Local experiment uses optional webrtcvad-wheels 2.0.14; propose adding it to the shared audio extra after review. Browser smoke also required local-only websockets 17.1 for Uvicorn WebSocket support; propose adding a WebSocket runtime through the shared dependency owner. No lockfile or contract change was made.
Next independent task: Review the injected multimodal evidence, conduct the voluntary feedback session, then coordinate the engine integration slice.
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
