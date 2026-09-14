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

## What this proves

- A real local ASR result can enter the same multimodal session context as image evidence.
- WAV validation/materialization, source identity, backend labels and observation provenance survive
  the composition path.
- The final response remains informational; no state-changing tool was proposed or authorized.

The deterministic regression coverage remains in
tests/demo/test_app.py::test_multimodal_audio_and_image_reach_one_agent_context and
tests/demo/test_app.py::test_multimodal_audio_revision_replaces_old_speech_and_keeps_frame. The
image-only controller limitation remains captured by the strict expected failure in
tests/demo/test_app.py::test_image_only_informational_response_needs_additive_controller_support.

## Limits

This is not a live multimodal model benchmark: the vision result was injected, Ollama was not
running, and the reasoner was a test double. The audio fixture is generated speech rather than
participant audio. Physical microphone capture, live vision quality, non-mock reasoning and pixel
inspection remain unverified.
