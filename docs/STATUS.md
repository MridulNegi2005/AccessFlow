# Implementation status

Updated 13 September 2026. This file records implementation, not aspirational completion.

## Bootstrap

- Typed v0.1 input events, snapshots, observations, tool manifests/calls and proposals added.
- Protocols, injectable clocks, fake perception/reasoner/tools and baseline policy added.
- Initial engine and controlled safety tests are implemented. The engine baseline covers
  contracts, partial-write blocking, dynamic names, corrections, cancellation, stale reads,
  duplicates, intentional repeat writes and authorization.
- Atishay's owned Workstream B now includes transcript/audio/frame perception seams,
  deterministic turn policy, a labeled fake-agent browser demo, fixture provenance,
  dependency-free PCM loading, local Faster Whisper configuration and optional Ollama
  vision provider tests.
- Git has main, mridul/engine and atishay/perception; the public branch is published.

## Workstream B — Atishay

Updated 14 September 2026.

- Multimodal end to end evidence now covers one session carrying a validated WAV and PNG through
  event_from_message, injected local ASR and vision providers, DemoPerception, and one Agent
  context. Source IDs and backend labels are preserved; the final response is informational.
- The multimodal regression also covers both arrival orders, a revised audio hypothesis and
  WebSocket paths: the latest transcript revision replaces the prior one while the frame remains
  in the same context, and the combined WAV, PNG and text response exposes both retained
  modalities. A browser transport regression verifies that the revised hypothesis survives the
  session route.
- Partial speech followed by a final image is covered by a write-safety regression:
  correction_pending stays true and no write tool is invoked.
- Image-only vision text that resembles a write request is also blocked: no write call or effect
  is allowed without a spoken request.
- The turn policy now treats image observations as context-only for speech cues, so captions containing
  correction or backchannel words cannot pause, complete or stop a spoken turn; a direct regression
  covers this boundary while existing text behavior remains covered.
- The WebSocket ordering regression also covers PNG arriving before WAV; the later audio final
  retains image context in the same session.
- The WebSocket image boundary also recovers from malformed PNG input with a labeled error and
  keeps the session available for a subsequent text request.
- The WebSocket input boundary also recovers from a non-object multimodal payload with a labeled
  demo/input error and keeps the session available for a subsequent transcript.
- PNG ingestion now validates chunk boundaries, CRCs, legal IHDR values, IDAT presence, zlib stream
  integrity and terminal IEND structure before a frame reaches a vision backend; rejected uploads are
  removed from the session directory.
- Failed WAV uploads now remove their post-header validation materialization, and local injected
  audio backends identify themselves separately from the installed Faster Whisper path in the demo label.
- A configured vision-backend failure is also covered: it emits backend_failure without a
  misleading final response.
- The configured vision failure is also covered through the WebSocket route: backend_failure is
  emitted and the same session completes a later text request.
- An audio backend failure is also covered through the WebSocket route: backend_failure is emitted,
  then a later PNG and spoken request complete in the same multimodal session with image context retained.
- A protocol-level loopback regression now runs the actual OllamaVisionProvider HTTP path with local
  ASR in one Agent context; it verifies model, prompt, image bytes and informational output without
  claiming live model quality.
- The configured vision environment is covered at the WebSocket boundary: a loopback provider receives
  the PNG and the later response retains the returned image evidence beside the spoken question.
- The combined configured-backend WebSocket regression now calls DemoPerception.from_environment with both
  modalities configured, then checks WAV and PNG transport, backend labels, source IDs and informational output.
- In-flight frame race coverage verifies that a delayed frame 1 result cannot enter the multimodal
  context after frame 2 arrives; only the current frame is presented to the reasoner.
- The changed-frame WebSocket reproducer is a strict expected failure until the controller
  removes the prior frame from the active context.
- A fresh local WebSocket run used the installed Faster Whisper base.en CPU INT8 snapshot and the
  configured OllamaVisionProvider against a loopback protocol service; in 1.326 seconds it retained the
  recognized speech and returned image evidence in the same session. Vision quality and reasoning remain unverified.
- A second composition run used the installed Faster Whisper base.en CPU INT8 snapshot for real
  audio inference and an injected vision provider; the paired context completed in 3.222 seconds.
  A fresh Chrome run also routed the speech fixture through that local backend before accepting a
  PNG in the same session. The result is mixed evidence, not a live multimodal model benchmark.
- The real Chrome smoke now passes text, checked in WAV, PNG plus paired transcript, and
  microphone capture through the served AudioWorklet. A separate isolated Chrome run used the
  present Microphone Array without a fake audio-device flag and completed the real getUserMedia,
  WAV upload and mock final path. The fresh CDP run also shows the mock final carrying prior
  audio and image context, with no console or page errors or horizontal overflow.
- Final verification is 107 tests passed with 3 strict expected failures, including 44 passing demo
  tests and 47 passing perception tests; Ruff, compilation and git diff --check are clean. The browser runtime
  still uses local only websockets 17.1.
- The three expected failures record current controller integration gaps: image-only informational
  response and direct or WebSocket replacement of a prior active frame. Proposals and corresponding integrated-branch
  behavior are available for the engine owner; no engine or contract file was changed here.
- Evidence is mixed and still bounded: live vision quality and non mock reasoning are still
  open. Pixel inspection is also unverified because the local image helper could not open the
  captures.
- origin/mridul/engine was fetched at ad04bca for integrated state review. No engine owned
  files were changed and this branch remains atishay/perception.

## Still required

- Broader engine race tests and validation of the normalized status reconciliation route.
- Live reasoning adapters, official-kit adapter after the kit is supplied, replay and metrics.
- Held-out generated-case ASR and endpoint measurements are recorded; human speech and endpoint quality, live vision service and real multimodal
  benchmark on declared hardware.
- Manual browser/device smoke proof, a completed voluntary feedback session, demo video and final presentation assembly.
- Docker/CI verification, the 60-scenario authored/provenance-tracked set, reviewed disclosure
  and final release assembly.

No live model, official compatibility, latency or completion target is currently certified.

## Checkpoint 17 - 13 September 2026: feedback and recording safeguards

Prepared the owned feedback and presentation artifacts for later human-led validation.

- docs/feedback/SESSION_TEMPLATE.md requires voluntary participation, separate capture
  consent and anonymized notes by default.
- docs/presentation/DEMO_RECORDING_SCRIPT.md provides a 4m40s evidence-labeled sequence
  for the current mock/local boundaries.
- No participant feedback or recording was collected in this checkpoint.
- Manual browser/device smoke, engine integration and final presentation recording remain.
## Checkpoint 18 - 13 September 2026: held-out generated speech and endpoint check

Measured three newly generated voice cases after fixing the local evaluation configuration.

- Faster Whisper preserved the fluent request, repeated phrase, correction and two-part
  request through LocalPerception.observe.
- WebRTC produced no internal candidate for the fluent or repetition case.
- On the labeled 1.2 second break, the candidate overlapped the full break but included
  0.669 seconds of early acoustic margin.
- The results are held-out generated-fixture evidence only; human speech accuracy and
  endpoint quality remain unverified.
## Checkpoint 19 - 13 September 2026: opt-in local audio demo path

Added an environment-gated local audio mode to the owned browser demo.

- The default remains demo/mock.
- Setting ACCESSFLOW_DEMO_WHISPER_MODEL to an existing model path routes WAV input through
  LocalPerception and displays the local backend label.
- Text and image inputs remain demo/mock.
- A real checked-in WAV completed the WebSocket route with the cached Faster Whisper model;
  the controller emitted its informational final output.
- Browser permission/device capture and live vision remain unverified.
## Checkpoint 20 - 13 September 2026: presentation content outline

Added docs/presentation/SLIDE_OUTLINE.md as a template-neutral content draft.

- Covers the problem, failure mode, architecture, correction/timing, action safety,
  multimodal boundary, evidence and limitations.
- Ties numbers to the current generated fixtures, local model configuration and test suite.
- Marks the official template, recording, feedback, integration and release work as
  outstanding.
## Checkpoint 21 - 13 September 2026: session path isolation

Hardened the browser media boundary against client-supplied filesystem paths.

- Session WebSocket traffic now roots no-byte fallbacks in the session temporary directory.
- Existing base64 WAV/PNG validation and cleanup remain unchanged.
- The boundary has a focused regression test; no shared contract or dependency changed.
## Checkpoint 22 - 13 September 2026: local model configuration guard

Added explicit validation for the optional local model path.

- Invalid configuration is reported as demo/config before an agent starts.
- The default mock mode and valid local configuration remain unchanged.
- Demo tests cover both the error event and the valid opt-in label.
## Checkpoint 23 - 13 September 2026: opt-in local Ollama vision path

Added an optional Ollama PNG provider and environment-gated demo routing.

- The provider accepts only loopback HTTP(S) endpoints.
- PNG bytes are sent to an already-running service; no model download occurs.
- LocalPerception preserves frame identity and reports the provider backend name.
- Mocked provider and demo tests cover successful responses and configuration/service errors.
- No Ollama executable or loopback service was available on this machine; live model
  availability and vision quality remain unverified.
## Checkpoint 24 - 13 September 2026: WebSocket media protocol smoke

Verified the browser demo's validated media path end to end for base64 WAV and PNG payloads.

- The WebSocket reports the received media kind and preserved source ID after materialization.
- WAV transport reaches the mock controller and emits its expected informational final.
- PNG transport is validated and session-scoped; the current v0.1 agent requires a paired
  transcript before producing a controller final, so image-only planning remains an engine
  integration item.
- Demo tests: 18 passed; full suite: 77 passed; Ruff and git diff --check are clean.

## Checkpoint 25 - 13 September 2026: functional Chrome browser smoke

Ran the local demo through a temporary isolated Chrome session using the actual page controls.

- Text produced the visible mock acknowledgment and informational final output.
- The checked-in WAV file control produced a media-received audio status and mock final.
- The PNG file control produced a media-received frame status; the current v0.1 agent then
  produced a final after a paired transcript.
- The rendered document had no horizontal overflow in the captured viewport.
- The smoke required local-only websockets 17.1 because the committed Uvicorn dependency
  does not currently include a WebSocket runtime. This is recorded as a dependency proposal.
- Physical microphone/device capture, pixel inspection and separate console capture remain
  unverified.
## Checkpoint 26 - 13 September 2026: synthetic microphone browser smoke

Exercised the microphone controls in isolated Chrome with Chrome's synthetic audio device.

- Start entered the recording state and enabled the stop control.
- Stop closed the capture path, encoded the samples as WAV and uploaded them through the
  session WebSocket.
- The browser observed media_received=audio and the mock controller final.
- No person or physical microphone was recorded. Physical device permission, pixel inspection
  and separate console capture remain unverified.