# Ownership-safe integration review — 26 September 2026

## Branch order and source preservation

The starting `main` was `e4be637`. Mridul's `mridul/engine` reached
`353fe98` and was fast-forwarded into local `main` **first**. A separate
`integration/ownership-safe-20260926` branch then merged Atishay's pushed
`atishay/perception` at `e04f943`. The teammate branch was not rewritten.

Atishay's two commits had edited five A-owned paths: `contracts.py`,
`engine.py`, and three `tests/engine` files (`test_binding_integration_review`,
`test_request_scope`, `test_speech_status`). Those versions were **excluded**
from the merge. Mridul's D1/D4 controller, image registry, tool/write guards,
and A tests remain the authoritative base. Only small A-owned compatibility
edits were made here: the shared `TurnDecision` contract accepts the two
B policy outcomes, the controller routes a policy-recognized long stop phrase
through its existing control path, and held clarification is visible in state.
An A-owned regression protects that seam.

The merged B-owned paths are `demo/app.py`, `demo/index.html`,
`demo/live-voice.js`, `src/accessflow/turn_policy/heuristic.py`, the two
browser Node checks, `tests/demo/test_app.py`, the two perception policy/stop
tests, and Atishay's timestamped handoff. His historical sync-context entries
were retained. Shared `STATUS`, `AI_USE_LOG`, and active handoff were preserved
from A, then updated with this verified integration record.

`docs/PROJECT_RUNDOWN_SIMPLE_2026-09-26.md` remains on Atishay's branch but
was omitted from `main`: it calls the runnable evaluator unavailable and D4
unimplemented, while this checkout has the runnable
`../participant-kit/participant-kit` and A's D4 registry. Merging that document
as the current project map would mislead the next agent. Its omission does not
delete it from Atishay's branch.

## Verification and limits

- Focused A/B stop and policy integration: **55 passed**.
- Combined Python suite: **1,451 passed, 6 skipped, 5 failed** in 94.44 s.
  The five failures are B-owned demo assertions still based on pre-D4
  single-image replacement or a strict xfail for a D4 behavior that now passes.
  They were already present before this merge and are listed in the D4 handoff.
- All seven browser Node checks passed.
- The previously tested A cloud media path directly transcribed a generated
  WAV and described a PNG; one configured setup hit Groq 429 and a later setup
  passed. No official audio/visual score or physical-microphone test follows
  from those calls.

The B demo currently enables its live ASR preview only when configured
perception mode is `process`; the new `cloud` mode therefore does not yet
provide that preview path. Atishay owns the browser/perception integration and
should fix this alongside the five obsolete D4 assertions, then run his twelve
real-inference attempts and four physical microphone cases. Mridul owns package
and official-kit verification. No teammate source was edited to conceal a test
failure; no release tag or final submission was created.
