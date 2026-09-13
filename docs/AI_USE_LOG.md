# AI-use development log

## 2026-09-13 — Codex bootstrap

- Feature origin: User-approved AccessFlow plan; original friend-agent proposal and prior
  ideation should be described honestly in the final organizer disclosure.
- Tool: Codex (current coding session).
- Prompt: Implement the approved AccessFlow implementation/collaboration plan; prioritize
  Git initialization, folder organization and context so Atishay can start independently.
- Output: Contracts, interfaces, fakes, initial controller, project configuration and docs.
- Human modifications/review: Not yet recorded; do not imply team review has occurred.
- Validation: Record actual commands/results in handoffs. No live-model evidence yet.

Append each future milestone with prompts, outputs, edits, tests and reviewer. This log
supports the mandatory organizer form; it is not a completed or signed disclosure form.

## 2026-09-13 - Codex Atishay audio fixture checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a reproducible audio fixture with explicit provenance and format validation.
- Output: Added a synthetic tone WAV, SHA-256 provenance and a checked-in fixture test.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 16 passed; Ruff passed for owned paths.
- Backend/dependencies: Python standard-library audio generation; no dependency or contract changes.
## 2026-09-13 - Codex Atishay ASR checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Make the optional local Faster Whisper path testable without model downloads.
- Output: Added model-path validation, CPU int8 factory configuration and segment aggregation tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 23 passed; Ruff passed for owned paths.
- Backend/dependencies: Faster Whisper remains optional; no dependency or contract changes; no live model run.
## 2026-09-13 - Codex Atishay PCM checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a small reusable PCM loader and deterministic activity baseline without changing shared contracts.
- Output: Added mono/stereo loading, rate conversion, RMS activity frames and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 21 passed; full suite verification follows; Ruff passed for owned paths.
- Backend/dependencies: Python standard library `audioop`; deprecation recorded, no lockfile change.
## 2026-09-13 - Codex Atishay demo checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Build a minimal fake-agent browser demo that renders controller output events.
- Output: Added FastAPI WebSocket routing, typed event conversion, mock-labeled controls and smoke tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 6 passed; full suite 37 passed; Ruff passed for owned paths.
- Backend/dependencies: Existing FastAPI stack; no dependency or contract changes. Test-client deprecation warnings recorded.
## 2026-09-13 - Codex Atishay vision checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a replaceable PNG provider path while preserving frame and event provenance.
- Output: Added standard-library PNG validation, injected provider execution and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused perception suite 15 passed; Ruff passed for owned paths.
- Backend/dependencies: Injected provider seam; no dependency or contract changes.

## 2026-09-13 - Codex Atishay turn-policy checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Implement a compact synchronous turn policy against the existing v0.1 observation contract.
- Output: Added correction, backchannel, partial-speech and stale-revision decisions with focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Full suite 29 passed; Ruff passed for owned paths.
- Backend/dependencies: Model-free heuristic; no dependency or contract changes.

## 2026-09-13 — Codex Atishay handoff

- Feature origin: User request to prepare Atishay’s independent repository start point.
- Tool: Codex (current coding session).
- Prompt: Verify the public clone/branch path and provide accurate `ATISHAY_START_HERE.md` guidance.
- Output: Confirmed the clone and branch checkout; clarified that direct pushes need collaborator
  access and that fork-based pull requests are the fallback.
- Human modifications/review: Awaiting Atishay’s review.
- Validation: `uv run --python 3.12 --extra dev pytest tests/test_contract.py` — 4 passed.
- Backend/dependencies: No live backend and no committed dependency changes.

## 2026-09-13 - Codex Atishay PCM maintenance checkpoint

- Feature origin: The approved AccessFlow Workstream B plan and the handoff requirement to replace deprecated audioop.
- Tool: Codex (current coding session).
- Prompt: Replace the owned audioop PCM path with a small maintained implementation without changing the shared contract.
- Output: Added standard-library PCM decoding, stereo downmixing, linear resampling and RMS helpers; added 1/2/3/4-byte coverage.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused audio suite 9 passed; Ruff passed for owned paths; no audioop import remains.
- Backend/dependencies: No dependency or lockfile change; no live ASR/VAD evidence.

## 2026-09-13 - Codex Atishay local ASR measurement

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Run the explicitly installed Faster Whisper base.en CPU INT8 backend on the checked-in audio fixture and record timing honestly.
- Output: Installed the optional runtime in the ignored virtual environment, downloaded the model into the ignored models directory and recorded the first local pass.
- Human modifications/review: Awaiting Atishay review.
- Validation: Model loaded in 0.464 s; inference took 0.677 s for 0.500 s of audio; realtime factor 1.354; transcript was empty as expected for a synthetic tone.
- Backend/dependencies: Faster Whisper 1.2.1, Systran/faster-whisper-base.en, CPU int8; no tracked dependency or contract change.
## 2026-09-13 - Codex Atishay demo teardown repair

- Feature origin: Full-suite verification of the Workstream B demo.
- Tool: Codex (current coding session).
- Prompt: Fix the WebSocket demo cleanup so normal disconnects await the queue-driven agent shutdown cleanly.
- Output: The demo now cancels only transport tasks, sends a typed session-end event and waits briefly for the agent before cancelling as a last resort.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 6 passed; full suite 50 passed; Ruff passed for owned paths.
- Backend/dependencies: No dependency or contract change.
## 2026-09-13 - Codex Atishay illustrative speech ASR run

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Generate a clearly labeled non-participant speech fixture and run the installed Faster Whisper base.en CPU INT8 adapter.
- Output: Added synthetic_speech.wav with provenance and recorded a LocalPerception.observe run.
- Human modifications/review: Awaiting Atishay review.
- Validation: 5.304 s fixture; adapter elapsed 5.874 s; realtime factor 1.108; transcript matched the known script apart from the final number wording.
- Backend/dependencies: Faster Whisper 1.2.1, CPU int8; no tracked dependency or contract change.
## 2026-09-13 - Codex Atishay timing-only activity summary

- Feature origin: The approved AccessFlow Workstream B plan and the v0.1 contract limitation around timer events.
- Tool: Codex (current coding session).
- Prompt: Add a timing-only activity summary that reports pauses without converting them into turn completion, and record an additive contract proposal.
- Output: Added contiguous activity windows, silence durations, pause signal tests and a pending timing metadata proposal.
- Human modifications/review: Awaiting Atishay and Mridul review.
- Validation: Focused audio/timing suite 13 passed; Ruff passed for owned paths; no shared contract changed.
- Backend/dependencies: Standard library energy frames; no dependency or lockfile change.
## 2026-09-13 - Codex Atishay optional WebRTC activity backend

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a lazy optional WebRTC VAD adapter with deterministic injection tests, then compare it with the energy baseline on the two generated fixtures.
- Output: Added 8/16/32/48 kHz and 10/20/30 ms format validation, optional package loading, and activity comparison evidence.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused perception suite 15 passed; Ruff passed for owned paths. Tone: WebRTC 25/25 active frames. Generated speech: WebRTC 189/265 active frames and 0.640 s trailing silence.
- Backend/dependencies: webrtcvad-wheels 2.0.14 in the ignored environment only; no tracked dependency, lockfile or contract change.

## 2026-09-13 - Codex Atishay pause-and-correction fixture

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Generate a non-participant speech fixture with an explicit pause and self-correction, then measure ASR and acoustic activity.
- Output: Added synthetic_pause_correction.wav with provenance and recorded WebRTC and Faster Whisper results.
- Human modifications/review: Awaiting Atishay review.
- Validation: 6.024 s fixture; WebRTC 139/301 active frames across three windows with 0.640 s trailing silence; ASR elapsed 1.334 s and realtime factor 0.221; transcript preserved the correction wording.
- Backend/dependencies: Faster Whisper 1.2.1 and webrtcvad-wheels 2.0.14 in the ignored environment; no tracked dependency, lockfile or contract change.

## 2026-09-13 - Codex Atishay browser media upload boundary

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Make selected WAV and PNG files travel through the minimal browser demo as validated session-scoped media while retaining the explicit mock perception boundary.
- Output: Added base64 upload decoding, size/type validation, temporary session storage, browser file encoding and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 9 passed; full suite verification follows; Ruff passed for owned paths.
- Backend/dependencies: Existing FastAPI WebSocket stack; no dependency or contract change. Microphone remains mock.
