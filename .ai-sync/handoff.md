# Active Handoff

Last updated by: Codex. Current task: merged-code validation and Samsung diagnostics.
In progress: delegated-result binding and retry latency.
Key files: diagnostic runner, runner tests, evidence reports and A-side documentation.

## Current validation checkpoint â€” 22 September 2026

Fresh rerun: **863 passed, 1 xfailed**, two dependency deprecation warnings
(63.64 seconds); Ruff passed; offline-fake development suite **4/4**.
Commands: `uv run --offline --frozen --extra dev pytest -q`,
`uv run --offline --frozen --extra dev ruff check .`, and
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.
The merged-main baseline previously measured 842 passed / 1 xfailed; the current
local Mridul branch additionally includes adapter, recovery and runner tests.
The conflicting-frame expected failure remains unresolved, not a passing safety test.

Three recorded live Qwen public text attempts: simple search **100.0**, chained
booking **56.9**, failed-read recovery **81.5**. These are individual development
scores, not task completion percentages or final benchmark results. Booking was
blocked by tool-derived argument authority; recovery succeeded but final inference
missed the normal tail window. Full evidence and provenance:
`docs/evidence/samsung-text-2026-09-22/README.md`.

Next A-side work: implement and test the proposed delegated-result binding in
`docs/DELEGATED_RESULT_BINDING.md`, then optimize bounded read recovery timing.
That spec is not implemented or certified. Coordinate MP3/vision/timing with
Atishay; no B-owned implementation changed. No new dependencies. Current work
remains local on `mridul/engine`; no release, submission or workflow dispatch.
This checkpoint supersedes current-state claims in historical sections below.

## Read-failure recovery checkpoint â€” 22 September 2026

Latest Workstream A validation: **859 passed, 1 xfailed**, with two dependency
deprecation warnings; Ruff passed; offline-fake development scenarios **4/4**.
Commands: `uv run --offline --frozen --extra dev pytest -q` (68.11 seconds),
`uv run --offline --frozen --extra dev ruff check .`, and
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.

Fixed a reproduced silence after failed read-only tools: the reasoner now gets
sanitized `tool_failures` separately from usable results, and can use the existing
one-retry allowance or explain the failure. Four new tests cover recovery,
repeated failure, the retry cap, and refusal to create write permission.
The first implementation broke three corpus invariants; separation of failures
restored all three original tests without weakening their assertions.

No Atishay-owned files changed. No live model, public Samsung score or full
security audit was run. The existing conflicting-frame xfail remains unresolved.
Next: legitimate tool-derived argument grounding and real Samsung configuration;
media/endpoint work remains coordinated with Atishay. Current work is local on
`mridul/engine`; main remains the earlier verified merge.


Last updated by: Codex. Current task: Samsung integration, Workstream A.
In progress: partial queue adapter; remaining work is listed below.
Key files modified: samsung.py, samsung_protocol.py, adapter tests and documentation.

## Samsung boundary checkpoint â€” 22 September 2026

This checkpoint supersedes older statements that the official adapter is entirely
unimplemented. Development is on `mridul/engine`, based on merged main `438b91b`.
The new queue adapter is partial; it is not full official-kit compatibility.

- Full suite: **855 passed, 1 xfailed**, two dependency deprecation warnings.
  `uv run --offline --frozen --extra dev pytest -q` (95.19 seconds).
- New adapter tests: **13 passed**. Ruff and diff checks passed.
- Supplied Samsung validator accepted all five output kinds using synthetic data.
  No public scenario scores or live inference were run in this slice.
- Added in-process runtime, translated manifests/text/corrections/results/actions,
  tail-window handling, uncertain-write status, and media-failure invalidation.
- Default entry point is text-only. MP3 assembly and real vision configuration
  are not complete. Failed media is explicit and invalidates pending writes.
- No Atishay-owned files changed. No workflow enabled, release tagged or submission made.

Next: reconcile legitimate tool-derived arguments with authority guards; verify
read-error recovery and frame-as-context behavior, then run recorded official
scenarios after real configuration. Coordinate media/C1â€“C4 seams with Atishay.
See `docs/SAMSUNG_ADAPTER.md` for configuration, limits and ownership.


Last updated by: Codex. Current task: branch integration completed.
In progress: none in this session; official adapter remains next.
Key files modified: integration note and status/handoff/AI-use records.

## Current integration checkpoint â€” 22 September 2026

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


> Last updated by: Claude Code
> Timestamp: 2026-09-18
> Branch: `mridul/engine`, three commits ahead of `main`. Current status, measured by the
> orchestrator on 18 September 2026 at commit `ef58557`: full suite 818 passed, 1 xfailed,
> 0 failed. Ruff clean. Offline dev suite 4 passed, 0 failed, oracle pass rate 1.0. The
> 19 `tests/demo/` failures recorded on 16 September are closed; Workstream B repaired
> them. Earlier figures of 384, 411, 543, 635, 769 and 799 are historical. Do not quote
> any number in this header as current except the ones on these lines. See
> `docs/STATUS.md` "Current status" for the full sourced fact list.
> Pushed to `origin/mridul/engine` at `2f91d6a` on 16 September 2026 without a security
> review. Mridul waived the review for that push. That range added a file access boundary
> in `src/accessflow/corpus.py`: an allowlist, a document name check and a resolved-path
> containment check. Corpus work has continued since that push, through commit `71b1bb5`
> (dispatch, I/O bounding and discovery fixes). None of `corpus.py`, at either commit, has
> had a security review. Whether the range through `71b1bb5` has been pushed is not recorded
> here. Run the security review before any push and before the submission tag.

> Before starting: read `docs/STATUS.md` "Still required" and update it before you finish.

## Review findings status

The Codex review (`docs/reviews/CLAUDE_REVIEW_2026-09-15.md`, audited baseline `92ead42`)
recorded its twelve findings, R1 to R12, as closed on 15 September. The later
`docs/reviews/MRIDUL_REAUDIT_2026-09-15.md` re-examined the codebase against that claim and
found several R-items still partial or open, re-numbered A1 through A9.
`docs/reviews/REAUDIT_RESOLUTION_2026-09-16.md` recorded evidence against that list. A second
audit, `docs/reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md`, then re-examined the repaired tree
and reassessed several A-numbers, adding its own findings M1 through M7. **The second audit
is the correct, current statement for anything it reassessed. Do not cite the resolution
record's verdict where the second audit narrowed or reopened it, and do not repeat "all
twelve findings closed."**

| ID | Finding | Current position |
|---|---|---|
| A1 | Clarify-then-image deadlock (was part of R2/R3/R11) | **Addressed**, confirmed by the second audit. See "Open work" below for what `SessionView` actually carries. |
| A2 | Vision options rejected by the perception worker (was R11) | **Open, blocked on Workstream B.** See "Cautions". |
| A3 | Audio task-effect oracle (was part of R11) | **Partial.** The relabeled smoke check is fine; the new clarification fixture had its own defect, tracked as M1 and fixed at commit `7b0d373`. |
| A4 | Evidence eligibility (was part of R4/R8) | **Partial, then fixed.** The 57-run cohort matched policy, but a success-then-429 sequence was misclassified: M6, fixed at commit `86655f0`. See `docs/STATUS.md` for the corrected 43-of-49 figure. |
| A5 | Portable evidence ordering (was part of R8) | **Addressed.** |
| A6 | Profile verification (was R7) | **Addressed.** |
| A7 | Contradictory current documents (was R12) | **Reopened by the second audit as M7**, because this file and `docs/STATUS.md` still disagreed after the first repair. **M7 is fixed by this update.** |
| A8a-c | Test command, malformed JSONL, relative inventory path | **Addressed.** |
| A9 | Corpus integration, scenario independence, baseline timing, release gates | **Partial.** `src/accessflow/corpus.py` has a real consumer now (M2, M3, M5 fixed at commit `71b1bb5`); action-trust and read-then-write boundaries were also fixed (M4, commit `6caa889`). It has never had a security review. Scenario independence, baseline timing and release gates remain open; see "Open work" below. |

Full evidence for the A-numbered findings is in `docs/reviews/MRIDUL_REAUDIT_2026-09-15.md`
and its reassessment in `docs/reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md`. Full evidence for
the M-numbered findings, including the unresolved `corpus.py` security-boundary items no
commit above closes, is in the second audit. This table is a pointer, not a substitute for
reading either document.

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
   repeat the same underlying workflow. `src/accessflow/corpus.py` now has a real consumer
   (`src/accessflow/engine.py` wires manifest dispatch, allowlist enforcement and bounded
   `CorpusStore` reads), fixed at commit `71b1bb5` (findings M2, M3, M5). Retrieval stays
   lexical only, with no semantic ranking, citation, size limit or installed document
   directory; see `docs/reviews/REAUDIT_RESOLUTION_2026-09-16.md`, "Scope limit of the corpus
   implementation". **`corpus.py` has never had a security review; that code is on the
   remote unreviewed.**
3. Docker execution on a Docker-capable host. Official kit adapter. Submission assembly.
   Docker is not installed on this machine, so this cannot be checked here at all.
4. Run a security review over `src/accessflow/corpus.py`. It has never been reviewed.

**Resolved, removed from this list:** the clarify-then-image deadlock (previously item 2
here). A spoken write request, a clarifying question, then the answering image now completes.
The stall was gated on `speech_write_requested` and `latest_complete`; that field no longer
exists. The controller session object now carries `write_intent_retained` and
`clarification_outstanding` as its own attributes (`src/accessflow/engine.py`) â€” these are
**not** `SessionView` fields. `SessionView` (`src/accessflow/contracts.py`) exposes only
`write_pending`, which the controller sets from `write_intent_retained` inside `_view()`;
`clarification_outstanding` does not reach the view at all. The former strict-xfail
reproduction is a passing acceptance test in `tests/engine/test_component_integration.py`
(`tests/engine/test_known_defects.py` is now empty by design; see its module docstring). This
is finding A1 in the re-audit.

**Also resolved, removed from this list:** the four held-out planner probes (previously item
3 here). They ran once, on 16 September 2026, and passed 4 of 4 on `groq/qwen/qwen3.8-27b`;
see `docs/STATUS.md` "Current status". They are now spent: development data, not unseen
evidence. Do not run them again expecting a fresh, unseen measurement.

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

- **Held-out probes are done, not in progress.** They ran once, on 16 September 2026, and
  passed 4 of 4; see "Open work" above and `docs/STATUS.md` "Current status". They were the
  only unseen data available and are now spent development data. Do not run them again and
  call the result unseen.
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
3. ~~Run the four held-out probes once, after the engine stops changing.~~ Done: they ran
   once on 16 September 2026 and passed 4 of 4. They are spent; do not run them again.
4. Verify Docker container execution on a Docker-capable host. Not possible on this machine:
   Docker is not installed here.
5. Official kit adapter once the organizer publishes the schema. Do not invent wire compatibility.
6. Submission assembly: deck, video of five minutes or less, AI disclosure, release tag
   `PRISM_GENAI_HACKATHON_Y2026`. Do not create the tag during ordinary development.
7. Run a security review over `src/accessflow/corpus.py`. It has never been reviewed, and
   corpus work landed again at commit `71b1bb5` after the unreviewed push at `2f91d6a`.

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

- `src/accessflow/adapters/models.py` â€” backends, error detail, think flag, continuation rule
- `src/accessflow/contracts.py` â€” additive `SessionView.write_pending`
- `src/accessflow/engine.py` â€” sets `write_pending` on the view; also owns
  `write_intent_retained` and `clarification_outstanding` (finding A1 fix)
- `src/accessflow/cli.py` â€” deadline flags, `groq` and `nvidia` choices, `vision_provider_requested`
- `src/accessflow/evaluation/replay.py` â€” deadline plumbing
- `scripts/start-local-ollama.ps1` â€” `-FlashAttention`, `-KvCacheType`, `-ContextLength`
- `tests/engine/test_models.py` â€” backend, think, continuation and diagnostics coverage
- `tests/engine/test_component_integration.py` â€” the clarify-then-image acceptance test
  (finding A1); `tests/engine/test_known_defects.py` is now empty by design
- `.env.example` â€” Groq, NVIDIA, think and layer-placement guidance
- `src/accessflow/evaluation/scenarios.py` â€” `event_gaps_s` per-pair pacing
- `scenarios/live_dev/stale_read_after_correction.json`, `stale_read_after_device_correction.json`
- `docs/results/` â€” HOSTED_MODEL, LOCAL_REPEAT, MODEL_SWEEP, CONTINUATION, INFERENCE_TUNING, ABLATION
- `docs/handoffs/mridul.md`, `.ai-sync/context.md`

## Historical: Workstream B handoff log

Merged from `atishay/perception` on 16 September 2026. These entries are dated history.
The header at the top of this file is the current state.

## 2026-09-14 - Codex Atishay multimodal end-to-end evidence

- **Task:** Complete the next Workstream B priority for multimodal coverage.
- **Changes:** Added the served demo/recorder-worklet.js path, focused route coverage and one
  Agent-level test for a validated WAV plus PNG sharing a context through injected local ASR/vision.
- **Status:** Full suite 81 passed; demo 22 passed; perception 43 passed; fresh Chrome CDP smoke
  passed synthetic microphone, text, WAV, PNG plus paired transcript, clean console and layout checks.
- **Limits:** Physical microphone, pixel inspection, live ASR/vision quality and non-mock reasoning
  remain unverified. No engine or contract files were changed.

## 2026-09-14 - Codex Atishay image-only controller gap

- **Task:** Make the remaining image-only multimodal gap explicit.
- **Changes:** Added a strict expected-failure demo example and an additive proposal for an
  informational evidence basis; no engine or contract files changed.
- **Status:** Full suite 81 passed, 1 strict xfailed; demo 22 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The expected failure remains until the engine owner implements and reviews the
  additive proposal. Live ASR/vision, physical capture and pixel inspection remain unverified.

## 2026-09-14 - Codex Atishay live local audio plus injected vision

- **Task:** Strengthen multimodal end-to-end evidence with the cached local ASR model.
- **Changes:** Ran synthetic_speech.wav through Faster Whisper base.en CPU INT8, paired the result
  with a validated PNG and injected vision provider in one Agent context, and recorded the run in
  docs/feedback/MULTIMODAL_E2E.md.
- **Status:** Both observations reached one context and produced an informational final in 3.222
  seconds. Vision was injected because Ollama is unavailable.
- **Limits:** This does not certify live multimodal model quality or non-mock reasoning.

## 2026-09-14 - Codex Atishay multimodal ordering coverage

- **Task:** Broaden multimodal end-to-end coverage across arrival orderings.
- **Changes:** The Agent-context test now covers audio-to-image and image-to-audio sequences.
- **Status:** Full suite 82 passed, 1 strict xfailed; demo 23 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only controller gap remains the intentional strict xfail pending the additive
  engine proposal.

## 2026-09-14 - Codex Atishay multimodal revision and frame retention

- **Task:** Cover revised speech hypotheses while retaining image evidence.
- **Changes:** Added one demo Agent test for audio revision 0 followed by revision 1 and a frame.
- **Status:** Full suite 83 passed, 1 strict xfailed; demo 24 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only controller gap remains the intentional strict xfail.

## 2026-09-14 - Codex Atishay browser local-ASR multimodal run

- **Task:** Connect local ASR evidence to the real browser transport.
- **Changes:** Chrome uploaded synthetic_speech.wav with the cached Faster Whisper backend, then
  uploaded a PNG and follow-up text in the same WebSocket session.
- **Status:** Local audio acknowledgment and transcript-bearing final passed; both media statuses,
  clean console and no overflow were observed.
- **Limits:** Image/text remained demo/mock; live vision quality, physical capture and non-mock
  reasoning remain unverified.

## 2026-09-14 - Codex Atishay changed-frame integration gap

- **Task:** Expose active-frame replacement for multimodal scenarios.
- **Changes:** Added a strict expected-failure demo example for frame 2 replacing frame 1 in the
  reasoner context; no engine-owned files changed.
- **Status:** Full suite 83 passed, 2 strict xfailed; demo 24 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only response and changed-frame behavior await engine integration.

## 2026-09-14 - Codex Atishay visible multimodal reasoner context

- **Task:** Make the browser demo response expose all retained modalities.
- **Changes:** DemoReasoner now includes prior observations; Chrome confirmed audio, image and text
  context in the visible final.
- **Status:** Full suite 84 passed, 2 strict xfailed; demo 25 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The response remains mock and informational; live vision and non-mock reasoning remain
  unverified.

## 2026-09-14 - Codex Atishay combined WebSocket context regression

- **Task:** Protect the browser-observed multimodal final with an automated route test.
- **Changes:** Added WAV, PNG and follow-up transcript coverage through one TestClient WebSocket,
  including source IDs and retained modality assertions.
- **Status:** Full suite 85 passed, 2 strict xfailed; demo 26 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only response and changed-frame behavior remain intentional xfails pending
  engine integration.

## 2026-09-14 - Codex Atishay in-flight frame stale-result coverage

**Task:** Cover a changed-device-frame race while the first vision result is still in flight.

**Changes:** Added an owned async Agent regression with a delayed frame 1 perception result. Frame 2
arrives and reaches the reasoner first; after frame 1 is released, its stale result is rejected and
never appears in a frame-bearing reasoner view.

**Status:** Focused regression passed. Expected suite counts after this change are 94 passed, 3 strict
xfailed; demo suite 35 passed, 3 strict xfailed; perception suite 43 passed.

**Notes:** This covers stale-result handling with a perception seam and makes no live vision quality
claim. No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay structural PNG validation

**Task:** Ensure malformed image payloads cannot reach the multimodal vision backend.

**Changes:** Hardened the owned PNG validator to check chunk boundaries, CRCs, legal IHDR metadata,
IDAT presence and terminal IEND structure. The demo now uses the same validator and removes rejected
materializations. Migrated image tests to real small PNG fixtures and added valid metadata, truncated,
bad-CRC and WebSocket recovery coverage.

**Status:** Full suite 98 passed, 3 strict xfailed; demo suite 36 passed, 3 strict xfailed; perception
suite 46 passed; Ruff and git diff --check clean.

**Notes:** Validation is structural and does not decode pixels or claim image understanding. No engine,
contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay configured vision WebSocket wiring

**Task:** Exercise the configured Ollama vision path through the actual demo WebSocket route.

**Changes:** Added an owned route regression that sets the vision environment configuration, runs a
loopback HTTP protocol service, uploads a real PNG, waits for the image observation, and submits a
follow-up transcript. The final contains both the service result and the spoken question.

**Status:** Full suite 99 passed, 3 strict xfailed; demo suite 37 passed, 3 strict xfailed; perception
suite 46 passed; Ruff, compilation and git diff --check clean.

**Notes:** The loopback service is a deterministic protocol stub and does not provide live vision quality
evidence. No engine, contract, lockfile or dependency manifest changes were made.


2026-09-14: Multimodal boundary follow-up committed locally on atishay/perception: failed WAV materializations are cleaned up and injected ASR receives an accurate backend label. Validation: 101 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Combined configured multimodal route regression added on atishay/perception. Validation: 102 passed, 3 strict xfailed; no protected files changed.

2026-09-14: ASR failure multimodal recovery regression added on atishay/perception. Validation: 103 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Fresh mixed runtime route evidence captured: cached Faster Whisper CPU INT8 plus loopback OllamaVisionProvider, 1.326 seconds, combined context retained. No protected files changed.

2026-09-14: PNG IDAT integrity regression added on atishay/perception. Validation: 104 passed, 3 strict xfailed; no protected files changed.
2026-09-14: Speech cue modality guard committed locally on atishay/perception. Image observations return continue with uncertainty 1.0 before speech cue matching. Full suite: 105 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Demo input parser now rejects non-object messages and payloads with ValueError handled as demo/input errors; WebSocket recovery regression passes. Full suite: 107 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Backend label fallback now reports local/unknown-audio for unidentified injected audio instead of Faster Whisper; focused and full validation passed. Full suite: 108 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Vision provider now rejects non-object JSON roots with RuntimeError invalid JSON shape; focused and full validation passed. Full suite: 110 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Configured Ollama route regression now covers malformed list JSON and same-session transcript recovery. Full suite: 111 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Ollama vision timeout regression added on atishay/perception; timeout now has explicit stable failure evidence. Full suite: 112 passed, 3 strict xfailed; no protected files changed.

2026-09-14: WebSocket session reset regression added: new connection does not inherit multimodal observations from the prior connection. Full suite: 113 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Added pre-decode encoded upload limit derived from the 8 MiB raw-media budget; oversized PNG regression passes. Full suite: 114 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Configured OllamaVisionProvider timeout regression now covers WebSocket backend_failure and same-session transcript recovery. Full suite: 115 passed, 3 strict xfailed; no protected files changed.
