# Human microphone smoke test — 25 September 2026

## Result

A user-provided browser screenshot shows the perception backend as
`local/Faster Whisper CPU INT8 audio` and the reasoner as
`demo/mock-reasoner`. The displayed audio input is:

> Set a reminder for Tuesday at 3, actually Wednesday at 5, tell me only the final time.

The mock response repeats the recognized input. This supports one successful
human microphone capture/upload and local ASR display, including the
Tuesday-to-Wednesday correction. It is one manual smoke check, not a word-error
measurement or a reasoning-quality test.

This later run supersedes the earlier same-day checkpoint that said no human
recording had yet been captured; that earlier statement was accurate at its
time and remains true of its generated-only test results.

## Limits

- The mock reasoner echoed the input; it did not answer only “Wednesday at 5”
  or create a reminder.
- No live partial transcript, speech-triggered interruption, endpoint timing,
  device/browser identity, recording duration, raw WAV, or inference latency was
  captured in the screenshot.
- No audio was copied into the repository and no real reminder or external
  effect was created.
- Uvicorn output confirms page/WebSocket connections only; it does not log
  audio payloads or transcripts. The screenshot is the evidence for the
  displayed result.

## Next

No additional user speech is needed for this smoke-test result. Continue with
owned timing/uncertainty and recovery work; request another physical-mic run only
when a changed behavior needs human-device validation. Live streaming and
barge-in remain unimplemented and require coordination on C24-1/2/3 with
Mridul before shared controller integration.
