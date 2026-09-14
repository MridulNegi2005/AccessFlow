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
The changed-frame route reproducer, tests/demo/test_app.py::test_websocket_new_frame_replaces_previous_frame,
is a strict expected failure on this branch: two frames arrive through the WebSocket, and the final
currently retains both until the integrated controller removes the prior active frame.
The configured vision failure companion, tests/demo/test_app.py::test_configured_vision_failure_emits_backend_error_without_final,
confirms that a vision backend exception becomes a backend_failure event without a misleading final.
The route-level companion, tests/demo/test_app.py::test_websocket_configured_vision_failure_is_recoverable,
confirms the same failure behavior through WebSocket transport and verifies that the session remains
usable for a later text request.

## Limits

This is not a live multimodal model benchmark: the vision result was injected, Ollama was not
running, and the reasoner was a test double. The audio fixture is generated speech rather than
participant audio. Live vision quality, non-mock reasoning and pixel
inspection remains unverified.


## Boundary follow-up

The demo now removes a WAV materialization when post-header PCM validation fails. LocalPerception also exposes its configured audio backend identity, so injected ASR is labeled as local/injected-asr while the installed Faster Whisper path keeps its Faster Whisper label. PNG validation also rejects CRC-valid but corrupt IDAT zlib streams before vision inference.

Automated coverage: tests/demo/test_app.py::test_websocket_configured_audio_and_vision_share_context calls DemoPerception.from_environment with both modality settings, substitutes only the ASR implementation for deterministic text, and verifies both configured backends through one WebSocket session. The focused boundary tests also cover truthful labeling and failed WAV cleanup. The companion test tests/demo/test_app.py::test_websocket_audio_backend_failure_keeps_multimodal_session_usable verifies that a backend_failure from ASR is recoverable before a later PNG and spoken request. The full suite is 107 passed with 3 strict expected failures; demo and perception coverage is 44 passed plus 3 strict xfailed and 47 passed. The turn-policy companion, tests/perception/test_turn_policy.py::test_image_captions_cannot_drive_speech_turn_policy, confirms that correction and backchannel words in image captions are treated as context rather than speech cues; existing text cue coverage remains unchanged.