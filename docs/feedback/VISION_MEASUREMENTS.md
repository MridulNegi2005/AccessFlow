# Vision availability preflight

Recorded 16 September 2026 on `atishay/perception` at commit `311116c`.

The live vision preflight on this evaluation machine found:

- `ollama` is not installed or available on `PATH`.
- `http://127.0.0.1:11434/api/tags` refused the connection.
- No `ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL` is configured.
- No `GEMINI_API_KEY` or `GOOGLE_API_KEY` is configured.
- The repository model cache contains the Faster Whisper snapshot only; no vision model is installed.

Consequently, no live vision-quality result is recorded for the 12 image cases. The existing
loopback HTTP tests and multimodal runs verify provider protocol wiring, payload bounds,
recoverable failures and context retention with deterministic responses. They do not measure
image grounding, live model quality, reasoning quality or user benefit.

To activate a live local run, provide an already-installed Ollama service and model, set
`ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL`, and run the 12 inline PNG cases through the provider
with a fresh recorded backend, model, hardware and timing result. The provider intentionally
does not download models or use a paid fallback.

## Availability recheck — 17 September 2026

The current `atishay/perception` checkout was rechecked before attempting another live run:

- `ollama` is not available on `PATH`.
- `http://127.0.0.1:11434/api/tags` is unavailable.
- No `ACCESSFLOW_OLLAMA_VISION_MODEL` is configured.
- No `ACCESSFLOW_GROQ_API_KEY` is configured.

No live benchmark was started. The existing deterministic child-process loopback test remains
protocol and provenance evidence only; it does not establish live vision grounding or quality.

## Availability recheck — 25 September 2026

Before selecting the next perception task, the local environment was checked
again. No Ollama process was present, `http://127.0.0.1:11434/api/tags` was
unavailable, and the participant kit was absent from the expected
`E:\Downloads\Samsung Stuff\participant-kit\participant-kit` path. No live
vision inference or official raw-media run was started. Existing provider
tests remain protocol evidence, not image-grounding results.
