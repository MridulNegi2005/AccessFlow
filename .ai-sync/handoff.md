# Active Handoff

> Last updated by: Claude Code
> Timestamp: 2026-09-16
> Branch: `mridul/engine`. Current status, measured by the orchestrator on 16 September 2026
> at commit `fd53aca`: 384 tests passed, 0 xfailed, two unrelated deprecation warnings, Ruff
> clean, offline dev suite 4/4. See `docs/STATUS.md` "Current status" for the full, sourced
> fact list; do not quote the numbers in this header past that section.
> Security review over the whole range has not run yet. Do not push before it passes.

> Before starting: read `docs/STATUS.md` "Still required" and update it before you finish.

## Review findings status

The Codex review (`docs/reviews/CLAUDE_REVIEW_2026-09-15.md`, audited baseline `92ead42`)
recorded its twelve findings, R1 to R12, as closed on 15 September. The later
`docs/reviews/MRIDUL_REAUDIT_2026-09-15.md` re-examined the codebase against that claim and
found several R-items still partial or open, re-numbered A1 through A9. **The re-audit is the
correct, current statement. "All twelve findings closed" is superseded and must not be
repeated.**

| ID | Finding | Current position |
|---|---|---|
| A1 | Clarify-then-image deadlock (was part of R2/R3/R11) | **Addressed.** `write_intent_retained` and `clarification_outstanding` replace the old `speech_write_requested` flag. See "Open work" below. |
| A2 | Vision options rejected by the perception worker (was R11) | **Open, blocked on Workstream B.** See "Cautions". |
| A3 | Audio task-effect oracle (was part of R11) | **Addressed.** |
| A4 | Evidence eligibility (was part of R4/R8) | **Addressed.** |
| A5 | Portable evidence ordering (was part of R8) | **Addressed.** |
| A6 | Profile verification (was R7) | **Addressed.** |
| A7 | Contradictory current documents (was R12) | This file and `docs/STATUS.md`, both dated 16 September, are the repair. |
| A8a-c | Test command, malformed JSONL, relative inventory path | **Addressed.** |
| A9 | Corpus integration, scenario independence, baseline timing, release gates | **Open, remaining scope.** |

Full evidence for each row is in `docs/reviews/MRIDUL_REAUDIT_2026-09-15.md`. This table is a
pointer, not a substitute for reading it.

## Open work

1. **Vision is blocked on Workstream B (finding A2).** The vision adapter, CLI options,
   fixture and scenario are committed. The perception worker needs one additive parameter to
   pass a provider to `LocalPerception`. `AGENTS.md` places `src/accessflow/adapters/` in
   Workstream A, but Mridul deliberately assigned this one file,
   `src/accessflow/adapters/perception_worker.py`, to Atishay on 15 September, overriding the
   directory rule for that file only. The request is in `docs/CONTRACT_PROPOSALS.md`. The
   path was measured once with a temporary local edit that is now reverted; the result
   document, `docs/results/VISION_E2E_2026-09-15.md`, is marked blocked and not reproducible
   from this checkout.
2. **Corpus is 17 files, 10 distinct tool sets, 2 audio, 1 visual.** See
   `docs/SCENARIO_INVENTORY.md`, which is generated from the files and lists which files
   repeat the same underlying workflow.
3. Held-out probes have still never run. Run them only after the request contract settles.
4. Docker execution on a Docker-capable host. Official kit adapter. Submission assembly.
   Docker is not installed on this machine, so this cannot be checked here at all.

**Resolved, removed from this list:** the clarify-then-image deadlock (previously item 2
here). A spoken write request, a clarifying question, then the answering image now completes.
The stall was gated on `speech_write_requested` and `latest_complete`; that field no longer
exists. `SessionView` now carries `write_intent_retained` and `clarification_outstanding`
(`src/accessflow/engine.py`), and the former strict-xfail reproduction is a passing acceptance
test in `tests/engine/test_component_integration.py` (`tests/engine/test_known_defects.py` is
now empty by design; see its module docstring). This is finding A1 in the re-audit.

## Cautions

- **Perception worker ownership is resolved, not a blanket Workstream B rule.** `AGENTS.md`
  places `src/accessflow/adapters/` in Workstream A. `src/accessflow/adapters/perception_worker.py`
  is the one deliberate exception: Mridul assigned its vision-provider wiring to Atishay on
  15 September, overriding the directory rule for that file only. See the ownership note in
  `docs/CONTRACT_PROPOSALS.md`. Everything else under `src/accessflow/perception/`,
  `src/accessflow/turn_policy/`, `demo/`, `tests/perception/` and `tests/demo/` remains
  Atishay's untouched territory; raise a proposal in `docs/CONTRACT_PROPOSALS.md` before
  editing any of it, including the worker file.
- Subagents have twice left `find /` scans running for half an hour. Sweep for stray
  `find.exe` and `bash.exe` after every agent finishes.
- Regenerate `MODEL_COMPARISON.md` and `SCENARIO_INVENTORY.md` with their scripts. Do not
  hand-edit below the generated marker, and do not rewrite line endings by hand.
- Answer model questions from `docs/results/MODEL_COMPARISON.md`, never from memory.

## Current Task

Workstream A. Model selection and local inference speed are finished and documented.
The ablation is done and returned a negative result. Multimodal evidence is the next work.

## Completed this session (dated 14-15 September 2026, historical)

- **Backends.** Groq and NVIDIA NIM added behind a shared OpenAI-compatible branch keyed by
  env prefix. Ollama and Gemini unchanged. Selection stays explicit with no automatic fallback.
- **Model question answered.** `qwen/qwen3.8-27b` is the primary: 6/6 across every
  `live_dev` fixture on 15 September at 0.83 s to 0.99 s per request, with no HTTP error.
  It requires `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`; without it Groq refuses every request at
  admission because the adapter sends no `max_tokens`. `openai/gpt-oss-120b` is the fallback
  and needs no cap. Read `docs/results/MODEL_COMPARISON.md` for any model question and
  regenerate it with `scripts/model_scoreboard.py`. Never quote model scores from memory.
- **Write-continuation constraint.** While a requested write is outstanding the planner sends
  a `complete_requested_write` step and types `response` as null, so prose is not a valid
  answer. `qwen3:4b` went from never passing `support-read-then-service` to 4/4 overall.
  Additive `SessionView.write_pending`, defaulted false, so every existing reasoner and fake
  stays valid. See `docs/results/CONTINUATION_2026-09-14.md`.
- **Local inference tuned.** Generation 7.9 to 38.1 tok/s, mean request 25.2 s to 8.6 s,
  scenario runtimes 16-59 s to 4-17 s against a 120 s cap. Start the server with
  `-FlashAttention 1 -KvCacheType q8_0`. See `docs/results/INFERENCE_TUNING_2026-09-14.md`.
- **Diagnostics.** Failed requests now record the HTTP status code and bounded provider error
  text. `--request-timeout` and `--inference-timeout` replace a hard-coded 25 s deadline.
- **Ablation complete, negative result.** `--disable dependency_invalidation` makes
  `_invalidate_dependencies` a no-op and emits `ablation_skipped_invalidation`. Twelve Groq
  runs across two new live fixtures: control 3/3 and ablated 3/3 on both, with identical
  committed effects. The mechanism is correct and observable, but it changes no task outcome
  for a strong model. Do not claim that wrong effects appear without it. See
  `docs/results/ABLATION_2026-09-15.md`.
- **Two live fixtures added.** `stale_read_after_correction` and
  `stale_read_after_device_correction` place a correction after a read returns, with no write
  in flight, so `_cancel_writes` cannot hide the mechanism under test.
- **`Scenario.event_gaps_s` added.** One uniform `event_spacing_s` caps at 5 seconds and
  cannot place a correction after a tool result when a local plan takes 12 to 14 seconds.
- Registration is complete.

## In Progress

- **Held-out probes unused.** Four independently authored planner probes exist, have never been
  run, and their labels have never been read. This is the only unseen data available.
- **Scenario corpus is 17 files, 10 distinct tool sets** (2 audio, 1 visual, 15 transcript).
  See `docs/SCENARIO_INVENTORY.md` for the full breakdown. The plan calls for 30 text, 18
  audio, 12 visual, split 40 development and 20 held out; the corpus is well short of that on
  every axis.

## Next Steps

1. **Multimodal end to end.** Audio and visual are 50 percent of the hidden set at a 1.5
   multiplier and have thin evidence: 2 audio files over one recording, 1 visual file that
   cannot run through the process adapter (finding A2). Largest unclaimed score.
2. **Fix the local write-intent defect.** `qwen3:4b` never sets `write_requested`, so the
   write-continuation constraint never starts locally. See "Known Defects" below. This is a
   local-model planning gap, separate from the clarify-then-image deadlock (A1), which is
   fixed. It blocks every local multi-step result.
3. Run the four held-out probes once, after the engine stops changing.
4. Verify Docker container execution on a Docker-capable host. Not possible on this machine:
   Docker is not installed here.
5. Official kit adapter once the organizer publishes the schema. Do not invent wire compatibility.
6. Submission assembly: deck, video of five minutes or less, AI disclosure, release tag
   `PRISM_GENAI_HACKATHON_Y2026`. Do not create the tag during ordinary development.

## Known Defects and Cautions

- **Local-model write-intent gap (open, distinct from the fixed A1 clarify-then-image
  deadlock).** The write-continuation constraint gates on the model's own `write_requested`
  flag. `qwen3:4b` proposes the read again on every turn and never sets the flag, so the
  safeguard never starts. The controller ignores the duplicate call and emits nothing, so the
  turn stalls silently until the scenario deadline. A stall with no diagnostic is the second
  half of this defect. This has not been re-verified against the current engine fields
  (`write_intent_retained`, `clarification_outstanding`) in this update; treat its current
  status as unverified rather than assume it still reproduces unchanged.
- **Pin `ACCESSFLOW_OLLAMA_NUM_GPU=37` for `qwen3:4b` on the GTX 1650.** Automatic fitting is
  not dependable. Ollama holds a 1024 MiB free-memory reserve and drops to 29/37 layers when
  full offload does not clear it. The 14 September auto-fit result cleared the reserve by
  17 MiB. Do not put the pin in `.env`; it is correct for exactly one model. See the
  15 September correction in `docs/results/INFERENCE_TUNING_2026-09-14.md`.
- **Three earlier results were infrastructure defects, not model failures.** A stale `num_gpu`
  pin, a hard-coded 25 s deadline, and an unsuppressed reasoning think block each produced
  scores that read as planning failures. Any older trace showing `backend_failure` is
  unmeasured rather than wrong. Record the offload line and think setting beside every local score.
- **Free-tier limits are per model and differ by dimension.** Groq throttles `qwen3.8-27b` on
  input tokens at 7000 per minute and `qwen3.6-27b` on output tokens at 1000 per minute. Pace
  one scenario per 55 to 95 seconds.
- **Network access is not guaranteed.** The Theme 5 guide never states that the evaluation
  environment has outbound network. Keep the local backend working; a hosted-only submission
  scores zero if the harness is sandboxed.
- **Secrets.** `.env` holds Groq and NVIDIA keys and is gitignored; no key is in any tracked
  file. The NVIDIA key was pasted into a chat transcript and should be rotated.
- **CI stays disabled.** Do not enable or dispatch the workflow.
- **No B-owned files were changed.** Atishay `871c8cf` is merged unmodified; his WebRTC VAD
  keeps `webrtcvad` as a lazy optional import, so no lockfile change was needed.
- **Append-only logs now use a union merge driver.** `.ai-sync/context.md` and
  `docs/AI_USE_LOG.md` concatenate both sides automatically. Never add a rewritten-in-place
  file such as `docs/STATUS.md` to that list.
- `main` and `mridul/engine` both sit at `ad04bca` and are pushed. Security review was run
  over the whole range before pushing and returned clean. Branch `mridul/engine` has since
  advanced locally past `fd53aca`; the push/security-review state above is not re-verified as
  part of this update and should be re-checked before the next push.

## Key Files Modified

- `src/accessflow/adapters/models.py` — backends, error detail, think flag, continuation rule
- `src/accessflow/contracts.py` — additive `SessionView.write_pending`
- `src/accessflow/engine.py` — sets `write_pending` on the view; also owns
  `write_intent_retained` and `clarification_outstanding` (finding A1 fix)
- `src/accessflow/cli.py` — deadline flags, `groq` and `nvidia` choices, `vision_provider_requested`
- `src/accessflow/evaluation/replay.py` — deadline plumbing
- `scripts/start-local-ollama.ps1` — `-FlashAttention`, `-KvCacheType`, `-ContextLength`
- `tests/engine/test_models.py` — backend, think, continuation and diagnostics coverage
- `tests/engine/test_component_integration.py` — the clarify-then-image acceptance test
  (finding A1); `tests/engine/test_known_defects.py` is now empty by design
- `.env.example` — Groq, NVIDIA, think and layer-placement guidance
- `src/accessflow/evaluation/scenarios.py` — `event_gaps_s` per-pair pacing
- `scenarios/live_dev/stale_read_after_correction.json`, `stale_read_after_device_correction.json`
- `docs/results/` — HOSTED_MODEL, LOCAL_REPEAT, MODEL_SWEEP, CONTINUATION, INFERENCE_TUNING, ABLATION
- `docs/handoffs/mridul.md`, `.ai-sync/context.md`
