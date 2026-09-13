# Active handoff

Last updated by: Codex (2026-09-13, after live model experiments)

## Current Task
Persistent Workstream A goal remains active. B checkpoint 2a4372a integrated unchanged.
Improve actual model planning accuracy after preserved failed live runs. CI must remain disabled.

## In Progress
204 tests and Ruff pass (two existing TestClient warnings). Actual Ollama gemma3:4b
live development suite 0/4: two request timeouts, two invalid semantic plans. No effects
or model-invented final successes emitted. Explicit GPU35 reduced one plan request from
19.74 to 11.11 s but task still failed. All traces/plans retained in docs/results.
Portable runtime/models are in D:\AccessFlow-LocalRuntime; server explicitly stopped.
See scripts/start-local-ollama.ps1 and docs/LOCAL_MODELS.md to restart. No paid fallback.
Native lifecycle remains tested; B's ASR report is teammate-reported evidence only.

## Next Steps
Fix demonstrated model misunderstandings (flat slot values, actual tool arguments,
request understanding versus completed effect, 24-hour time); test unfamiliar wording
and explicitly compare another local model if needed. Preserve failed evidence. Then
actual vision/ASR integration, B activity contract review, baselines/ablation and broader
held-out cases. Official-kit schema and corrected Docker execution remain outstanding.

## Key Files Modified
A model/schema/telemetry adapter, final-correction acknowledgment, replay evidence,
local runtime/experiment scripts, live_dev fixture variants, results/docs and A tests.
No B implementation, public wire contract or dependency changes.

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
