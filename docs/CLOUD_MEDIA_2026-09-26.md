# Hosted audio and vision trial — 26 September 2026

Owner: Mridul (Samsung adapter, runtime configuration, packaging). Atishay owns
browser microphone capture, perception policy, and his acceptance cases. No
Atishay-owned source or test was edited for this trial.

## Result so far

The Samsung kit permits hosted models. A new **opt-in** `cloud` media profile uses
Groq `whisper-large-v3-turbo` to transcribe complete WAV turns and Groq
`qwen/qwen3.8-27b` to describe PNG frames. The existing Groq Qwen reasoner is
unchanged. Cloud media does not load Faster Whisper weights or start Ollama.

On this machine, direct calls with the checked-in generated
`synthetic_speech.wav` and `device_panel.png` both succeeded:

| Path | Observed result | Elapsed |
| --- | --- | ---: |
| Audio | “My screen keeps flickering after the update. Book Wednesday at 5.” | 0.970 s |
| Image | Read `PANEL-B` and `ERR-42` from the PNG | 0.381 s |

These are two component calls, not an official scenario, human microphone run,
or evidence of task completion. The subsequent configured-agent setup warmed
both media routes but failed during reasoner warm-up with Groq HTTP **429** after
1.229 s. The reasoner shares Qwen's quota with cloud vision. Do not relabel the
combined setup as passing; a failed warm-up cannot become a transcript-only
fallback. No secrets or raw provider responses are recorded here.

After more than two minutes of independent test work, a second full configured
setup succeeded in **1.414 s** with both cloud media backends and the existing
Groq Qwen reasoner. This confirms the configured factory path can start; it
does not erase the first 429 or prove sustained evaluator throughput.

Controlled cloud provider/package tests: **8 passed**. The full repository run
reported **1,439 passed, 6 skipped, 7 failed**; those seven are the previously
identified B-owned demo/image and strict-xfail stop assertions based on older
D1/D4 behavior. This run did not edit or hide them. The test count is software
regression evidence, not a model-quality benchmark.

## Runtime contract

Set `ACCESSFLOW_SAMSUNG_PERCEPTION=cloud` with explicit audio and vision models,
`ACCESSFLOW_SAMSUNG_VISION_PROVIDER=groq`, validated installation WAV/PNG
fixtures, and a positive perception timeout. `SECRET_GROQ_API_KEY` is supplied
outside Git; the package entry maps it to the existing local client setting.
The cloud profile uses the same rooted Samsung MP3-to-WAV input bridge and
`Observation` source IDs, revisions and timestamps as the local path.

The HTTP calls are asynchronous, so a slow request does not freeze the queue.
Cancellation can stop awaiting the response; it cannot guarantee that the
provider stops processing or charging for a request already sent. Provider
errors, empty outputs and timeouts fail explicitly without invented content.
Image captions are evidence; they do not authorize state-changing actions.

Build a development package from a **clean committed source** with:

```powershell
uv run --offline --frozen python -m scripts.build_samsung_package `
  --kit ../participant-kit/participant-kit `
  --output artifacts/cloud-media-candidate `
  --team AccessFlow --model qwen/qwen3.8-27b --cloud-media `
  --warmup-audio tests/fixtures/audio/synthetic_speech.wav `
  --audio-provenance "Checked-in generated development speech fixture" `
  --warmup-image tests/fixtures/images/device_panel.png `
  --image-provenance "Checked-in generated development panel fixture"
```

The builder includes the two fixtures, hashes and provenance, not ASR/vision
weights. Its profile freezes both media models and the Groq provider. The kit's
`submission.yaml` declares only the **name** `SECRET_GROQ_API_KEY`; its value
must be registered on the event portal. Package assembly itself does not use
the key or call Groq.

## Remaining gates

1. Recheck provider quota, then run normal-speed public audio and visual
   scenarios from the generated package. Record every attempt, including 429s.
2. Compare cloud and local audio on the fixed development utterances; inspect
   corrections and uncertainty, not only raw transcript fluency.
3. Atishay must integrate this profile into his configured demo and perform the
   12 predeclared actual-inference attempts and four physical microphone checks.
   Mridul does not edit his capture, perception policy or UI.
4. Run repeated kit evaluation and a clean target-platform package check before
   claiming submission readiness. Cloud inference removes local model memory
   pressure but adds network latency, provider availability and shared quota.

The Groq transcription endpoint processes files, not a continuous two-way
voice session. The existing browser capture and endpointing still decide when
to create previews and final turns. Do not claim Gemini Live-style hands-free
behavior from this provider switch alone.
