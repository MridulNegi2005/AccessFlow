# Multimodal end-to-end evidence

Date and branch: 2026-09-14 / atishay/perception

Status: MIXED EVIDENCE

This run exercised the session-scoped WAV and PNG path through event translation, DemoPerception
and one Agent context. Audio used the already-installed local Faster Whisper base.en CPU INT8
snapshot. Vision used an explicitly injected provider because no Ollama service is available on
this machine.

## Run

- Audio fixture: tests/fixtures/audio/synthetic_speech.wav
- Image input: validated PNG materialized through the same session media root
- Audio source ID: live-audio-1
- Image source ID: injected-frame-1
- Elapsed time: 3.222 seconds
- Local audio backend: faster-whisper/cpu-int8
- Vision backend: local/injected-vision
- Final basis: informational

Faster Whisper returned:

> My screen keeps flickering after the update. Book Wednesday at 5.

The injected vision provider returned:

> screen shows the approval prompt

The Agent reasoner received both observations in one view and emitted:

> Local speech and screen evidence are available together.

## Browser mixed run

A fresh Chrome CDP run started the demo with the cached local Faster Whisper snapshot enabled.
The browser uploaded tests/fixtures/audio/synthetic_speech.wav and then a validated PNG in the
same WebSocket session.

- Backend label: local/Faster Whisper CPU INT8 audio + demo/mock text/image
- Audio media status: media_received=audio
- Audio acknowledgment backend: faster-whisper/cpu-int8
- Audio final: Mock agent received audio input: My screen keeps flickering after the update. Book Wednesday at 5.
- Image media status: media_received=frame
- Image and follow-up text finals: observed
- Browser layout: scroll width 741, viewport width 756
- Browser event stream: no Runtime exceptions, console errors, deprecation warnings or page errors

The image remains demo/mock in this browser run because Ollama is unavailable.

## Fresh local-ASR and loopback-vision route

A separate served WebSocket run enabled the cached Faster Whisper base.en CPU INT8 snapshot and a configured OllamaVisionProvider pointed at a loopback protocol service. It completed in 1.326 seconds.

- Backend label: local/Faster Whisper CPU INT8 audio + local/Ollama gemma3:4b image
- Audio acknowledgment backend: faster-whisper/cpu-int8
- Recognized fixture speech: My screen keeps flickering after the update. Book Wednesday at 5.
- Vision response: screen shows the approval prompt
- Follow-up final retained both audio and image context
- Protocol request checked model, default safety prompt, PNG bytes and stream=false

This is mixed runtime evidence: local audio inference and the HTTP provider path are real, while the vision service is a deterministic loopback stub and the reasoner remains the demo mock. It does not establish live vision quality or non-mock reasoning. The visible
mock final after the follow-up text included both prior audio and image context. This proves browser
transport into the local audio backend plus continued multimodal session handling; it does not prove
live vision quality or non-mock reasoning.

## What this proves

- A real local ASR result can enter the same multimodal session context as image evidence.
- WAV validation/materialization, source identity, backend labels and observation provenance survive
  the composition path.
- The final response remains informational; no state-changing tool was proposed or authorized.

The deterministic regression coverage remains in
tests/demo/test_app.py::test_multimodal_audio_and_image_reach_one_agent_context and
tests/demo/test_app.py::test_multimodal_audio_revision_replaces_old_speech_and_keeps_frame. The
image-only response and changed-frame controller limitations remain captured by strict expected
failures in
tests/demo/test_app.py::test_image_only_informational_response_needs_additive_controller_support and
tests/demo/test_app.py::test_new_frame_replaces_previous_frame_in_reasoner_context.

## Automated WebSocket regression

tests/demo/test_app.py::test_websocket_combined_media_context_is_visible now sends a validated
base64 WAV, a validated base64 PNG and a follow-up transcript through one TestClient WebSocket.
It asserts both media status source IDs and verifies that the final response contains audio and
image context. This protects the browser-observed behavior at the demo route level.
The companion tests/demo/test_app.py::test_websocket_multimodal_revision_keeps_latest_text_and_frame
sends two transcript revisions for one utterance between a WAV and PNG and verifies that the
latest speech hypothesis and image context survive the browser transport.
The image boundary regression, tests/demo/test_app.py::test_websocket_reports_recoverable_image_input_error,
returns a labeled demo/input error for malformed PNG data and confirms the WebSocket session remains
usable for a later text request. The structural input companion,
tests/demo/test_app.py::test_websocket_reports_recoverable_structural_input_error, covers a non-object
frame payload and verifies the same recovery path.
The image upload boundary now validates complete PNG chunk structure, CRCs, legal IHDR metadata, IDAT
and terminal IEND before materializing a frame; focused tests cover truncated and CRC-invalid payloads.
The loopback companion, tests/demo/test_app.py::test_multimodal_context_uses_loopback_ollama_transport,
exercises the actual OllamaVisionProvider HTTP request with local ASR in one Agent context. It verifies
the model, prompt, base64 image and informational result against a local protocol stub; it is not live
vision quality evidence.
The configured environment companion, tests/demo/test_app.py::test_websocket_environment_vision_provider_reaches_multimodal_context,
exercises the same provider through DemoPerception.from_environment and the WebSocket route. It waits
for the image observation, then sends the spoken question and verifies both pieces of context in the final;
the loopback service remains a protocol stub rather than live vision quality evidence.
The in-flight companion, tests/demo/test_app.py::test_inflight_old_frame_cannot_enter_multimodal_context,
delays frame 1, delivers frame 2, and verifies that the stale result never reaches a frame-bearing
reasoner view.
The safety companion test, tests/demo/test_app.py::test_partial_speech_and_final_image_never_authorize_a_write,
keeps correction_pending true and confirms that image evidence cannot authorize a write while speech
is unfinished.
The image-only safety companion, tests/demo/test_app.py::test_image_evidence_never_authorizes_a_write_without_spoken_request,
confirms that vision text resembling a write request cannot create an executor call or effect without
a spoken request.
The image-first companion test, tests/demo/test_app.py::test_websocket_image_before_audio_context_is_visible,
sends the PNG before the WAV and verifies that the later audio final still includes image context.
The session-reset companion, tests/demo/test_app.py::test_websocket_session_reset_does_not_inherit_multimodal_context,
completes multimodal input in one connection and verifies a second connection has no inherited audio or image context.
The changed-frame route reproducer, tests/demo/test_app.py::test_websocket_new_frame_replaces_previous_frame,
is a strict expected failure on this branch: two frames arrive through the WebSocket, and the final
currently retains both until the integrated controller removes the prior active frame.
The configured vision failure companion, tests/demo/test_app.py::test_configured_vision_failure_emits_backend_error_without_final,
confirms that a vision backend exception becomes a backend_failure event without a misleading final.
The provider shape companion, tests/perception/test_vision.py::test_ollama_provider_rejects_non_object_json_response,
confirms that list and null JSON roots become a classified invalid JSON shape error. The timeout companion,
tests/perception/test_vision.py::test_ollama_provider_normalizes_timeout, confirms provider timeouts use
the same stable RuntimeError boundary. The route companion,
tests/demo/test_app.py::test_websocket_malformed_vision_json_is_recoverable, exercises a list response
through the configured provider and verifies backend_failure followed by a usable transcript request.
The configured timeout companion, tests/demo/test_app.py::test_websocket_vision_timeout_is_recoverable,
exercises the provider timeout through the same WebSocket route and verifies transcript recovery.
The route-level companion, tests/demo/test_app.py::test_websocket_configured_vision_failure_is_recoverable,
confirms the same failure behavior through WebSocket transport and verifies that the session remains
usable for a later text request.

## Limits

This is not a live multimodal model benchmark: the vision result was injected, Ollama was not
running, and the reasoner was a test double. The audio fixture is generated speech rather than
participant audio. Live vision quality, non-mock reasoning and pixel
inspection remains unverified.


## Boundary follow-up

The demo now removes a WAV materialization when post-header PCM validation fails. LocalPerception also exposes its configured audio backend identity, so injected ASR is labeled as local/injected-asr while the installed Faster Whisper path keeps its Faster Whisper label; an injected backend without an identity is labeled local/unknown-audio. Encoded media uploads are rejected before base64 decoding when they exceed the 8 MiB raw-media budget. PNG validation also rejects CRC-valid but corrupt IDAT zlib streams before vision inference.

Automated coverage: tests/demo/test_app.py::test_websocket_configured_audio_and_vision_share_context calls DemoPerception.from_environment with both modality settings, substitutes only the ASR implementation for deterministic text, and verifies both configured backends through one WebSocket session. The focused boundary tests also cover truthful labeling and failed WAV cleanup. The companion test tests/demo/test_app.py::test_websocket_audio_backend_failure_keeps_multimodal_session_usable verifies that a backend_failure from ASR is recoverable before a later PNG and spoken request. The full suite is 117 passed with 3 strict expected failures; demo and perception coverage is 51 passed plus 3 strict xfailed and 50 passed. The turn-policy companion, tests/perception/test_turn_policy.py::test_image_captions_cannot_drive_speech_turn_policy, confirms that correction and backchannel words in image captions are treated as context rather than speech cues; existing text cue coverage remains unchanged.


## 2026-09-15 - Codex Atishay timestamp provenance

**Task:** Preserve source timing when browser multimodal events enter the demo.

**Changes:** The owned event adapter now carries a supplied capture timestamp into transcript, audio
and frame envelopes, forwards audio speech bounds, and maps frame event timing into image observation
bounds. The browser stamps outgoing events from its capture clock while allowing an explicit source
timestamp to survive.

**Status:** Full suite 117 passed, 3 strict expected failures; demo suite 51 passed, 3 strict expected
failures; perception suite 50 passed; Ruff, compilation and git diff --check clean. No engine, contract,
dependency or lockfile change.



## 2026-09-15 - Codex Atishay quota and conflicting-frame coverage

**Task:** Exercise vision quota exhaustion and contradictory visual evidence in the multimodal path.

**Changes:** Added provider and WebSocket regressions showing quota errors become recoverable backend_failure
events and the session remains usable. Added a strict conflicting-frame reproducer and an additive
contract proposal because the protected controller has no structured visual conflict state.

**Status:** Full suite 119 passed, 4 strict expected failures; demo suite 51 passed, 4 strict expected
failures; perception suite 52 passed; Ruff, compilation and git diff --check clean. No engine, contract,
dependency or lockfile change. Live vision quality remains unverified.



## 2026-09-15 - Codex Atishay envelope timestamp alignment

**Task:** Align browser timing with the v0.1 event envelope.

**Changes:** The browser now emits its capture timestamp beside kind and payload, while the adapter
accepts both envelope timestamps and the prior payload form. The existing frame observation and audio
speech-bound regressions cover the preserved timing.

**Status:** Full suite 119 passed, 4 strict expected failures; no engine, contract, dependency or
lockfile change.



## 2026-09-15 - Codex Atishay in-flight cross-modal retention

**Task:** Verify that frame arrival does not discard an already-running audio observation.

**Changes:** Added a passing regression that holds audio perception in flight, delivers a frame, then
releases audio and verifies both observations reach the same reasoner context. This confirms current
source acceptance preserves independent cross-modal results.

**Status:** Full suite 120 passed, 4 strict expected failures; demo suite 52 passed, 4 strict expected
failures; perception suite 52 passed; Ruff, compilation and git diff --check clean.



## 2026-09-15 - Codex Atishay invalid PNG cleanup

**Task:** Verify rejected PNG uploads do not remain in the session directory.

**Changes:** Added direct materialization cleanup coverage for structurally invalid PNG bytes, complementing
the existing WebSocket recovery path.

**Status:** Full suite 121 passed, 4 strict expected failures; demo suite 53 passed, 4 strict expected
failures; perception suite 52 passed; Ruff, compilation and git diff --check clean.



## 2026-09-15 - Codex Atishay truthful vision labeling

**Task:** Keep injected vision backend labels truthful when model metadata is absent.

**Changes:** Added a local/unknown-vision fallback for identity-free vision adapters, matching the
existing unknown-audio behavior and preventing configuration-time crashes.

**Status:** Full suite 122 passed, 4 strict expected failures; demo suite 54 passed, 4 strict expected
failures; perception suite 52 passed; Ruff, compilation and git diff --check clean.


## 2026-09-15 - Codex Atishay HTTP quota error normalization

**Task:** Preserve provider quota details when the configured vision service rejects an HTTP request.

**Changes:** OllamaVisionProvider now reads a structured JSON error body from HTTP failures such as
429 and raises the same classified runtime error used by the WebSocket backend_failure recovery path.
The regression verifies the quota detail survives the provider boundary.

**Status:** Full suite 123 passed, 4 strict expected failures; demo suite 54 passed, 4 strict expected
failures; perception suite 53 passed; Ruff, compilation and git diff --check clean. No engine, contract,
dependency or lockfile change.


## 2026-09-15 - Codex Atishay HTTP quota WebSocket recovery

**Task:** Exercise structured HTTP quota failures through the configured multimodal WebSocket path.

**Changes:** Added a route regression using an HTTP 429 JSON error from OllamaVisionProvider. The route
emits backend_failure without a misleading final and the same session accepts a later transcript.

**Status:** Full suite 124 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 53 passed. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay perception worker responsiveness

**Task:** Verify that slow image inference does not block the multimodal event loop.

**Changes:** Added a regression with a deliberately slow injected vision provider. The provider runs in
a worker while an async heartbeat completes, and the final image observation retains its source identity.

**Status:** Full suite 125 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 54 passed. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay audio worker responsiveness

**Task:** Verify that slow raw audio transcription does not block the multimodal event loop.

**Changes:** Added a regression with a deliberately slow injected ASR provider. The worker-backed audio
path allows an async heartbeat to complete and preserves the final utterance identity and text.

**Status:** Full suite 126 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 55 passed. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay safe multimodal output rendering

**Task:** Keep untrusted vision and transcript output as display text in the browser demo.

**Changes:** Replaced the event card's innerHTML construction with textContent-backed DOM nodes and
extended the existing UI regression to require the safe rendering path.

**Status:** Full suite 126 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 55 passed. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay nonblocking browser media intake

**Task:** Keep base64 decoding and WAV/PNG validation from blocking the WebSocket receive loop.

**Changes:** The route now offloads synchronous event translation and session-scoped media validation to
a worker while retaining the existing adapter API. Existing raw media, combined context and recovery
regressions pass through the updated boundary.

**Status:** Full suite 126 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 55 passed. No engine, contract, dependency or lockfile change.


## 2026-09-15 - Codex Atishay malformed provider output guards

**Task:** Prevent blank or non-string ASR and vision responses from becoming empty multimodal observations.

**Changes:** LocalPerception now normalizes provider text and raises a classified runtime failure for
empty or non-string audio and image output. Focused regressions cover both modalities.

**Status:** Full suite 128 passed, 4 strict expected failures; demo suite 55 passed, 4 strict expected
failures; perception suite 57 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay bounded multimodal context

**Task:** Keep the mock demo's prior multimodal context bounded as sessions accumulate observations.

**Changes:** DemoReasoner now caps the prior context suffix at 16,384 characters, walks backward from
the newest observation, and truncates the item that reaches the remaining capacity so the newest
evidence is retained. The regression covers recent evidence, oldest-history omission, the exact
capacity for an oversized item, and request completeness.

**Status:** Full suite 129 passed, 4 strict expected failures; demo suite 56 passed, 4 strict expected
failures; perception suite 57 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay invalid vision JSON recovery

**Task:** Cover syntactically invalid vision-provider JSON at both the provider and browser-session
boundaries.

**Changes:** Added raw invalid-byte coverage for OllamaVisionProvider and parameterized the WebSocket
malformed-response recovery regression over both a valid non-object JSON root and invalid JSON bytes.
Both paths classify the failure without a misleading final and accept a later transcript in the same
session.

**Status:** Full suite 131 passed, 4 strict expected failures; demo suite 57 passed, 4 strict expected
failures; perception suite 58 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay truthful vision provenance

**Task:** Prevent injected vision backends from being presented as Ollama without an explicit identity.

**Changes:** DemoPerception now requires an ollama/ backend identity as well as a model name before
using the Ollama label. A model-only injected provider is classified as local/unknown-vision, with a
regression covering the overclaim boundary.

**Status:** Full suite 132 passed, 4 strict expected failures; demo suite 58 passed, 4 strict expected
failures; perception suite 58 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay bounded local perception deadlines

**Task:** Bound local audio and image provider wait time while preserving the replaceable provider seam.

**Changes:** LocalPerception now accepts an opt-in finite timeout for provider results and reports
modality-specific timeout failures. Direct tests cover invalid configuration, audio and image deadline
classification, and eventual completion of already-started worker calls; a WebSocket regression covers
audio timeout recovery and source identity. The deadline bounds caller latency, while Python cannot
forcibly stop an arbitrary synchronous function already running in a worker thread.

**Status:** Full suite 141 passed, 4 strict expected failures; demo suite 59 passed, 4 strict expected
failures; perception suite 66 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay cancellation cleanup guard

**Task:** Ensure cancellation of a bounded local perception observer releases its async task cleanly.

**Changes:** Moved the initial scheduling yield inside LocalPerception's timeout cleanup guard and added a
regression that cancels an already-running audio observation, verifies prompt observer cancellation,
and waits for the synchronous worker to finish. This records the non-force-cancellable worker limit
honestly.

**Status:** Full suite 142 passed, 4 strict expected failures; demo suite 59 passed, 4 strict expected
failures; perception suite 67 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay multimodal recovery after vision failure

**Task:** Verify that a vision backend failure can recover into a later image plus audio session.

**Changes:** Added a WebSocket regression that sends a failing frame, then a valid frame and WAV
through the same session. The final informational response preserves the recovered image evidence,
audio transcript, source IDs and backend labels.

**Status:** Full suite 143 passed, 4 strict expected failures; demo suite 60 passed, 4 strict expected
failures; perception suite 67 passed. No engine, contract, dependency or lockfile change.

## 2026-09-15 - Codex Atishay bounded multimodal admission

**Task:** Bound replaceable local perception work while preserving paired audio and image processing.

**Changes:** LocalPerception now uses independent latest-only workers for audio and image. Each worker
runs one provider call and keeps one pending item per modality, drops obsolete same-session frames
and same-utterance audio revisions, suppresses stale successes and failures, and preserves direct
observation fields. DemoPerception retains the vision worker for the session and closes queued work
during WebSocket shutdown. Tests cover rapid frames, revised audio, cross-modal concurrency,
session isolation, demo reuse and active-worker shutdown cleanup.

**Status:** Full suite 149 passed, 4 strict expected failures; demo suite 61 passed, 4 strict expected
failures; perception suite 72 passed. No engine, contract, dependency or lockfile change.
