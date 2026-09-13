# Atishay workstream handoff

Date and branch: 2026-09-13 / atishay/perception
Completed: Perception foundation, deterministic turn-policy baseline, replaceable PNG vision seam, minimal fake-agent demo, opt-in local audio demo path, opt-in local Ollama vision path, session path isolation, local model configuration guard, synthetic audio provenance fixtures, PCM/activity baseline, local ASR seam, dependency-free PCM backend, optional VAD/timing candidates, session-scoped browser media upload, microphone WAV capture, held-out generated-case evaluation, feedback-session template, demo recording script and template-neutral presentation outline implemented in owned paths; shared fakes/interfaces remain unchanged.
Contract version used: 0.1
Tests run and results: `uv run --python 3.12 --extra dev pytest -q` — 75 passed; perception run — 43
passed; demo run — 9 passed; Ruff clean for owned paths.
Live-model/backend results: Local Faster Whisper base.en CPU INT8 measured on the development and three generated held-out cases; the opt-in WebSocket demo route also completed a checked-in WAV with the cached model and emitted a local-backend acknowledgment; no human speech accuracy or endpoint-quality claim.
Known failures: Default 3.11 uv target link is broken on this machine; manual browser/device smoke proof, human speech accuracy and endpoint quality, vision quality, hosted backend, completed user feedback session and demo recording are not implemented.
Dependency or contract proposals: Local experiment uses optional webrtcvad-wheels 2.0.14; propose adding it to the shared audio extra after review. No lockfile or contract change was made.
Next independent task: Run a manual browser/device smoke check, then conduct the voluntary session and compare observed behavior with the recording script before engine integration.
AI tools/prompts/outputs and human modifications: Record each milestone in AI_USE_LOG.md.
