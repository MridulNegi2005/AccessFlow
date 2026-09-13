# Active handoff

Last updated by: Codex

## Current Task
Persistent user goal: continue Workstream A until manually stopped. Only Mridul-owned code.

## In Progress
Engine source/race safety and evaluation implementation. 47 offline tests, Ruff and
scripted replay pass. No live inference, official-kit or clinical claims. Luna high workers
reviewed controller behavior and authored trace metrics; parent reviewed and integrated.

## Next Steps
Read docs/ENGINE_PROGRESS.md for evidence and remaining work. Next independent slice:
more fault/cancellation measurements, manifest-driven mock workflow and scenario evaluation.
Atishay continues perception/timing/UI against shared contracts. SessionView.calls is an
additive defaulted field; no B-owned paths changed. Actual model validation still pending.

## Key Files Modified
engine.py, contracts.py, fakes.py, clock.py, evaluation/replay.py, evaluation/trace_metrics.py,
model prompt, regression tests, docs/CONTRACT.md and docs/ENGINE_PROGRESS.md.

## CI constraint
GitHub workflow disabled remotely; YAML manual-only. Do not re-enable or dispatch CI
without user request. Corrected Docker execution still unverified on a Docker host.
