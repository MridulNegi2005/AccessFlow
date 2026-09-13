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
