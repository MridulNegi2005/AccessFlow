# Samsung runtime media integration: next A work — 23 September 2026

The base package installs and passes Samsung startup plus one text case. This is
not multimedia readiness. Keep these requirements separate from the six-case text
screen and from Atishay's browser/media benchmark evidence.

## Verified current path

- scripts/submission_entry.py constructs Samsung ParticipantAgent; the current
  profile freezes text-model settings only. samsung.py `_build_agent` constructs
  LocalPerception() without ASR weights or a vision provider.
- samsung_protocol.py accepts bounded/rooted PNG FrameEvents. Actual observation
  fails without an explicitly configured vision provider. Path acceptance tests
  are not image inference evidence.
- perception_worker.py now accepts Ollama vision flags. Older cli.py/contract notes
  saying the child rejects them are historical/stale, not a current blocker.
- ProcessPerception still checks that model_path exists before any native event;
  its worker CLI requires --model-path even for vision-only work. Do not create a
  dummy directory or misleading model path to get past this requirement.
- Official user_audio_chunk remains an explicit unsupported-media path: the kit
  supplies MP3 segments while internal perception takes PCM WAV. Decoding/turn
  assembly ownership was left undecided in SAMSUNG_ADAPTER.md.

## Independent A work

1. Add validated, explicit perception configuration at the Samsung runtime factory,
   using the agreed existing worker interfaces and recording actual requested and
   observed backend identity. Keep the default text profile truthful; do not call
   a configured provider a successful perception run before observing its result.
2. Mirror the chosen configuration in the submission profile and dependencies.
   Reject contradictory environment settings. In particular, the newer optional
   read-answer mode is not yet frozen by submission_entry.PROFILE_KEYS; include it
   when finalizing the reproducible profile so inherited environment cannot silently
   change package behavior.
3. Exercise PNG through the official entry point with deterministic provider evidence
   first, then a real explicitly installed model. Preserve frame IDs and stale-result
   cancellation. Record model load, failure and scenario timing separately.
4. Re-run clean-package validation after media dependencies/configuration change.
   Existing cached-wheel installation does not cover optional ASR/vision or Docker.

## Coordination required

A pending user question asks whether Mridul owns the MP3-to-WAV/turn-assembly bridge
in the Samsung adapter, with Atishay retaining transcription and speech timing.
No answer has been received and no decoder implementation has started. Until the
ownership decision arrives, continue the independent runtime/profile work above.
If Atishay owns the bridge, give him the exact official chunk interface and bounded
lifecycle requirements; do not replace his recordings with handwritten transcripts.

The vision-only model-path restriction spans the A parent and B worker contract.
A may configure a genuinely installed ASR model using the existing interface; a
vision-only/no-ASR option requires an additive agreement and B-owned worker change.
Do not edit the worker or perception source unilaterally. Whole-file arrival still
must not be presented as a calibrated speech endpoint. Frame conflict policy and
stop-speaking/stop-task semantics also need coordinated validation.

No global model-installation absence is claimed: standard local model/cache and
Ollama executable locations were checked without finding an immediately usable
configured backend. No downloads, dummy model files or provider fallback occurred.

[Fresh base-package evidence](evidence/samsung-clean-install-2026-09-23/README.md)
