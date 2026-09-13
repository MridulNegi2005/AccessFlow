# Active handoff

Last updated by: Codex (2026-09-13 17:23)

## Current Task
Persistent Workstream A goal remains active. B checkpoint 2a4372a integrated unchanged.
Native process lifecycle is implemented and locally verified; CI must remain disabled.

## In Progress
178 tests and Ruff pass; installed-wheel local profile 4/4. ProcessPerception serializes
native inference, handles cancellation/startup/close, and launches the actual interpreter
on Windows instead of leaving a venv-redirector child alive. Replay closes owned providers
and records cleanup outcome. Controller cancels superseded/interrupt workers; late-result
checks remain. See docs/PROCESS_WORKER.md for actual PID evidence and honest limits.
No actual model was run in this slice. B's ASR report remains teammate-reported evidence.

## Next Steps
Measure/configure actual reasoning/vision and local model warm-up/reload/runtime. Review
B's activity timing contract proposal; add baseline/ablation and broader/held-out cases.
Official-kit schema and corrected Docker execution remain outstanding. Preserve B ownership.

## Key Files Modified
A process adapter/worker, engine worker cancellation, CLI/replay, A lifecycle tests;
PROCESS_WORKER.md, setup/contract/status and AI/sync notes. No public wire/dependency change.

## CI constraint
Workflow 357005144 disabled remotely and YAML manual-only. Do not enable or dispatch.
No final release tag, forms or participant contact.

## Incoming teammate handoff at d61d4dc (historical snapshot)

# Active handoff

Last updated by: Codex on 2026-09-13

## Current Task
Implement AccessFlow Workstream A and prepare independent Workstream B checkout.

## In Progress
Initial engine and 16 offline contract/safety tests pass. Broader race and reconciliation
tests, replay and packaging remain incomplete. GitHub setup was explicitly requested.
This is not a finished hackathon submission.

## Next Steps
Atishay: read ATISHAY_START_HERE.md, branch atishay/perception, build only owned components
against fakes. The public clone path is verified; direct pushes require collaborator access,
otherwise use a fork and pull request. Atishay has completed perception, turn-policy, vision, demo, audio baselines and the dependency-free PCM maintenance checkpoint; next is speech-quality ASR measurement and timing refinement.
Mridul: continue engine tests/fixes on mridul/engine. Integrate small slices.

## Key Files Modified
contracts.py, interfaces.py, fakes.py, clock.py, engine.py; pyproject.toml/uv.lock;
AGENTS.md, docs/CONTRACT.md, docs/IMPLEMENTATION_PLAN.md, docs/STATUS.md and start guide.

## Workflow status recheck (2026-09-13 16:51)
Last updated by: Codex. Workflow remains disabled_manually; no new runs. Current task: workflow explanation completed. In-progress implementation and next steps above remain unchanged. Key files modified: sync context and handoff only.

Workflow recheck (2026-09-13 17:41), Codex: still disabled_manually, manual-only YAML, no new runs. Explanation completed; existing Workstream A work and next steps above remain in progress. Only sync notes changed during this check.

Local-model checkpoint (2026-09-13 17:43), Codex: 185 tests and Ruff pass; portable runtime and real readiness verified. Current task: clean-source live reasoning measurements. New files: scripts and docs/LOCAL_MODELS.md; model/replay telemetry updated. Model task quality, live vision, baseline and kit/Docker gates remain open. CI remains disabled.
