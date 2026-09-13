# Active handoff

Last updated by: Codex (2026-09-13 16:38)

## Current Task
Persistent Workstream A goal remains active until user stops it. CI must stay disabled.

## In Progress
Engine and evaluation improvements committed. 108 tests and Ruff pass; four developer-authored
mock workflows pass. Clean source 7a67b44 produced 400/400 gated-worker probes. Ack p95 0.471 ms;
_cancel-entry-to-output p95 0.144 ms. See docs/results/RESPONSIVENESS_2026-09-13.md for raw evidence.
This is synthetic queue/controller timing, not speech/model/user-benefit validation.

## Next Steps
Remote origin/atishay/perception advanced to d61d4dc. Read its handoff and review/test in an
isolated checkout before integration. It contains perception/local ASR seam, PCM activity,
turn-policy baseline and fake-agent demo; his handoff states no actual model validation.
Respect B ownership; do not silently patch his modules to fix interface failures. After
integration: actual reasoning setup, broader scenarios and baseline/ablation comparisons.

## Key Files Modified
engine.py, replay.py, trace_metrics.py, responsiveness.py and CLI; focused engine/evaluation
tests; docs/RESPONSIVENESS.md, progress/handoff/AI-use docs; measured reports in docs/results.

## CI constraint
Workflow 357005144 disabled remotely; YAML manual-only. Do not enable or dispatch. Corrected
Docker execution still unverified. No final release tag, forms or participant contact.
