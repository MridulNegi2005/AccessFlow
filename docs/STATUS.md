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
