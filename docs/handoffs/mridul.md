# Mridul workstream handoff

## Current integration checkpoint — 22 September 2026

This dated checkpoint supersedes older current-state, branch and kit-availability
claims below; those sections are historical records, not fresh verification.
Mridul merged first (`5c84976`), then Atishay (`a0c36c5`), without conflicts.
The other AI's pending engine/test changes were preserved in `93afd57`.

- Combined suite: **842 passed, 1 xfailed**, with two dependency deprecation warnings.
  Command: `uv run --offline --frozen --extra dev pytest -q`.
- Ruff: passed (`uv run --offline --frozen --extra dev ruff check .`).
- Offline-fake development suite: **4/4 passed** (`python -m accessflow.cli suite scenarios/dev`).
- The retained conflicting-frame xfail is not proof of safe conflict handling.
- Both branch tips are ancestors of main. No implementation added by this merge session.
- Samsung kit is now available outside the repository. Its README says Theme 5;
  the enclosing ZIP name says Theme02. Official adapter is still unimplemented.
- No live inference, official evaluation, Docker test or fresh security audit was run.
  Prior issue-closure statements are not independently certified by these tests.
- Workflow remains manual-only; no workflow enabled or dispatched.

Next: implement Mridul's official queue adapter, coordinating MP3/timing/frame
interfaces with Atishay. Details and ownership: docs/INTEGRATION_2026-09-22.md.


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

Full live development run on79bd263 completed0/4; reports/traces preserved. Next isolate GPU placement with ACCESSFLOW_OLLAMA_NUM_GPU; same planner and timeouts, not a claimed semantic fix. Missing raw model accuracy, baselines, full60 cases, officialkit and Docker gates remain. CI stays off.

## Final live-measurement checkpoint
204 tests and Ruff pass; two existing TestClient warnings. Real gemma3:4b suite0/4 and GPU35 textpilot still failed. All reports/typed plans/source hashes saved under docs/results/local-model-2026-09-13. GPU35 readiness12.68s, modelrequest11.11s versus19.74s auto on same case; generated tokens differed, so not a latency distribution. Server explicitly unloaded/stopped. Next: request-completion and data-shape semantics plus alternate local-model comparison, then actual modalities and broader benchmarks. No B/CI/dependency changes. Human review pending.

## Planner accuracy iteration
Explicit Qwen2.5:3b comparison on clean82a9d0c:1/4 task criteria passed with original prompt. Raw plans expose missing slot updates and repeated writes after unknown outcomes (retry blocked). Source now clarifies required flat slot state and argument format; ledger-derived status guidance uses dynamic manifests.24 model tests and Ruff pass. Four independently drafted AI probes are copied without parent reading expected labels before first scoring; not final held-out evidence. Next: clean-source known suite and new probes. Dependency coverage audit pending; don't claim full live safety from one task pass.

## [2026-09-13 18:32] — Codex
**Task:** Explain GitHub workflow failure emails.
**Changes:** Read-only GitHub verification; no workflow enabled, dispatched or changed.
**Status:** completed (workflow check only).
**Notes:** Workflow 357005144 remains disabled_manually; local YAML is manual-only. Latest run 34749085599 still dates to 09:11:24 UTC: lint/tests/replay/build passed, container execution failed. Missing-git handling fixed in aa255bc; corrected container execution unverified. Run 34749085594 now reports startup_failure; 34749085039 remains queued. Existing Workstream A remains in progress.

---


## [2026-09-13 18:40] — Codex
**Task:** Repair dynamic argument dependencies and retry identities; constrain model tool selection.
**Changes:** Optional argument_slots mapping; read/write parameter grounding; model nonce excluded from operation signature; exact manifest tool-name generation and read-only choices while outcomes are unknown. Preserved guided Qwen run and contract notes.
**Status:** in-progress (persistent Workstream A goal).
**Notes:** Seven reproduced failures fixed; full224 tests and Ruff pass with two existing TestClient warnings. Guided Qwen before repairs:1/4 known text cases. Next: clean-source real run and unread independent probes. No B-owned changes or CI runs.

---

## [2026-09-13 18:47] — Codex
**Task:** Safely stop at the user's explicit request.
**Changes:** Saved final Qwen report/traces. Unloaded models and stopped verified Ollama process; no listener on11435 or live model-check process remains. All child agents completed.
**Status:** stopped by user; project incomplete. Do not resume until user requests it.
**Notes:** Engine commit3e24c06 pushed to mridul/engine;224 tests/Ruff passed. Actual guarded Qwen suite2/4: corrected-device and lost-response recovery pass; support omits slots, text correction leaves completion/write flags false. Independent planner probes remain unrun/unread. Review wrote only sync notes during live run; source code stayed at3e24c06, so dirty-worktree flags in raw evidence reflect docs only. CI remains disabled. Next on explicit resume: address incomplete model plans, then unseen probes and remaining Workstream A gates.

---

## [2026-09-13 20:45] — Claude Code
**Task:** Add a Groq hosted reasoning backend to test planner accuracy against larger open models.
**Changes:** `JsonBackend` accepts `groq` beside `ollama` and `gemini`. Backend model defaults move to a
`DEFAULT_MODELS` table. The Groq branch uses the OpenAI-compatible chat completions endpoint, bearer
authentication, temperature 0 and `response_format` `json_object`. Strict `json_schema` output is
opt-in through `ACCESSFLOW_GROQ_STRUCTURED=1`, because strict mode rejects some schemas this project
generates. Request evidence records the Groq `usage` block: queue time, prompt time, completion time,
token counts and total time. The CLI accepts `--backend groq` for `replay`, `warmup` and `suite`.
**Status:** in-progress. Adapter is complete and tested. The live comparison is not run.
**Tests run and results:** `uv run pytest -q` — 231 passed, two existing TestClient warnings.
`uv run ruff check .` passed. Seven new Groq tests cover request shape, opt-in structured output,
missing key, rate-limit non-retry, usage metric filtering, GPU rejection and unknown backend rejection.
End-to-end check: `accessflow warmup --backend groq` against a local stub that speaks the Groq wire
format returned `ready: true` and exit code 0. The stub confirmed path, bearer header, model,
temperature, response format and message roles.
**Live-model results:** None. No Groq API key exists on this machine.
**Known failures/limits:** No hosted key is configured, so no accuracy comparison against the saved
gemma3:4b 0/4 and guarded Qwen2.5:3b 2/4 results. The default model id `llama-3.3-70b-versatile`
must be checked against Groq's current model list before a scored run. Free-tier rate limits are
unmeasured and matter across a 60-scenario suite.
**Dependency or contract proposals:** None. No new dependency. No public schema change.
**Next independent task:** Set `ACCESSFLOW_GROQ_API_KEY` in `.env`, then run
`accessflow suite scenarios/live_dev --backend groq` and compare against the preserved local traces.
**AI tools and human modifications:** Claude Code (Opus 5) wrote the adapter, tests and this entry.
No human review recorded.
**Atishay:** No B-owned files changed. CI remains disabled. No push performed.

## [2026-09-13 21:20] — Claude Code
**Task:** Test whether a larger open model fixes the planner failures.
**Changes:** Added `--request-timeout` and `--inference-timeout` to the CLI and plumbed the
controller deadline through `run_suite` and `replay`. Defaults are unchanged. Pulled
`qwen2.5:7b-instruct` to the existing D: runtime.
**Status:** in-progress. The local scaling question is answered. The hosted question is not.
**Tests run and results:** `uv run pytest -q` — 234 passed. `uv run ruff check .` passed.
Fair comparison on `scenarios/live_dev`, same commit, same prompt, same guards, 90-second
requests and a 95-second controller deadline: qwen2.5:3b 2/4 and qwen2.5:7b-instruct 2/4.
Mean successful request 10.1 s versus 26.5 s. See results/MODEL_SCALING_2026-09-13.md.
**Live-model results:** A larger local model gave no accuracy gain at about 2.6 times the
latency. The two models passed different subsets, so this is not a capability ordering.
`support-read-then-service` failed on both. Each model ran once.
**Known failures/limits:** An earlier 7B run scored 1/4 only because the fixed 25-second
controller deadline cancelled the requests. Any earlier result reporting `backend_failure`
is unmeasured, not a planning error. Single runs; no repeat measurement of variance.
No hosted key, so the large-model hypothesis remains untested.
**Dependency or contract proposals:** None. No new dependency. No public schema change.
**Next independent task:** Run the Groq backend once a key exists, then decide between
planner redesign and a hosted model. Repeat runs to separate variance from capability.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI remains disabled. Nothing pushed.

## [2026-09-14 00:35] — Claude Code
**Task:** Run the hosted Groq comparison against the preserved local baselines.
**Changes:** Added HTTP status code and bounded provider error text to request evidence.
Added results/HOSTED_MODEL_2026-09-14.md. No engine or contract change.
**Status:** in-progress. The model-capacity question is answered. Multimodal and the
official kit remain open.
**Tests run and results:** `uv run pytest -q` — 235 passed. `uv run ruff check .` passed.
Paced hosted run on `scenarios/live_dev`, Groq `qwen/qwen3.8-27b`, one scenario every
75 seconds: **4/4 passed**, 6 requests, mean 0.91 s, maximum 1.03 s, slowest scenario 2.0 s.
**Live-model results:** The hosted 27B model passed every case, including
`support-read-then-service`, which failed on gemma3:4b, qwen2.5:3b and qwen2.5:7b. Local
baselines were 0/4, 2/4 and 2/4. The remaining planner failures were model capacity, not
the interface contract.
**Known failures/limits:** Two batched suite runs scored 3/4 and 2/4. Every failure was
HTTP 429 free-tier ITPM throttling at 7000 input tokens per minute, not a planning error.
Requests average 1459 prompt tokens, so the ceiling is about 4.8 requests per minute. A
60-scenario run implies about 25 minutes of rate-limited time. The system prompt is 781
tokens, 54 percent of an average request. The configured default `llama-3.3-70b-versatile`
is not available on this account. The official guide does not state that the evaluation
environment has outbound network access; a hosted-only submission scores zero if the
harness is sandboxed. Each configuration ran once.
**Dependency or contract proposals:** None. No new dependency. No public schema change.
**Next independent task:** Decide the backend policy for submission, keeping local working.
Then multimodal end-to-end, which is 50 percent of the hidden set at a 1.5 multiplier.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI remains disabled. Nothing pushed. Groq also hosts
`whisper-large-v3` and `whisper-large-v3-turbo`, subject to the same network caveat.

## [2026-09-14 01:30] — Claude Code
**Task:** Repeat trials on lightweight local models; check whether Gemma 4 is usable locally.
**Changes:** `ACCESSFLOW_OLLAMA_THINK` controls the Ollama think field. Groq request path
generalised into a shared OpenAI-compatible branch; NVIDIA NIM registered against it.
Added results/LOCAL_REPEAT_2026-09-14.md.
**Status:** in-progress.
**Tests run and results:** 240 passed, Ruff passed. qwen3:4b on live_dev across three valid
trials: **3/4, 2/4, 2/4**.
**Live-model results:** qwen3:4b (2.5 GB) is the best local model tested and matches or beats
qwen2.5:7b. text-correction and device-correction pass in all three trials.
lost-response-reconciliation is timing-marginal. support-read-then-service never passes.
**Known failures/limits:** Two configuration defects produced false model results. A leftover
`num_gpu` override forced qwen2.5:7b to request a 4168 MiB buffer on a 4096 MiB card, so the
13 September 2/4 at 26.54 s was measured while spilling to shared memory. qwen3 emits a think
block; with it enabled the model scored 0/4 with zero successful requests, all ReadTimeout.
Record the offload line and think setting beside every local score. Local small models are
non-deterministic against the 120-second cap on this hardware. Gemma 4 has no small variant;
the smallest tag is 12b at 7.6 GB against 4 GB of VRAM.
**Dependency or contract proposals:** None. No public schema change. No new dependency.
**Next independent task:** Run `google/gemma-4-31b-it` through the NVIDIA backend; needs
`ACCESSFLOW_NVIDIA_API_KEY`. Then baselines and ablation, then multimodal.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI disabled. Nothing pushed.

## [2026-09-14 02:20] — Claude Code
**Task:** Sweep well-known hosted models; test Gemma 4 through NVIDIA NIM.
**Changes:** Added results/MODEL_SWEEP_2026-09-14.md. No source change in this slice.
**Status:** in-progress.
**Live-model results:** `qwen/qwen3.8-27b` 4/4 at 0.91 s mean and `openai/gpt-oss-120b` 4/4
at 1.95 s mean. `openai/gpt-oss-20b` 3/4; it fails support-read-then-service on a timeout
with no rate-limit error after one successful 1.45 s request, which is the small-model
signature at hosted speed. The capacity wall for the four-slot two-step chain sits between
20 B and 27 B.
**Known failures/limits:** `qwen/qwen3.6-27b` is unusable: a 1000 output-token-per-minute
limit against plans needing 660 to 1120 output tokens, plus `400 json_validate_failed` with
an empty failed_generation. Free-tier limits are enforced per model and differ by dimension;
qwen3.8-27b and gpt-oss-120b are input-limited, qwen3.6-27b is output-limited. NVIDIA NIM is
blocked: the key lists models but every inference request returns 403 Authorization failed
across four different models. The key is well formed at 115 characters with an nvapi- prefix,
so the rejection is account-side. Gemma 4 remains untested.
**Dependency or contract proposals:** None.
**Next independent task:** Resolve NVIDIA authorization or drop it, then baselines and
ablation, then multimodal.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI disabled. Nothing pushed.

## [2026-09-14 02:55] — Claude Code
**Task:** Test `google/gemma-4-31b-it` after the NVIDIA key was corrected.
**Changes:** Updated results/MODEL_SWEEP_2026-09-14.md. No source change.
**Status:** in-progress.
**Live-model results:** The earlier 403 was a wrong key in `.env`, 115 characters instead of
70, not an account restriction. Gemma 4 31B scored 4/4 on the first run and 2/4 on the
second. It is the third independent model to complete the four-slot two-step chain.
**Known failures/limits:** Both second-run failures were latency, not planning. One scenario
timed out after a successful 13.52 s request and one ended in a 90 s read timeout with no
successful request. Request times on this endpoint ranged from 5.76 s to over 90 s for the
same work, which is free-tier queueing. Against a 120-second cap and a 15 percent latency
weight this endpoint is unsuitable for a scored run, though useful as an accuracy check.
NVIDIA NIM requires `response_format` `json_object`; without it Gemma 4 wraps JSON in
Markdown fences.
**Security note:** The working NVIDIA key was pasted into a chat transcript and should be
rotated at build.nvidia.com. It is stored only in the gitignored `.env`.
**Next independent task:** Baselines and ablation, then multimodal.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI disabled. Nothing pushed.

## [2026-09-14 03:40] — Claude Code
**Task:** Make lower-parameter models complete the two-step chain.
**Changes:** Additive `write_pending` field on `SessionView`, defaulted false. The controller
sets it from `speech_write_requested`. When a requested write is outstanding, `ModelReasoner`
adds a `complete_requested_write` next step and builds the schema with `response` typed null,
so prose is not a valid answer while the effect is unperformed. New `write_outstanding` helper.
Added results/CONTINUATION_2026-09-14.md.
**Status:** in-progress.
**Tests run and results:** 244 passed, Ruff passed, offline `scenarios/dev` 4/4.
**Live-model results:** qwen3:4b (2.5 GB, GTX 1650) went from 3/4, 2/4, 2/4 to 3/4 and 4/4.
`support-read-then-service` had failed in all three earlier trials and now passes at 78 s and
58 s, with one 100-second scenario-cap timeout. Hosted regression check on `qwen/qwen3.8-27b`
is 4/4 unchanged at 0.83 to 1.53 s per request.
**Known failures/limits:** The trace shows the earlier "omits slots" description was wrong for
qwen3:4b. Slots, tool and dependencies were correct; the model answered with the read result
instead of continuing to the write. Local runs remain latency-bound at 16 to 41 s per request
against the 120-second cap. One earlier attempt added a `write_pending` keyword to
`Reasoner.plan`, which broke 75 tests because every fake reasoner takes two arguments; the
additive view field replaced it.
**Dependency or contract proposals:** `SessionView.write_pending`, additive and defaulted.
No wire change and no new dependency. Atishay's components need no change.
**Next independent task:** Re-measure the sweep under the new contract, then baselines and
ablation, then multimodal.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI disabled. Nothing pushed.

## [2026-09-14 04:30] — Claude Code
**Task:** Speed up local inference.
**Changes:** `scripts/start-local-ollama.ps1` accepts `-FlashAttention`, `-KvCacheType` and
`-ContextLength`, and records them in `ollama-server.json`. Defaults preserve previous
behaviour. Added results/INFERENCE_TUNING_2026-09-14.md. No source or contract change.
**Status:** in-progress.
**Live-model results:** The bottleneck was placement, not the model. Only 26 of 37 layers were
on the GPU while about 1560 MiB of VRAM sat idle, so generation ran at 7.9 tok/s. Flash
attention with a q8_0 KV cache cuts the KV cache from 576 MiB to 306 MiB, which lets all 37
layers fit. Warm generation is now **38.1 tok/s**, 4.8 times faster; mean request 25.2 s to
**8.6 s**; scenario runtimes 16-59 s to **4-17 s**. Suite score unchanged at 3/4 and 4/4.
**Known failures/limits:** Do not pin `ACCESSFLOW_OLLAMA_NUM_GPU`. Verified with 37 and then
with it unset: automatic fitting selects 37/37 and reaches 37.3 tok/s, matching the pinned
result, and adapts per model. The one failure was `lost-response-status-reconciliation`
rejecting a reconciliation plan for `missing_dependency`: the status tool's `receipt`
parameter carries the controller operation id, which is not a slot, so listing it as a
dependency fails. Known contract edge, passes in most runs, worth a separate fix.
**Dependency or contract proposals:** None.
**Next independent task:** Baselines and ablation, then multimodal.
**AI tools and human modifications:** Claude Code (Opus 5). No human review recorded.
**Atishay:** No B-owned files changed. CI disabled. Nothing pushed.
