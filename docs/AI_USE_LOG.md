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
