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
