# Active Handoff

> Last updated by: Claude Code
> Timestamp: 2026-09-15T00:35:00+05:30
> Branch: `mridul/engine` = `main` = `ad04bca` · 254 tests and Ruff pass · **ablation work uncommitted** · CI disabled

> Before starting: read `docs/STATUS.md` "Still required" and update it before you finish.

## Current Task

Workstream A. Model selection and local inference speed are finished and documented.
The ablation is done and returned a negative result. Multimodal evidence is the next work.

## Completed this session

- **Backends.** Groq and NVIDIA NIM added behind a shared OpenAI-compatible branch keyed by
  env prefix. Ollama and Gemini unchanged. Selection stays explicit with no automatic fallback.
- **Model question answered.** `qwen/qwen3.8-27b` scores 4/4 at 0.91 s mean and is the
  recommended primary. `openai/gpt-oss-120b` is a verified 4/4 fallback on a separate
  per-model budget. See `docs/results/MODEL_SWEEP_2026-09-14.md`.
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
- **Scenario corpus is 8 of 60.** Plan calls for 30 text, 18 audio, 12 visual, split 40
  development and 20 held out.

## Next Steps

1. **Multimodal end to end.** Audio and visual are 50 percent of the hidden set at a 1.5
   multiplier and have no evidence at all. Largest unclaimed score.
2. **Fix the write-intent defect.** `qwen3:4b` never sets `write_requested`, so the
   write-continuation constraint never starts. See the open defect below. This blocks every
   local multi-step result.
3. Run the four held-out probes once, after the engine stops changing.
4. Verify Docker container execution on a Docker-capable host.
5. Official kit adapter once the organizer publishes the schema. Do not invent wire compatibility.
6. Submission assembly: deck, video of five minutes or less, AI disclosure, release tag
   `PRISM_GENAI_HACKATHON_Y2026`. Do not create the tag during ordinary development.

## Known Defects and Cautions

- **`missing_dependency` on reconciliation.** `lost-response-status-reconciliation`
  intermittently fails because the status tool's `receipt` parameter carries the controller
  operation id, which is not a slot, so listing it as a dependency is rejected. This is the
  compatibility edge recorded in the 13 September review entry.
- **Open defect: the write-continuation constraint is self-triggered.** It gates on
  `speech_write_requested`, which the controller sets from the model's own `write_requested`
  flag. `qwen3:4b` proposes the read again on every turn and never sets the flag, so the
  safeguard never starts. The controller ignores the duplicate call and emits nothing, so the
  turn stalls silently until the scenario deadline. A stall with no diagnostic is the second
  half of this defect.
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
  over the whole range before pushing and returned clean.

## Key Files Modified

- `src/accessflow/adapters/models.py` — backends, error detail, think flag, continuation rule
- `src/accessflow/contracts.py` — additive `SessionView.write_pending`
- `src/accessflow/engine.py` — sets `write_pending` on the view
- `src/accessflow/cli.py` — deadline flags, `groq` and `nvidia` choices
- `src/accessflow/evaluation/replay.py` — deadline plumbing
- `scripts/start-local-ollama.ps1` — `-FlashAttention`, `-KvCacheType`, `-ContextLength`
- `tests/engine/test_models.py` — backend, think, continuation and diagnostics coverage
- `.env.example` — Groq, NVIDIA, think and layer-placement guidance
- `src/accessflow/evaluation/scenarios.py` — `event_gaps_s` per-pair pacing
- `scenarios/live_dev/stale_read_after_correction.json`, `stale_read_after_device_correction.json`
- `docs/results/` — HOSTED_MODEL, LOCAL_REPEAT, MODEL_SWEEP, CONTINUATION, INFERENCE_TUNING, ABLATION
- `docs/handoffs/mridul.md`, `.ai-sync/context.md`
