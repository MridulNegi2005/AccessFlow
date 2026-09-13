# Active handoff

Last updated by: Codex (2026-09-13, focused argument dependency review)

## Current Task
STOPPED at user request. Do not resume until explicitly requested. Workstream A remains incomplete. B checkpoint 2a4372a integrated unchanged.
Improve actual model planning accuracy and dependency enforcement. CI must remain disabled.

## In Progress
224 tests and Ruff pass (two existing TestClient warnings). Actual Gemma suite 0/4;
explicit Qwen2.5:3b original and guided prompt runs each 1/4 on known text cases.
All failures retained. Qwen's invented tool names and repeated write instead of status
query remain task failures. New controller guards reject untracked/contradictory arguments
and preserve retry identity across model nonce changes. Optional argument_slots maps aliases.
Model generation now binds exact tool names and read-only choices during unresolved writes.
Focused review found no bypass or crash within the documented contract; direct constants are
top-level by design and nested/$ref forms fail closed. If read/status manifests are allowed
to declare idempotency_parameter, that field is overwritten with the status call identity,
so it cannot target the original operation; current contract/tests do not explicitly forbid it.
Portable runtime/models are in D:\AccessFlow-LocalRuntime; server is now stopped
after the terminal measurement. No background model work remains.
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

## [2026-09-13 18:47] — Codex
**Task:** Safely stop at the user's explicit request.
**Changes:** Saved final Qwen report/traces. Unloaded models and stopped verified Ollama process; no listener on11435 or live model-check process remains. All child agents completed.
**Status:** stopped by user; project incomplete. Do not resume until user requests it.
**Notes:** Engine commit3e24c06 pushed to mridul/engine;224 tests/Ruff passed. Actual guarded Qwen suite2/4: corrected-device and lost-response recovery pass; support omits slots, text correction leaves completion/write flags false. Independent planner probes remain unrun/unread. Review wrote only sync notes during live run; source code stayed at3e24c06, so dirty-worktree flags in raw evidence reflect docs only. CI remains disabled. Next on explicit resume: address incomplete model plans, then unseen probes and remaining Workstream A gates.

---

## [2026-09-13 20:45] — Claude Code
**Task:** Add a Groq hosted reasoning backend for planner accuracy testing.
**Changes:** `JsonBackend` gains a `groq` branch beside `ollama` and `gemini`; CLI accepts
`--backend groq`; `.env.example` documents the new variables. Usage metrics are recorded per request.
**Status:** adapter complete and tested; live comparison blocked on an API key.
**Notes:** 231 tests and Ruff pass. End-to-end CLI warmup verified against a Groq-shaped local stub.
No key exists on this machine, so no accuracy result is claimed. Next: set `ACCESSFLOW_GROQ_API_KEY`
and run the live_dev suite against the preserved gemma3 0/4 and Qwen 2/4 traces. No B-owned files
changed. CI remains disabled. Nothing pushed.

---

## [2026-09-14 00:35] — Claude Code
**Task:** Hosted Groq comparison against preserved local baselines.
**Status:** Paced hosted run scored 4/4 on live_dev with Groq `qwen/qwen3.8-27b`.
**Notes:** Local baselines were gemma3:4b 0/4, qwen2.5:3b 2/4, qwen2.5:7b 2/4. Mean request
0.91 s against 10.06 s and 26.54 s locally. Batched runs scored 3/4 and 2/4 purely from
HTTP 429 free-tier throttling at 7000 input tokens per minute, not planning errors. Keep the
local backend working: the official guide never states that the evaluation environment has
outbound network access. Next: backend policy decision, then multimodal end to end.
235 tests and Ruff pass. No B-owned files changed. CI disabled. Nothing pushed.

---

## [2026-09-14 01:30] — Claude Code
**Task:** Lightweight local model repeat trials.
**Status:** qwen3:4b scored 3/4, 2/4, 2/4 across three trials; best local model tested.
**Notes:** Found two config defects that faked model failures: a leftover num_gpu override made
qwen2.5:7b spill to shared memory, and qwen3's think block caused 0/4 with zero successful
requests. ACCESSFLOW_OLLAMA_THINK now controls the latter. Local models are non-deterministic
against the 120-second cap on this hardware. Gemma 4 has no small variant (12b/7.6 GB minimum),
so it must be tested hosted; NVIDIA NIM backend added and awaiting a key. 240 tests and Ruff
pass. No B-owned files changed. CI disabled. Nothing pushed.

---

## [2026-09-14 02:20] — Claude Code
**Task:** Hosted model sweep.
**Status:** Two models reach 4/4: qwen/qwen3.8-27b at 0.91 s and openai/gpt-oss-120b at 1.95 s.
**Notes:** gpt-oss-20b scores 3/4 and fails the four-slot two-step chain, so the capacity wall
sits between 20 B and 27 B. qwen3.6-27b is unusable at 1000 output tokens per minute and also
fails JSON validation. Free-tier limits are per model and differ by dimension. NVIDIA NIM is
blocked by a 403 on every inference call while model listing succeeds; the key is well formed,
so the cause is account-side and Gemma 4 remains untested. No B-owned files changed. CI
disabled. Nothing pushed.

---

## [2026-09-14 03:40] — Claude Code
**Task:** Write-continuation constraint for lower-parameter models.
**Status:** qwen3:4b reached 4/4 locally; it had never passed support-read-then-service before.
**Notes:** The trace showed the failure was continuation, not extraction: correct slots and a
correct read, then the model answered with the read result instead of calling the write tool.
`SessionView` gains an additive `write_pending` field, defaulted false. While a requested write
is outstanding the planner sends a `complete_requested_write` step and types `response` as null,
so a tool call or clarification are the only valid answers. Hosted qwen3.8-27b stays 4/4.
244 tests, Ruff and the offline dev suite pass. No B-owned files changed. Nothing pushed.

---

## [2026-09-14 04:30] — Claude Code
**Task:** Local inference tuning.
**Status:** Generation 7.9 to 38.1 tok/s; mean request 25.2 s to 8.6 s.
**Notes:** Only 26 of 37 layers were on the GPU while about 1560 MiB of VRAM sat idle. Flash
attention plus a q8_0 KV cache frees enough room for full offload. Start the server with
`-FlashAttention 1 -KvCacheType q8_0`. Do not pin ACCESSFLOW_OLLAMA_NUM_GPU: automatic fitting
now selects 37/37 and adapts per model, while a stale pin once made qwen2.5:7b spill into
shared memory. Scenario runtimes are now 4-17 s against a 120 s cap. No B-owned files changed.
Nothing pushed.

---
