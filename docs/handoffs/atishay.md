# Atishay workstream handoff

Date and branch: 2026-09-13 / atishay/perception
Completed: Perception foundation, deterministic turn-policy baseline, replaceable PNG vision seam, minimal fake-agent demo, synthetic audio provenance fixture, PCM/activity baseline, local ASR seam and dependency-free PCM backend implemented in owned paths; shared fakes/interfaces remain unchanged.
Contract version used: 0.1
Tests run and results: `uv run --python 3.12 --extra dev pytest -q` — 59 passed; perception run — 34
passed; demo run — 9 passed; Ruff clean for owned paths.
Live-model/backend results: Local Faster Whisper base.en CPU INT8 measured on both fixtures; tone adapter 1.233 s for 0.500 s, generated speech adapter 5.874 s for 5.304 s (realtime factor 1.108); no held-out accuracy claim.
Known failures: Default 3.11 uv target link is broken on this machine; manual browser/device smoke proof, held-out speech-quality ASR, acoustic VAD endpoint quality, vision quality, hosted backend and user feedback evidence are not implemented.
Dependency or contract proposals: Local experiment uses optional webrtcvad-wheels 2.0.14; propose adding it to the shared audio extra after review. No lockfile or contract change was made.
Next independent task: Add held-out speech cases and evaluate endpoint behavior against both activity backends.
AI tools/prompts/outputs and human modifications: Record each milestone in AI_USE_LOG.md.
