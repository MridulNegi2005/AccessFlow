# Mridul workstream handoff

Date and branch: 2026-09-13 / mridul/engine
Completed: Contracts/controller, source isolation, provisional rollback, dynamic scheduling,
operation ledger/reconciliation, model HTTP adapters, causal traces, manifest-driven mock
environment, explicit task criteria and four-case development suite. Accepted reads expire
when corrected dependencies change. Replay preserves crash/timeout evidence and fails its
CLI command on failed criteria. Immediate canceled-operation retries have independent attempts.
Contract version used: 0.1; no public contract changes in this slice.
Tests run and results: `uv run pytest -q` — 92 passed; `uv run ruff check .` passed.
`uv run accessflow suite scenarios/dev --output-dir artifacts/development-suite` — 4/4 passed.
`uv build --out-dir artifacts/dist` — source distribution and wheel built.
Isolated installed-wheel CLI suite — 4/4 passed; module path verified in site-packages.
Live-model/backend results: None. All outcome results above are offline-fake development cases.
Known failures/limits: No live ASR/vision/reasoning or official-kit score; corrected Docker
execution remains unverified. No baseline/ablation or 60-case held-out evaluation yet.
Dependency or contract proposals: None added; dependency lockfile unchanged.
Next independent task: Causal controller cancellation/ack measurement under inference/tool
load, baseline/ablation harness, broader scenarios, then real reasoning validation.
AI tools/prompts/outputs and human modifications: Codex implementation and review; Luna high
workers drafted/revised the mock environment and retry races. No human review recorded yet.
GitHub Actions: Disabled remotely and manual-only in source. Do not enable or dispatch.
Atishay: No B-owned components edited. Read EVALUATION.md to run or author cases independently.

## Responsiveness and conflicting-outcome slice
108 local tests and Ruff pass; four-case development suite passes. Added gated-worker timing
CLI with four conditions (smoke: 8/8 probes), raw queue/method timestamps and p95 target checks.
Added five regression cases for late/inconsistent committed write results; the initial four
failed before the fix. The fifth guards duplicate/conflicting delivery after a late commit. Metrics distinguish normal retries from within-attempt contradictions and
exclude ordinary failed reads from write outcomes. Confirmed cancellation evidence is traced.
Next: commit source, measure 100 samples per condition against that clean commit, save reviewed
raw samples/report, then real reasoning access and baseline/ablation. CI remains disabled.

## Measured result and next integration
Code commit 7a67b44 (clean): 100 samples per condition, 400/400 passed. Aggregate acknowledgment
p95 0.47073 ms; cancellation method-entry-to-output p95 0.144025 ms. Independent raw timestamp
and p95 checks passed. Evidence: docs/results/RESPONSIVENESS_2026-09-13.md and linked JSON/JSONL.
Atishay remote advanced to d61d4dc (ASR/perception/timing/demo foundations). Read his branch
handoff and review/test in isolation next. His handoff reports no live model validation.
No shared/B files were changed to force integration; current engine worktree remains separate.

## Integrated checkpoint d61d4dc

Combined engine and B components: 151 tests and Ruff pass; both fake and local component
profiles pass the four development cases. See INTEGRATION_2026-09-13.md for reproduced
failures and A-only fixes. Contract v0.1 unchanged; existing semantic completion fields
are documented. Raw-media callbacks are doubles, no model quality claim. No dependencies
added. Next: bounded native worker lifecycle, actual model setup, baselines/ablation and
broader evaluation. B browser revision/lifecycle findings are documented for Atishay.
CI remains disabled. Human review has not been recorded.

Before publication, Atishay advanced to 2a4372a. Review its PCM/timing changes and
reported illustrative-speech ASR evidence next; this merge tests d61d4dc only.

## Follow-up integration: 2a4372a
159 tests and Ruff pass after merging B's PCM/timing/demo updates. B-owned bytes unchanged;
both WAV hashes/durations match provenance. ASR measurements are B-reported, not rerun here.
Next: A subprocess perception adapter and replay ownership/cleanup; worker development is
in progress on the canonical checkout. No CI trigger, dependency or public schema change.

## Native process lifecycle checkpoint
178 tests and Ruff pass. CLI local profile uses ProcessPerception; replay owns optional
aclose, reports cleanup failures, and closes on cancellation. Controller cancels superseded
same-source perception, old frames and interrupted perception/reasoning without awaiting
native work on the dispatcher. Source/epoch checks still reject late callbacks.
Luna drafted the adapter; parent fixed canceled-startup restart and Windows venv redirector
PID behavior and added integration tests. Real worker-entry PID and exit verified.
Fresh installed-wheel local suite 4/4; actual packaged child starts and reports missing-WAV
failure; no live inference. B2a4372a implementation unchanged. See PROCESS_WORKER.md.
Next: live reasoning/vision and model warm-up/runtime, activity-contract proposal review,
baselines/ablation and broader scenario set. Official kit and Docker verification remain.
CI disabled/manual-only. No new dependencies or public wire fields. Goal remains active.

## Local-model instrumentation checkpoint
185 tests and Ruff pass. Luna high drafted bounded request telemetry and warm-up validation; parent reviewed, integrated replay evidence and added portable runtime/measurement scripts. Real cold readiness: 144.93 s; not a task-quality result. D: runtime/model storage avoids nearly full C:. See LOCAL_MODELS.md. Next: clean-source live task measurements. No B-owned code, dependencies, CI or release changes.

## 2026-09-13 — Explicit live planner decisions
Real local pilot on clean 6099497: readiness 18.32 s, valid model plan in 8.23 s,
no calls and unresolved completion; task timed out at 30 s with zero mock effects.
Generation schema previously allowed every top-level field to be omitted. A-side fix
requires explicit output fields and dependencies in the model schema, explains resolved
corrections and action planning in the system prompt; internal v0.1 defaults unchanged.
Focused model tests 13 pass and Ruff passes. Same-fixture live retry follows; this is
development tuning, not a held-out comparison. CI remains disabled.

## Grounded planning and fair live fixtures
Original pilots remain failures; schema grounding follows official Ollama guidance. Parent added explicit dependency descriptions and input-size accounting. Final correction gets immediate acknowledgment while model runs, with write guards intact. 194 full tests passed before adding two focused runner cancellation tests; those pass (runner6). Four live-dev variants pass scripted plumbing only. PowerShell actual stop/restart and port refusal pass. No OS listener ownership check in Python runner; use only verified project server. Next: clean-source actual live suite.
