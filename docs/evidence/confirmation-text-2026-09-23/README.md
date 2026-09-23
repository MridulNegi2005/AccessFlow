# Confirmed-action presentation evidence

These are exposed development checks, not repeated official results or voice-user testing.
Application source was frozen during each full suite and live run. Final implementation
is committed with this bundle; its Python source digest is recorded in manifest.json.
Both reports show a dirty worktree because tests preceded the implementation commit.

- Intermediate: 1184 passed, 2 skipped, 1 expected failure; booking scorer 100.
  This version had readable text but lacked explicit mock wording; it is retained,
  not counted as a separate reliability repetition or final-source proof.
- Final: 1186 passed, 2 skipped, 1 expected failure in 64.47 seconds; focused 23 passed,
  repository Ruff clean. The two skips are existing Windows symlink restrictions;
  conflicting-frame expected failure and dependency deprecation warnings remain.
- Final booking: scorer 100, failure null, all 3 provider calls successful (including
  warm-up), 4794 reported input tokens. Exactly one search and one mock booking.
  Final at 6407ms; 5500ms after the last text-turn input. No new latency claim.
- Final spoken output: The mock action is confirmed. Status: "success".
  Booking ID: "BK-0001". Flight ID: "FL-DEN-8AM".

Backend: Groq Qwen qwen/qwen3.8-27b; compact-v2, evidence read mode, JSON mode off,
950 output-token budget, 32768 context-character budget, 1s partial debounce,
fast read retry enabled. These experimental settings remain opt-in. Tool results
come from Samsung's mock harness. No private recordings or real bookings involved.

Reproduce software checks with:

```powershell
uv run --offline --frozen --extra dev pytest tests/engine/test_confirmation_text.py -q
uv run --offline --frozen --extra dev pytest -q
uv run --offline --frozen --extra dev ruff check .
```

For live reproduction, configure the backend above and an environment credential,
then run scripts.run_samsung_check with the local participant kit and
pub_03_text_chained_booking.json. The existing runner records prompts, raw traces,
configuration and source digests. Provider access and quota are external dependencies.
Do not overwrite these reports with new attempts. Source truth, arbitrary field
semantics, clinical usefulness and speech playback are not established here.
