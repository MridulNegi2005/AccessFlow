# Active handoff

Last updated by: Codex (2026-09-13, argument dependency repair)

## Current Task
Persistent Workstream A goal remains active. B checkpoint 2a4372a integrated unchanged.
Improve actual model planning accuracy and dependency enforcement. CI must remain disabled.

## In Progress
224 tests and Ruff pass (two existing TestClient warnings). Actual Gemma suite 0/4;
explicit Qwen2.5:3b original and guided prompt runs each 1/4 on known text cases.
All failures retained. Qwen's invented tool names and repeated write instead of status
query remain task failures. New controller guards reject untracked/contradictory arguments
and preserve retry identity across model nonce changes. Optional argument_slots maps aliases.
Model generation now binds exact tool names and read-only choices during unresolved writes.
Portable runtime/models are in D:\AccessFlow-LocalRuntime; server is currently running
for the next clean-source measurement. Stop it with scripts/stop-local-ollama.ps1 after runs.
Native lifecycle remains tested; B's ASR report is teammate-reported evidence only.

## Next Steps
Measure the controller/schema fixes on known cases, then run independent AI planner probes
before reading their expected labels. Preserve failed evidence. Then
actual vision/ASR integration, B activity contract review, baselines/ablation and broader
held-out cases. Official-kit schema and corrected Docker execution remain outstanding.

## Key Files Modified
A contracts/controller/model adapter and regression tests; contract documentation and
Qwen guided-run evidence. Optional internal argument_slots is additive, not official wire.
No B implementation, package dependency or CI changes.

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

Live evidence checkpoint (2026-09-13 17:57), Codex: two failed real pilots preserved in docs/results/LOCAL_MODEL_2026-09-13.md. Source fixes include grounded explicit planner schema, correction acknowledgment, fixture formats and diagnostics. Runner verifies model reset and aborts on cleanup failure; parent added cooperative cancellation reports. Next: clean-source live four-case experiment. B ownership and CI-off constraint unchanged.

Workflow check (2026-09-13 18:32), last updated by Codex: explanation completed; CI remains disabled and manual-only. No new workflow runs. Existing implementation next steps preserved. Key files modified: sync notes, A handoff and AI-use log only.
