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
  dependency-free PCM loading and local Faster Whisper configuration tests.
- Git has main, mridul/engine and atishay/perception; the public branch is published.

## Still required

- Broader engine race tests and validation of the normalized status reconciliation route.
- Live reasoning adapters, official-kit adapter after the kit is supplied, replay and metrics.
- Held-out speech-quality ASR measurement, validated acoustic VAD endpoint quality, live vision backend and real multimodal
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