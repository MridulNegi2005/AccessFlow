# Implementation status

Updated 13 September 2026. Workstream A remains in progress; this is implementation
evidence, not an evaluated submission.

## Implemented and locally exercised

- Internal v0.1 contracts, fakes, injected clocks and queue-based session controller.
- Corrections, provisional rollback, source revisions and stale perception/result rejection.
- Manifest-driven tool scheduling, cancellation, operation ledger and uncertain-write status
  reconciliation. Accepted read evidence expires when its dependencies change.
- Gemini/Ollama reasoning adapters tested with HTTP doubles; no real model results yet.
- Manifest-bound in-memory lookup/write/status environment with independent committed effects.
- Four developer-authored text workflows, task criteria, isolated suite runs and causal traces.
- Replay crash/timeout evidence and nonzero CLI exits for failed runs or task criteria.
- Public repository and teammate bootstrap. Atishay9828 was invited with write permission;
  invitation acceptance has not been checked in this slice.

See [ENGINE_PROGRESS.md](ENGINE_PROGRESS.md) for requirement-level evidence and
[EVALUATION.md](EVALUATION.md) for commands and fixture authoring. Exact test results are
recorded in [handoffs/mridul.md](handoffs/mridul.md).

## Still required for Mridul's workstream

- Real reasoning on unfamiliar manifests and held-out wording.
- Broader timing/fault measurements, baseline comparison and dependency-rejection ablation.
- Full scenario set, independently authored held-out cases and modality/backend reports.
- Integration with Atishay's raw audio, image and turn-policy implementations when available.
- Corrected Docker execution on a Docker-capable host; hardware/warm-up measurements.
- Official-kit translation and public-kit runs after the organizer supplies the schema.
- Submission assembly, reviewed disclosure and human registration/template/release checks.

No live model, official compatibility, accessibility benefit or latency target is certified.

## GitHub Actions

Workflow 357005144 is disabled on GitHub and source is manual-only. Do not enable or
dispatch it without user request. The prior run passed lint/tests/replay and Docker build;
container execution failed because metadata lookup assumed git was installed. That lookup
is fixed and regression-tested locally. Corrected container execution remains unverified.
Two older push runs still appeared queued on the latest check; no new run was dispatched.
