# Implementation status

Workstream A remains in progress. This is implementation evidence, not an evaluated
submission.

## Current status

This section is the single authoritative statement of current state. It replaces all older
headers in this file. Read it first. Facts below were measured by the orchestrator on
16 September 2026 at commit `fd53aca` on branch `mridul/engine`, using the commands quoted
next to each fact. Everything dated below this section is historical and is kept for record,
not as current status.

- **Tests:** 384 passed, 0 xfailed, two unrelated deprecation warnings.
  Command: `uv run --offline --frozen --extra dev pytest -q`.
- **Lint:** `uv run --offline --frozen --extra dev ruff check .` reports all checks passed.
- **Offline dev suite:** `uv run --offline --frozen accessflow suite scenarios/dev` reports
  `scenario_count 4, passed 4, failed 0, unscored 0, error 0`.
- **Scenario corpus:** 17 files, 10 distinct tool sets. Modalities: 15 transcript, 2 audio,
  1 frame. Sets: `dev` 4, `live_dev` 9, `planner_probes` 4. See
  [SCENARIO_INVENTORY.md](SCENARIO_INVENTORY.md), which is generated from the files and is
  current.
- **Held-out planner probes:** 4. They ran once on 16 September 2026 on
  `groq/qwen/qwen3.8-27b` and passed 4 of 4, all completed, no backend failure. The
  clarification probe committed zero effects, which is the required safe behaviour. Traces
  are in the ignored `artifacts/heldout/` directory, so a clean clone does not carry them.
  The probes are now spent: they are development data and cannot measure generalization
  again.
- **Evidence bundle:** 57 attempted runs. The quality denominator is **43 of 46**; only 429
  admission refusals are excluded. Earlier documents stated 43 of 45 and 43 of 57. Both of
  those figures were wrong; do not cite them.
- **Docker:** not installed on this machine (`docker: command not found`). The container
  execution gate cannot be verified in this environment at all. This is unmeasured here, not
  passing or failing.
- **`Start.corpus`:** declared at `src/accessflow/contracts.py:37`, has zero consumers
  anywhere in `src/`. Declaring an allowed corpus provides no retrieval, grounding or
  citation. Open; tracked as part of A9 below.
- **Endpoint telemetry:** no trace recorded on or before 15 September 2026 carries
  `config.endpoint`; 0 of 161.

### Findings status

The live list of findings is
[reviews/MRIDUL_REAUDIT_2026-09-15.md](reviews/MRIDUL_REAUDIT_2026-09-15.md), identified
A1 through A9. Read that document for the current state of any specific finding.
[reviews/CLAUDE_REVIEW_2026-09-15.md](reviews/CLAUDE_REVIEW_2026-09-15.md) (R1 through R12) is
the earlier, historical audit. Most of its findings are folded into or superseded by the
A-numbered list; do not cite an R-number as current status.

- **Addressed, with tests:** A1 (clarify-then-image write intent), A3 (audio task-effect
  oracle), A4 (evidence eligibility), A5 (portable ordering), A6 (profile verification), A8a
  (canonical test command), A8b (malformed JSONL), A8c (relative inventory path).
- **Open, blocked on Workstream B:** A2. The perception worker rejects the vision options the
  CLI sends. `AGENTS.md` places `src/accessflow/adapters/` in Workstream A, but Mridul decided
  on 2026-09-15 to leave this one file to Atishay; this deliberately overrides the directory
  rule for that file only. See the ownership note in
  [CONTRACT_PROPOSALS.md](CONTRACT_PROPOSALS.md). Workstream A has finished its own side: the
  CLI now records `vision_provider_requested` instead of naming a vision backend that never
  ran (`src/accessflow/cli.py`).
- **Open, this document:** A7. This update is the repair for A7. The contradictions the
  re-audit found in this file and in `.ai-sync/handoff.md` are corrected below and in that
  file.
- **Open, remaining scope:** A9 — corpus integration and scenario independence (see
  `Start.corpus` above and the corpus note in "Still required"), a matched-timing baseline,
  and release gates (official kit adapter, Docker execution, clean-install evidence,
  submission materials).

### Multimodal coverage

- **Audio:** 2 files, both built on the same committed WAV recording.
  `audio_correction.json` is an ASR and turn-correction smoke check.
  `audio_correction_ambiguous_hour_clarification.json` scores write safety when the spoken
  hour is ambiguous. Two files over one recording are not two independent audio cases.
- **Visual:** 1 file, `frame_device_panel.json`. It cannot run through the process adapter
  because of A2. The one recorded vision run used a temporary, since-reverted worker edit;
  see `docs/results/VISION_E2E_2026-09-15.md`, which states its own status as blocked and not
  reproducible from this checkout.
- Full gap accounting, including the planned-versus-present modality table and the
  known-gaps list, is in [SCENARIO_INVENTORY.md](SCENARIO_INVENTORY.md).

No official-kit compatibility is claimed. No live model, ASR or vision inference was run
during this update.

---

## Historical: entries dated 13-15 September 2026

Everything below this line was written before the "Current status" section above. It is
kept for history and is not current. Counts inside it (test totals, scenario-file totals,
finding IDs) belong to the date each entry carries and are superseded by "Current status".

### Implemented and locally exercised (as of 15 September 2026)

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

- Independently authored held-out cases, and the full 60-scenario set. The corpus currently
  has 17 scenario files: 4 in `scenarios/dev`, 9 in `scenarios/live_dev` and 4 planner probes.
  See [SCENARIO_INVENTORY.md](SCENARIO_INVENTORY.md) for the distinct-tool-set count and for
  which files are repeats of the same underlying workflow. The probes ran once on 16
  September 2026 and
  their labels are unread.
- Baseline comparison. The dependency-rejection ablation is complete and returned a negative
  result; see `results/ABLATION_2026-09-15.md`. No baseline arm exists yet.
- End-to-end multimodal runs through the controller, reported by modality and backend.
- Corrected Docker execution on a Docker-capable host; hardware and warm-up measurements.
  Not verified in this environment: Docker is not installed on this machine.
- Official-kit translation and public-kit runs after the organizer supplies the schema.
- Submission assembly, reviewed disclosure, and the release tag.
- **Resolved since this list was last written:** the `missing_dependency` failure on
  `lost-response-status-reconciliation`, previously listed here as an open defect, is fixed.
  `tests/engine/test_reconciliation.py` and `tests/engine/test_suite.py` cover the receipt
  parameter case, and `reviews/MRIDUL_REAUDIT_2026-09-15.md` does not list it as open.

### Workstream B — Atishay

- Held-out speech-quality ASR measurement and validated acoustic VAD integration.
- Live vision backend and a real multimodal benchmark on declared hardware.
- Accept the optional vision-provider options in `src/accessflow/adapters/perception_worker.py`
  and pass the constructed provider to `LocalPerception(vision_provider=...)`, keeping the
  default `none` so audio-only behaviour is unchanged. This is finding A2; see the ownership
  note in `CONTRACT_PROPOSALS.md` for why this file stays with Atishay despite the general
  directory rule.
- Microphone capture and voluntary feedback notes.
- Demo video and presentation draft.

### Completed since this list was last written (as of 15 September 2026)

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
