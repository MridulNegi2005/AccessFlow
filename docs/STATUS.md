# Implementation status

Updated 15 September 2026. Workstream A remains in progress; this is implementation
evidence, not an evaluated submission.

The dated entries below are historical. Read this header for current state.

- HEAD is on `mridul/engine`. 280 tests and Ruff pass. The offline `scenarios/dev` suite
  passes 4 of 4.
- `qwen/qwen3.8-27b` on Groq is the primary model. It passed all six `live_dev` fixtures on
  15 September. It requires `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`. See `PROFILES.md` and
  `results/MODEL_COMPARISON.md`, which is generated from recorded traces.
- The Codex review in `reviews/CLAUDE_REVIEW_2026-09-15.md` lists twelve findings. R1, R4,
  R7, R9 and R10 are addressed. R2, R3, R5, R6, R8, R11 and R12 are open.
- No audio or visual fixture exists. Multimodal is at zero, not partial.

## Implemented and locally exercised

- Internal v0.1 contracts, fakes, injected clocks and queue-based session controller.
- Corrections, provisional rollback, source revisions and stale perception/result rejection.
- Manifest-driven tool scheduling, cancellation, operation ledger and uncertain-write status
  reconciliation. Accepted read evidence expires when its dependencies change.
- Dynamic read/write arguments must match tracked slots, with explicit parameter aliases;
  model-provided nonce values cannot split retry identities. Manifest-bound generation
  restricts tool names and uses read-only choices during unresolved writes.
- Atishay perception/policy integrated; final corrections, image readiness and clarification/write guard tested.
- Native subprocess perception lifecycle, Windows PID correctness, cleanup traces and controller cancellation tested.
- Gemini/Ollama reasoning adapters tested with HTTP doubles and bounded request telemetry.
  Local Ollama readiness succeeded; the first two live task pilots failed and are preserved
  in results/LOCAL_MODEL_2026-09-13.md. Further model evaluation remains in progress.
- Manifest-bound in-memory lookup/write/status environment with independent committed effects.
- Four developer-authored text workflows, task criteria, isolated suite runs and causal traces.
- Replay crash/timeout/cancellation evidence and nonzero CLI exits for failed runs or task criteria.
- Late committed writes retained after earlier no-effect claims; contradictory transport status reported.
- Four-condition synthetic controller responsiveness command with auditable raw timestamps.
- 204 local tests and Ruff pass at that date; four development workflows pass in fake
  reasoning mode. Measured run on clean 7a67b44: 400/400 synthetic probes; see results/RESPONSIVENESS_2026-09-13.md.
- Actual gemma3:4b live development suite: 0/4 completed. Two request timeouts and two
  incorrect semantic plans; no effects. Explicit GPU placement improved one request's
  speed but its task still failed. Raw proposals and traces are preserved, not replaced
  by mock successes. See results/LOCAL_MODEL_2026-09-13.md.
- Public repository and teammate bootstrap. Atishay9828 was invited with write permission;
  invitation acceptance has not been checked in this slice.

See [ENGINE_PROGRESS.md](ENGINE_PROGRESS.md) for requirement-level evidence and
[EVALUATION.md](EVALUATION.md) for commands and fixture authoring. Exact test results are
recorded in [handoffs/mridul.md](handoffs/mridul.md).

## Still required

Read this section before starting work and update it before finishing. That applies to every
person and every AI agent on the project. Record evidence in your own handoff file, not here.

### Workstream A — Mridul

- Independently authored held-out cases, and the full 60-scenario set. Fourteen scenario
  files exist: four in `scenarios/dev`, six in `scenarios/live_dev` and four planner probes.
  Several are variants of the same underlying workflow, so the count of independent
  workflows is lower. The probes have never been run and their labels are unread.
- Baseline comparison. The dependency-rejection ablation is complete and returned a negative
  result; see `results/ABLATION_2026-09-15.md`. No baseline arm exists yet.
- End-to-end multimodal runs through the controller, reported by modality and backend.
- Corrected Docker execution on a Docker-capable host; hardware and warm-up measurements.
- Official-kit translation and public-kit runs after the organizer supplies the schema.
- Submission assembly, reviewed disclosure, and the release tag.
- Open defect: `lost-response-status-reconciliation` intermittently fails with
  `missing_dependency` because the status tool's target id is not a slot.

### Workstream B — Atishay

- Held-out speech-quality ASR measurement and validated acoustic VAD integration.
- Live vision backend and a real multimodal benchmark on declared hardware.
- Microphone capture and voluntary feedback notes.
- Demo video and presentation draft.

### Completed since this list was last written

- Live reasoning adapters. `qwen/qwen3.8-27b` is primary and scored 6/6 across `live_dev`
  on 15 September. See results/MODEL_COMPARISON.md, which supersedes the 14 September sweep
  for model selection. The sweep's 20 B to 27 B capacity wall is doubtful: `gpt-oss-20b`
  later cleared a harder fixture, so its earlier failure was probably the output contract.
- Real reasoning on the development scenarios, including the two-step read-then-write chain.
- Team registration.

Atishay reports a real Faster Whisper CPU INT8 run on one generated speech fixture;
see feedback/ASR_MEASUREMENTS.md. This is teammate-recorded adapter evidence on his machine,
not an independently reproduced end-to-end result, held-out score or accessibility benefit.
No live model task-completion or vision-quality target, official compatibility or
end-to-end latency target is certified.

## GitHub Actions

Workflow 357005144 is disabled on GitHub and source is manual-only. Do not enable or
dispatch it without user request. The prior run passed lint/tests/replay and Docker build;
container execution failed because metadata lookup assumed git was installed. That lookup
is fixed and regression-tested locally. Corrected container execution remains unverified.
On the 18:32 IST check, one older run reported startup failure and another remained queued;
the latest run was still from 09:11:24 UTC. No new run was dispatched.
