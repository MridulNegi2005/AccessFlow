# Live development fixtures

These are four variants of `../dev`, not four additional independent user examples.
They use the same mock effects and task criteria. Scripted proposals remain available
for an offline plumbing check; the live runner supplies ModelReasoner and never sends
those proposals, task criteria or environment internals to the model.

Differences from the original deterministic orchestration fixtures:

- Completion wait is 100 seconds, within the scenario budget. The original three-second
  waits for three cases were appropriate for scripted planners, not multi-step inference.
  Backend request and controller inference timeouts are unchanged.
- Tool manifests explicitly require 24-hour HH:MM where the oracle expects that format.
  Lookup vocabulary and receipt identity are described in the supplied schemas. A hidden
  exact string expectation without a corresponding tool requirement is not a fair model test.
- Device correction is a new utterance containing the request, not an ASR hypothesis that
  silently replaces the original command with a fragment. The rapid delivery is labelled
  correction-before-plan. It does not establish cancellation during a dispatched write.

The original pilot fixtures and failed traces are preserved separately for comparison.
Changing these fixtures does not retroactively convert those failures into passes.
No held-out, image, clinical or official-kit score is claimed here.

## Audio scenario

`audio_correction.json` (id `live-dev-audio-correction-01`) is the first real audio path:
a committed WAV fixture (`tests/fixtures/audio/synthetic_pause_correction.wav`, provenance in
`docs/feedback/PROVENANCE.md`), not a scripted transcript, drives one `audio` input event.
Run it with `--components local --asr-model-path <installed Faster Whisper base.en
directory>` and a live model backend so the path is: raw WAV -> actual Faster Whisper ASR ->
`HeuristicTurnPolicy` -> real model reasoning -> a confirmed mock `reserve_service_slot`
effect. See `docs/results/` for a dated run record.

It has no `proposals` or `reasoning_steps`: offline-fake mode has nothing to script the
perception step against on purpose, so `accessflow.cli replay ... --backend offline-fake`
fails loudly (`ValueError`) instead of silently substituting a transcript for ASR. Only a
real backend (`ollama`, `groq`, `gemini`, `nvidia`) exercises this file.

The fixture's spoken script ("Book Tuesday. [pause] Actually, Wednesday at five.") never
states AM or PM, so the oracle checks `day` and that a tool effect was confirmed, and does
not assert a specific `hour`. The committed hour is real model output, not a scripted
answer; it is reported, not scored, so this scenario cannot be made to pass by pinning a
lucky guess.
