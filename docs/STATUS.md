# Implementation status

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


Workstream A remains in progress. This is implementation evidence, not an evaluated
submission.

## Current status

This section is the single authoritative statement of current state. It replaces all older
headers in this file, including the commit `fd53aca` snapshot below, which is historical.
Read this section first. The orchestrator measured every fact below on 18 September 2026, on
branch `mridul/engine`, at commit `ef58557`. Each fact quotes the command that produced it.
The repository virtualenv at `.venv` supplied the interpreter.

Branch `mridul/engine` is three commits ahead of `main`. Workstream A work is committed
there, not directly on `main`.

- **Full test suite:** 818 passed, 1 xfailed, 0 failed.
  Command: `./.venv/Scripts/python.exe -m pytest -q`.
  Earlier figures of 411, 635, 769 and 799 are historical. Do not cite them as current.
- **Remaining xfail:** one test in `tests/demo/test_app.py`, named
  `test_conflicting_frames_require_resolution_before_write`. Read finding A17-3 below before
  you interpret it. It does not prove what its reason string says.
- **Lint:** all checks passed.
  Command: `./.venv/Scripts/python.exe -m ruff check .`.
- **Offline dev suite:** 4 passed, 0 failed, 0 unscored, 0 error. Oracle pass rate 1.0.
  Command: `./.venv/Scripts/python.exe -m accessflow.cli suite scenarios/dev`.
  The report states its own limitation: developer-authored criteria and mock effects. These
  are not official-kit results and not held-out results.
- **Scenario counts.** Workstream A has **17 executable scenario files**. Workstream B has a
  **60-entry authored media catalog**. These are different artifacts. Do not add them
  together and do not use one count where the other belongs.
- **Evidence bundle:** 57 attempted runs. The quality denominator is **43 of 49**. It is not
  43 of 46.
- **Held-out planner probes:** ran once, on 16 September 2026, on `groq/qwen/qwen3.8-27b`.
  They passed 4 of 4. They are spent. They are development data now.
- **Security review status.** A corpus review ran on 16 September 2026 and reached a clean
  verdict after repairs. A review of the first Workstream B merge ran on 17 September 2026
  and found one medium and five low findings, which are listed below and are not repaired.
  A further 69 Workstream B commits, and all Workstream A work on this branch, have had no
  security review. **No full-surface review has ever run. Do not describe the current
  surface as reviewed or clean.**
- **Docker:** not installed on this machine. The container execution gate is unmeasured here.
- **Endpoint telemetry:** not re-measured. The last recorded figure is 0 of 161 traces
  carrying `config.endpoint`, in the `fd53aca` snapshot below. Treat it as unverified.

### Findings status at commit `ef58557`

The current findings record is
[reviews/MRIDUL_MERGED_AUDIT_2026-09-17.md](reviews/MRIDUL_MERGED_AUDIT_2026-09-17.md)
(A17-1 through A17-4), with the companion
[reviews/ATISHAY_MERGED_AUDIT_2026-09-17.md](reviews/ATISHAY_MERGED_AUDIT_2026-09-17.md).
Earlier records are
[reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md](reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md)
(M1 through M7) and
[reviews/MRIDUL_REAUDIT_2026-09-15.md](reviews/MRIDUL_REAUDIT_2026-09-15.md) (A1 through A9).

- **A17-1, argument authority — NOT closed. Partly mitigated, and the residual is larger
  than the mitigation.**
  - Commit `3c59f31` adds controller-only slot provenance. `Agent._user_fixed_slots` records
    the slot names a fresh-evidence proposal supplied. A tool-result replan can no longer
    change the value of a slot the user fixed. It can still set a slot the user never fixed,
    so a delegated value such as "book the first available day" continues to work.
  - Commit `ef58557` closes a bypass of that guard. The first fix keyed on the slot NAME. An
    adversarial planner avoided the fixed name completely: it created a new slot and used
    `ProposedCall.argument_slots` to steer the write's own parameter onto it. The orchestrator
    reproduced this and recorded a committed Friday effect while the `day` slot still read
    Wednesday. `_argument_dependency_error` now refuses an alias that redirects a write
    parameter whose own name is a user-fixed slot.
  - Regressions: `tests/engine/test_argument_authority.py` (2 tests) and
    `tests/engine/test_slot_provenance.py`. Both use an adversarial planner that actively
    proposes the unsafe write. A cooperative planner that refuses on its own would not prove
    the guard.
  - No contract change. The provenance state is controller-only, so `Slot` and `Snapshot` in
    `contracts.py` are untouched.
  - **Residual, confirmed by probe on 18 September 2026.** Both guards key on a SLOT NAME.
    Nothing binds a write tool's PARAMETER name to the slot name the planner chose. When the
    two differ, which is the normal case, neither guard fires. Two demonstrated bypasses:
    1. The fresh proposal names the slot `requested_day`. The tool-result replan creates a
       new slot named `day` -- the write parameter's own name, never user-fixed -- sets it to
       `Friday` and dispatches. The write commits `Friday` while `requested_day` still reads
       `Wednesday`.
    2. The same shape through `argument_slots`, aliasing the `day` parameter onto a new slot.
    The two tests in `tests/engine/test_argument_authority.py` pass only because the fixture
    in `tests/engine/test_safety.py` declares the parameter `day` AND the fixture's fresh
    proposal happens to name the slot `day`. Rename either and both tests fail open. Treat
    those tests as covering one naming coincidence, not the property.
  - **Why no controller-only fix closes this.** The attack and a legitimate delegated value
    are structurally identical: in both, a non-fresh replan creates a new slot and grounds
    the write on it. "Book Wednesday after checking the manual" and "book the first available
    day" differ only in whether the user's utterance named a day. The controller sees slot
    names the planner chose, not the utterance. The reviewer's proposed repair -- record the
    tool/parameter binding from the fresh proposal's write calls -- does not apply, because
    the documented legitimate read-then-write pattern
    (`tests/engine/test_write_authority_evidence.py:188`) puts no write call in the fresh
    proposal at all.
  - **Decision required before any further work.** Either the planner declares delegation
    explicitly, which is a shared contract change and a C3 coordination item, or any write
    grounded on a tool-origin value requires one explicit user confirmation. The second is
    controller-only and needs no agreement, at the cost of one extra turn on every delegated
    write. Neither is started.

- **A17-2, corpus harness configuration — partly closed.**
  - Commit `73f31e9` adds an explicit `corpus_root` parameter to `replay()` and `run_suite()`
    and passes it from both CLI subcommands. An explicit value wins over
    `ACCESSFLOW_CORPUS_ROOT`, which stays as a documented fallback. A missing or non-directory
    root fails once, before any scenario runs. Recorded metadata carries
    `corpus_root_configured` and `corpus_root_basename` only, never the absolute path.
  - **Still open:** no scenario retrieves a document through the normal harness. The
    plumbing is tested; end-to-end retrieval through a scenario is not. This needs a scenario
    fixture and a small team-authored corpus document. It is held pending Mridul's decision
    on whether the corpus is kept at all.

- **A17-3, conflicting frames — open, and blocked on a shared decision.**
  Ownership is not the open question. The engine and engine tests are Mridul's; the demo test
  is Atishay's. The open question is the design: whether a second frame REPLACES the first,
  contradicts it, or is an explicit device change. Nothing can be implemented before that is
  agreed. The existing xfail does not establish the safety gap its reason string claims: it
  times out at `conflict_seen.wait()`, `tests/demo/test_app.py:3725`, before reaching
  `assert not executor.calls` and `assert not executor.effects`. Verified by the orchestrator
  with `--runxfail`. Do not treat that test as a specification.

- **Open, with owner:**
  - Six security findings in the first Workstream B merge. Workstream B owns every affected
    file. Some later Workstream B commits may close some of them; nobody has verified which.
  - A2 and B0, vision worker wiring — Atishay, by Mridul's decision; see `CONTRACT_PROPOSALS.md`.
  - Matched-timing baseline — `perception/timing.py` and `turn_policy/timing_replay.py` now
    exist. Whether they supply the calibrated signal the baseline needs is not yet assessed.
  - C1 through C4 coordination items in the 17 September audits — each needs an agreed
    example and event trace before any shared schema changes.
  - Official kit adapter — blocked on the organizer. Docker — unmeasured here.
  - Submission materials: deck, video, AI disclosure and tag — untouched.


Multimodal coverage counts are unchanged from the `fd53aca` snapshot below (2 audio files
over one recording, 1 visual file blocked on A2). See
[SCENARIO_INVENTORY.md](SCENARIO_INVENTORY.md), which is current.

---

## Historical current-status snapshot: commit `fd53aca` (16 September 2026)

Superseded by the "Current status" section above. Keep this for record. Do not cite the
numbers below as current, and do not treat its "Findings status" or "Multimodal coverage"
subsections below as the present state; the section above replaces them.

Measured by the orchestrator on 16 September 2026 at commit `fd53aca` on branch
`mridul/engine`, using the commands quoted next to each fact.

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

### Findings status (as recorded 16 September 2026 at `fd53aca`; superseded above)

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

### Multimodal coverage (as recorded 16 September 2026 at `fd53aca`)

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
  which files are repeats of the same underlying workflow. The four planner probes ran once,
  on 16 September 2026, and passed 4 of 4; see "Current status" above. They are now spent
  development data, not unseen evidence, so do not run them again expecting a fresh
  measurement. The remaining gap is breadth: four text-only probes are a narrow sample, and
  there is no unseen audio or visual case.
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

- PCM activity measurements now normalize 8/16/24/32-bit input to signed 16-bit full-scale units,
  and the WebRTC path converts those widths before calling the detector. Activity frames now reject
  non-finite, negative, zero-length and out-of-order timelines. Focused audio coverage passes 45
  tests and the full branch passes 673 tests with one retained conflict example; held-out speech-quality
  measurement and hardware timing validation remain open.
- The browser adapter now translates typed `speech` and `task` interruption events, and the demo
  exposes separate Stop speaking and Stop task controls. Demo route coverage preserves session
  usability after a speech interruption; no engine or shared-contract change was needed.
- Demo media intake now enforces a monotonic 16 MiB per-session decoded-byte budget in addition to
  the 8 MiB per-file bound, so rejected decoded uploads still consume admission quota and cannot
  repeat expensive validation without limit; it also applies backpressure with a 16-item incoming
  queue. The repeated-invalid-PNG regression passes; the current demo suite has 144 passed and one
  retained conflict xfail, and live device behavior remains unverified.
- Browser input now reports malformed JSON as a recoverable `demo/input` error, and PNG validation
  rejects unknown critical chunks before a vision provider is called. The full branch passes 673
  tests with one retained conflict example; Ruff and diff checks pass.
- Failed browser media writes and unexpected validation errors now remove partial session files while
  retaining their aggregate budget admission. The full branch passes 673 tests with one retained
  conflict example; live vision and device behavior remain unverified.
- The demo now keeps the detailed event trace out of live announcements and exposes a concise
  screen-reader status region. A fresh local browser smoke confirmed the page rendered without
  horizontal overflow or console errors; the full branch remains at 673 passed with one xfail.
- Live announcements also compact untrusted message and response text to a 240-character content
  bound. A browser smoke with a 1,200-character response produced a bounded announcement while the
  full trace stayed visible; no live model or device claim is made.
- Browser sends now catch a close race after the ready-state check and report a stable transport error;
  queued-message draining also stops without a false connected announcement. A fresh browser send
  smoke completed with no console errors; the full branch remains at 673 passed with one xfail.
- The demo now exposes an explicit Restart session control that discards an active microphone stream,
  reloads client state and establishes a fresh WebSocket session. Browser smoke cleared the prior
  event trace and reconnected cleanly; no live model or device claim is made.
- The demo WebSocket now bounds both incoming and outgoing event queues at 16 items, applying
  backpressure when a browser stops reading responses. The full branch passes 673 tests with one
  retained conflict example; live model and device behavior remain unverified.
- Demo receiver status and error admission now fails closed when the bounded output queue is full,
  allowing the existing cleanup path to cancel stalled sessions instead of waiting forever. The
  output-queue saturation regression passes; full verification passes 785 tests with one retained
  conflict xfail and Ruff.
- Perception workers now bound retained source token and revision state to 64 recent keys while
  protecting active and pending work from eviction. A regression confirms twelve completed unique
  audio sources stay bounded, retained stale revisions remain suppressed, and an evicted source is
  reprocessed as new; full verification passes 786 tests with one retained conflict xfail and Ruff.
- Local perception now caps retained session worker registries at 64 entries per modality and fails
  closed when a new session would exceed that bound, avoiding unbounded worker-object retention.
  A session-capacity regression passes; full verification passes 787 tests with one retained conflict
  xfail and Ruff.
- Activity timing summaries now reject overlapping or duplicate frames before deriving pause evidence,
  while preserving adjacent frame boundaries. Focused overlap regressions pass; full verification
  passes 789 tests with one retained conflict xfail and Ruff.
- PCM resampling now applies the shared 64 MiB decoded-payload ceiling before allocating its output
  list, preventing a caller-controlled target rate from causing an oversized expansion. The focused
  regression passes; full verification passes 790 tests with one retained conflict xfail and Ruff.
- PNG validation and direct vision-provider reads now request at most one byte beyond the 8 MiB file
  bound, preventing a size-check/read race from causing an oversized allocation. Focused bounded-read
  regressions pass; full verification passes 792 tests with one retained conflict xfail and Ruff.
- Browser transcript text is capped at the 16,384-character reasoner context limit, and client-supplied
  utterance and frame identities are capped at 256 characters before they enter session state. Boundary
  regressions preserve exact-limit inputs and reject oversized values; full verification passes 796 tests
  with one retained conflict xfail and Ruff.
- Browser WebSocket frames are size-checked at 12 MiB before JSON parsing, while the existing 8 MiB
  per-file upload limit remains available with JSON overhead. Malformed and oversized frames remain
  recoverable `demo/input` errors; the full demo suite passes 143 tests with one retained xfail and full
  verification passes 798 tests with one retained conflict xfail and Ruff.
- PNG validation now requires all compressed image data chunks to be consecutive, rejecting ancillary
  data between `IDAT` chunks before a vision provider is called. The focused regression passes; full
  verification passes 799 tests with one retained conflict xfail and Ruff.
- Timed-out local perception now retains one real native-work permit per session worker until the
  underlying thread returns, so repeated timeouts cannot launch concurrent replacement calls. The
  gated three-call probe now reports one native call, peak concurrency one, and one tracked call after
  close; owned perception coverage passes 217 tests and full verification passes 807 tests with one
  retained conflict xfail and Ruff.
- The assigned JSONL perception worker now accepts `none` or `ollama` plus model, base URL and timeout
  options, constructs the agreed A-side provider and preserves its `ollama/<model>` identity through
  `LocalPerception`. A real child-process loopback regression covers a configured frame, while the
  default builder remains audio-only; full verification passes 807 tests with one retained conflict
  xfail and Ruff.
- The committed monotonic media-admission fix was reviewed with a bounded security diff scan over
  `demo/app.py`; it found zero reportable findings. Deterministic invalid-PNG repetition coverage
  confirms the quota is consumed after decoded admission and failed temporary files are removed.
- Direct WAV perception now rejects files above 8 MiB and declared PCM payloads above 64 MiB before
  validation or loading can process them. This closes the unbounded local-path seam while preserving
  the existing small fixtures; the full branch passes 673 tests with one retained conflict example.
- Browser microphone capture now caps accumulated samples so the generated WAV stays within the 8 MiB
  media boundary; reaching the cap stops capture once, reports a labeled status and uploads only the
  bounded recording. Browser layout smoke remained clean; the full branch passes 673 tests with one
  retained conflict example.
- Selected WAV and PNG files are rejected in the browser before `arrayBuffer()` when they exceed the
  8 MiB media boundary, avoiding an unnecessary client-side read while preserving the existing
  serialized send path. Browser smoke remained free of layout overflow and console errors.
- Derived timing facts now validate finite nonnegative timestamps, positive and non-overlapping activity
  windows, matching pause and active durations, and boolean timing labels before policy experiments
  consume them. Duration comparison uses a bounded absolute tolerance. Focused timing coverage and the
  full branch pass with one retained conflict example.
- Configured local audio and vision backends now reject browser placeholder paths before backend
  invocation, emit a recoverable `demo/input` error and keep the WebSocket session usable. Mock mode
  retains its explicitly labeled placeholder behavior; the full branch passes 673 tests with one xfail.
- Modality coverage metrics now reject observations with missing, blank or non-string modality labels
  before constructing a typed result, instead of leaking invalid values or failing during sorting.
- A demo startup failure in reasoner configuration now closes any perception backend that was already
  initialized before reporting the configuration error. The full branch passes 675 tests with one
  retained conflict example and two dependency deprecation warnings; Ruff passes.
- Direct PNG validation now rejects `PLTE` chunks for grayscale and grayscale-with-alpha images before
  a vision provider can receive the malformed input. Focused local-perception coverage passes 49 tests;
  the full branch passes 677 tests with one retained conflict example and Ruff passes.
- Ollama vision configuration now rejects blank and non-string grounding prompts and normalizes valid
  prompt whitespace before a request can reach the local model. The full branch passes 679 tests with
  one retained conflict example and two dependency deprecation warnings; Ruff passes.
- An explicit opt-in vision benchmark now runs the 12 committed image cases through LocalPerception and
  OllamaVisionProvider, recording backend/model/prompt metadata, hashes, source IDs, timings, captions,
  failures and token-level label recall. Offline execution reports `SKIPPED` without fabricating live
  evidence; deterministic benchmark coverage passes 3 tests and the full branch passes 682 tests with
  one retained conflict example. The live backend remains unavailable on this machine.
- An explicit `--live` probe against `ollama/gemma3:4b` processed all 12 image cases and returned 12
  classified loopback transport failures with exit code 1, zero captions and zero recall; this confirms
  the gate fails closed without fabricating live vision quality evidence.
- Direct PNG validation now rejects non-alphabetic chunk codes and lowercase reserved bytes before
  unknown data can be treated as metadata. Focused local-perception coverage passes 51 tests; the full
  branch passes 684 tests with one retained conflict example and Ruff passes.
- Live vision backend and a real multimodal benchmark on declared hardware.
- **Completed:** the assigned perception worker now accepts `none` or `ollama` with model, URL and
  timeout options, passes the configured provider to `LocalPerception`, preserves audio-only
  defaults and closes the backend at EOF. Actual child-process coverage is in
  `tests/perception/test_perception_worker.py`.
- **Completed:** repeated native perception timeouts retain one real in-flight permit per session
  worker and track the underlying work through completion; the gated regression covers the
  timeout/close lifecycle boundary.
- Voluntary feedback notes and live microphone/device validation.
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

## Historical: Workstream B checkpoint log

These entries are Atishay's dated record, merged from `atishay/perception` on 16 September
2026. They are historical. The "Current status" section at the top of this file stays the
one authoritative statement of current state.

## Workstream B — Atishay

Updated 16 September 2026.

- Multimodal end to end evidence now covers one session carrying a validated WAV and PNG through
  event_from_message, injected local ASR and vision providers, DemoPerception, and one Agent
  context. Source IDs and backend labels are preserved; the final response is informational.
- Browser event timestamps now cross the owned demo boundary on the event envelope, audio
  speech_start/speech_end values are forwarded into typed audio events, and frame timestamps reach
  image observations. The adapter still accepts the earlier payload timestamp form for compatibility.
- The multimodal regression also covers both arrival orders, a revised audio hypothesis and
  WebSocket paths: the latest transcript revision replaces the prior one while the frame remains
  in the same context, and the combined WAV, PNG and text response exposes both retained
  modalities. A browser transport regression verifies that the revised hypothesis survives the
  session route.
- Partial speech followed by a final image is covered by a write-safety regression:
  correction_pending stays true and no write tool is invoked.
- Image-only vision text that resembles a write request is also blocked: no write call or effect
  is allowed without a spoken request.
- The turn policy now treats image observations as context-only for speech cues, so captions containing
  correction or backchannel words cannot pause, complete or stop a spoken turn; a direct regression
  covers this boundary while existing text behavior remains covered.
- The owned heuristic turn policy now classifies explicit stop/cancel-leading speech as `stop`, including
  stop-speaking and stop-task wording, before final-flag completion. The controller still owns interruption
  scope and cancellation effects; focused policy coverage verifies the new decision boundary.
- The WebSocket ordering regression also covers PNG arriving before WAV; the later audio final
  retains image context in the same session.
- A session-reset WebSocket regression confirms a new connection does not inherit the prior session's
  audio or image context.
- The WebSocket image boundary also recovers from malformed PNG input with a labeled error and
  keeps the session available for a subsequent text request.
- The WebSocket input boundary also recovers from a non-object multimodal payload with a labeled
  demo/input error and keeps the session available for a subsequent transcript. Encoded uploads are
  rejected before base64 decoding when they exceed the 8 MiB raw-media budget.
- The WebSocket route also recovers from invalid envelope metadata, returning a labeled demo/input
  error for a non-finite timestamp and completing a later transcript in the same session.
- PNG ingestion now validates chunk boundaries, CRCs, legal IHDR values, IDAT presence, zlib stream
  integrity and terminal IEND structure before a frame reaches a vision backend; rejected uploads are
  removed from the session directory. A direct cleanup regression verifies invalid PNG materialization
  leaves no session file behind.
- Direct PNG validation now bounds the compressed file at 8 MiB before reading it, complementing the
  64 MiB decoded-payload limit and preventing an oversized local image from consuming unbounded input memory.
- The direct Ollama vision provider now applies the same 8 MiB image bound and a 1 MiB response bound,
  classifying oversized or unreadable bodies before request/JSON handling.
- Failed WAV uploads now remove their post-header validation materialization, and local injected
  audio backends identify themselves separately from the installed Faster Whisper path in the demo label.
  An injected backend without an identity is reported as local/unknown-audio rather than overclaimed.
  Injected vision backends without an identity, including model-only test doubles, now use
  local/unknown-vision rather than crashing or implying an Ollama model.
- A configured vision-backend failure is also covered: it emits backend_failure without a
  misleading final response.
- The Ollama vision provider normalizes syntactically invalid JSON bytes and syntactically valid
  non-object JSON roots into classified invalid JSON errors, with raw-byte, list and null response
  coverage, rejects explicit incomplete responses, and normalizes provider timeouts
  into the same stable runtime failure boundary.
- The configured vision failure is also covered through the WebSocket route: backend_failure is
  emitted and the same session completes a later text request. A malformed list response and a
  provider timeout follow the same route and are also recoverable.
- Vision quota exhaustion is covered at provider and WebSocket boundaries: the quota error becomes
  backend_failure, produces no misleading final, and the same session accepts a later transcript.
- HTTP quota responses are also normalized: a JSON error body from a 429 response is surfaced as the
  provider's classified quota failure instead of an opaque transport error.
- The WebSocket regression now exercises an HTTP 429 quota response through the configured vision provider,
  emits backend_failure, and confirms the same multimodal session accepts a later transcript.
- Audio and image adapters reject blank or non-string provider output as a classified runtime failure, so malformed
  perception cannot become a misleading empty observation.
- LocalPerception now accepts an opt-in finite timeout_s for audio and image providers. Deadline expiry is classified by modality and tested directly; the default remains unlimited for compatibility, and synchronous work already running in a worker cannot be forcibly stopped.
- Slow audio and image inference are covered at the perception boundary: replaceable providers run in workers
  while an async heartbeat remains responsive.
- An audio backend failure is also covered through the WebSocket route: backend_failure is emitted,
  then a later PNG and spoken request complete in the same multimodal session with image context retained.
- A protocol-level loopback regression now runs the actual OllamaVisionProvider HTTP path with local
  ASR in one Agent context; it verifies model, prompt, image bytes and informational output without
  claiming live model quality.
- The configured vision environment is covered at the WebSocket boundary: a loopback provider receives
  the PNG and the later response retains the returned image evidence beside the spoken question.
- The combined configured-backend WebSocket regression now calls DemoPerception.from_environment with both
  modalities configured, then checks WAV and PNG transport, backend labels, source IDs and informational output.
- In-flight frame race coverage verifies that a delayed frame 1 result cannot enter the multimodal
  context after frame 2 arrives; only the current frame is presented to the reasoner.
- The changed-frame WebSocket reproducer is a strict expected failure until the controller
  removes the prior frame from the active context.
- A strict conflicting-frame reproducer shows that contradictory visual evidence currently has no
  structured resolution state before a write; an additive provenance/conflict proposal is recorded
  for the engine owner without changing shared contracts here.
- Cross-modal in-flight coverage now proves a delayed audio observation remains usable when a newer
  frame arrives; source acceptance preserves both independent modalities in one reasoner view.
- A fresh local WebSocket run used the installed Faster Whisper base.en CPU INT8 snapshot and the
  configured OllamaVisionProvider against a loopback protocol service; in 1.326 seconds it retained the
  recognized speech and returned image evidence in the same session. Vision quality and reasoning remain unverified.
- A second composition run used the installed Faster Whisper base.en CPU INT8 snapshot for real
  audio inference and an injected vision provider; the paired context completed in 3.222 seconds.
  A fresh Chrome run also routed the speech fixture through that local backend before accepting a
  PNG in the same session. The result is mixed evidence, not a live multimodal model benchmark.
- Reusable perception metrics now provide punctuation-insensitive word error counts/rates, realtime
  factor, interval IoU and required-modality coverage; the multimodal context regression uses the
  coverage result to verify that audio and image evidence are retained together.
- A provenance-labeled 60-case scenario inventory now records the weighted split of 30 text, 18 audio
  and 12 image cases across 40 development and 20 held-out entries. All 18 WAV files and 12 inline PNG
  payloads are materialized with recorded generator, size and SHA-256 metadata; validation checks the
  assets and every case's provenance while preserving the catalog-only evidence boundary.
- An offline fake-mode replay now sends all 60 inventory cases through LocalPerception in one session and
  verifies one observation per case, preserved event/source identities and the 30/18/12 modality counts.
  The injected replay providers make this routing evidence only; live ASR, vision and reasoning quality
  remain unmeasured.
- The 18 authored WAV cases now have a live local Faster Whisper base.en CPU INT8 run with per-case
  transcripts, word edits and realtime factors recorded. Across 132 reference words, micro-WER was 0.098,
  mean realtime factor 0.158 and maximum realtime factor 0.251 on the declared Intel Core Ultra 5 125H;
  the generated fixtures do not establish human speech accuracy or task completion.
- A live vision availability preflight found no Ollama executable or running loopback service, no configured
  vision model and no hosted API key on this machine; the 12 image cases therefore remain unscored for live
  grounding. The exact preflight and activation boundary are recorded in docs/feedback/VISION_MEASUREMENTS.md.
- A mixed end-to-end replay sent all 60 scenarios through one Agent session: 60 observations and 60
  informational finals were produced, with real local ASR for 18 audio cases, injected vision for 12 images
  and mock text/reasoning for the remaining boundaries. Per-case context and backend identity are recorded
  in docs/feedback/MULTIMODAL_SCENARIO_REPLAY.md and its JSON result.
- WebRTC VAD timing was also run over all 18 audio cases at 16 kHz, 20 ms frames and aggressiveness 2:
  3,764 frames were classified, internal pause candidates appeared in 10 cases and trailing candidates
  in all 18. The result is acoustic timing evidence only and is recorded per case with the matrix.
- The weighted split now preserves the three historical held-out WAV fixtures in held-out evaluation and
  assigns three newly generated WAV fixtures to development; matrix, ASR, VAD and mixed-replay records agree
  on the 40 development / 20 held-out allocation.
- Browser base64 decoding and WAV/PNG materialization validation now run in a worker from the WebSocket
  receive path, keeping upload handling off the event loop.
- The browser demo renders untrusted multimodal event kinds and payloads through text nodes, so model or
  transcript output is displayed without interpreting markup.
- The real Chrome smoke now passes text, checked in WAV, PNG plus paired transcript, and
  microphone capture through the served AudioWorklet. A separate isolated Chrome run used the
  present Microphone Array without a fake audio-device flag and completed the real getUserMedia,
  WAV upload and mock final path. The fresh CDP run also shows the mock final carrying prior
  audio and image context, with no console or page errors or horizontal overflow.
- A current-head local headless Chrome capture at 1280x1600 shows the full demo page with no visible
  clipping, overlap or broken text; live model quality and interactive device behavior remain separate evidence gaps.
- The current demo page now gives the transcript, WAV and PNG controls explicit labels tied to their inputs; the refreshed 1280x1600 capture keeps the layout legible.
- A current-head Chrome CDP interaction drove text partial/final submission, checked-in WAV upload and PNG upload through the page; both media acknowledgments and retained audio/image context appeared in the event stream with zero console or page exceptions.
- The demo reasoner now bounds prior multimodal context to 16,384 characters while retaining the newest evidence by truncating only the item that reaches the remaining capacity. Regressions cover recent evidence, oldest-history omission, the exact bound for an oversized prior item, and request completeness.
- The demo now exposes an optional loopback Ollama JSON reasoner through `ACCESSFLOW_DEMO_OLLAMA_REASONER_MODEL`; requests are bounded with valid JSON context that drops oldest evidence first, incomplete provider responses are rejected, returned plans are strictly parsed as `PlanProposal`, provider failures remain recoverable through the Agent and a WebSocket regression covers failure followed by a later successful request. A second WebSocket regression runs configured vision plus reasoning providers with frame evidence and a later spoken request. The browser status now labels perception and reasoning backends together. The mock reasoner remains the default, and no live reasoning quality claim is made without a running local service.
- LocalPerception now gives each session one provider call plus one pending item per modality, coalesces obsolete same-session frames and same-utterance audio revisions, suppresses stale results and keeps audio/image workers independent. DemoPerception retains the vision worker for the session and closes active and queued work during WebSocket shutdown; synchronous worker threads remain non-force-cancellable.
- The demo WebSocket now serializes controller events, media statuses and recoverable input errors through one outbound sender, preventing concurrent writes from interleaving. A route regression holds a controller send open while an invalid frame is received and confirms no overlapping WebSocket sends.
- A configured WebSocket regression now exercises the real LocalPerception Faster Whisper model branch with a deterministic factory and the real OllamaVisionProvider HTTP path together. It sends text, two revised WAV hypotheses and PNG in one session, then verifies that the latest audio revision, timestamps, distinct generated event IDs, source IDs, backend labels and one informational multimodal final are retained.
- A configured recovery regression sends a valid PNG, a failing audio revision and a corrected revision for the same utterance. It verifies one classified backend failure, no stale audio observation, and a later final retaining the corrected audio beside the frame.
- A concurrent WebSocket regression keeps two browser sessions open together, carries image and audio in the first session, and verifies that neither modality can appear in a fresh transcript final from the other.
- LocalPerception now closes admission before validation can register new work, suppresses observers that finish validation after shutdown, and marks each bounded worker closed. Audio, image and transcript shutdown races plus post-close DemoPerception admission are covered; closed peers also terminate the demo sender cleanly.
- A route-level cleanup regression confirms valid uploaded WAV and PNG files exist inside the live session directory and that the directory is removed after WebSocket disconnect.
- The conflicting-frame expected failure now uses two content-distinct valid PNG payloads, asserts their Tuesday/Wednesday captions, and waits until the first reaches the reasoner before sending the second. Its remaining failure is a deterministic controller conflict-state gap rather than a perception coalescing or fixture artifact.
- Integrated-state review against origin/mridul/engine 919ed27 confirms targeted active-frame replacement and image-only informational tests pass there. That controller removes the superseded frame before planning, so the conflicting-evidence proposal still needs an additive pre-replacement comparison or provenance signal; no protected engine or contract file was changed here.
- A fresh shallow public-clone check on 16 September 2026 checked out `atishay/perception`, resolved `origin` to the shared GitHub repository and included `ATISHAY_START_HERE.md` at commit `4892c185`.
- WAV validation now reads the declared PCM frames in bounded chunks and rejects a truncated payload before audio inference; the new regression passes in the full multimodal suite.
- PNG validation now checks decompressed scanline sizing and filter bytes, including Adam7 row sizing, before an image reaches a vision provider; incomplete scanline coverage passes in the full suite.
- PNG validation now groups scanline accounting instead of materializing one entry per declared row, rejects decoded payloads above 64 MiB before decompression, and avoids an unbounded zlib flush. A huge-dimension PNG regression covers the resource boundary.
- PNG validation now requires a correctly sized palette before IDAT for indexed-color images and bounds indexed palette entries by bit depth.
- Ollama vision configuration now rejects non-string model/endpoints and non-finite, boolean or non-positive timeouts with stable ValueErrors before a request is attempted.
- Browser sends now queue up to 16 text, WAV or PNG actions while the WebSocket is connecting, flush them in order on open, and report labeled transport errors when the queue is full or the session is closed.
- Browser transcript submissions now keep one utterance ID across partial and final hypotheses, incrementing revisions in order and closing the active utterance only after its final hypothesis.
- Browser payload factories now defer transcript revisions and audio/frame identity allocation until a send is accepted or queued. Media IDs use a page-scoped monotonic sequence, preventing rapid uploads from reusing a source identity; rejected microphone uploads are reported as rejected.
- Browser event translation now rejects explicit blank or non-string utterance and frame identities while preserving generated IDs for omitted fields, so accepted multimodal observations always have a usable source identity.
- The same browser boundary now rejects coerced revision/final/text values, non-finite or boolean timestamps, and inverted speech bounds before typed events are built; valid omitted defaults remain supported.
- Browser events now carry a page-scoped monotonic envelope sequence through the adapter, preserving arrival order alongside timestamps, source IDs and revisions.
- Browser WAV, PNG and microphone actions now serialize their asynchronous reads and sends in click/stop order, so event sequencing and media identity allocation cannot be reordered by competing media operations.
- Audio and frame metadata is now validated before base64 media materialization, so rejected browser events cannot leave an orphaned session file; direct cleanup regressions cover both modalities.
- Threaded browser upload materialization is now shielded from receiver cancellation and drained before the session directory is cleaned up, so a disconnect cannot race an in-flight WAV or PNG write. A focused cancellation regression covers this boundary.
- PCM loading, energy activity, WebRTC VAD and pause-threshold boundaries now reject booleans, wrong numeric types and non-finite values with stable ValueErrors instead of leaking arithmetic or range TypeErrors.
- Energy activity now validates `AudioBuffer` sample-rate and sample-width metadata before calculating frame timing, preventing invalid manually supplied buffers from reaching division or range operations.
- Energy activity now rejects PCM buffers whose byte length ends with a partial sample instead of silently dropping trailing bytes.
- The bounded audio worker now keeps pending work per utterance key, so a newer revision for one utterance cannot discard an unrelated queued utterance; same-utterance replacement and the single active provider-call limit remain intact.
- A real local Uvicorn/WebSocket run on the current demo served a WAV, PNG and transcript sequentially in one session; it emitted media statuses and finals whose last context retained both audio and image evidence.
- A fresh current-head Uvicorn/WebSocket smoke repeated the mock route with the checked-in WAV and a valid PNG: both media acknowledgments arrived in one session, and the final retained audio and image context.
- A current-head served run also used the cached Faster Whisper base.en CPU INT8 model and a loopback Ollama vision endpoint: the speech fixture was transcribed, the PNG produced image evidence, and the final transcript retained both real audio and vision observations. This is protocol/backend evidence with mock reasoning, not a live quality benchmark.

- Final verification is 257 tests passed with 4 strict expected failures, including 108 passing demo
  tests and 133 passing perception tests; Ruff, compilation and git diff --check are clean. The browser runtime
  still uses local only websockets 17.1.
- The four expected failures record current controller integration gaps: image-only informational response,
  direct or WebSocket replacement of a prior active frame, and unresolved conflicting-frame evidence before
  a write. The owned timing-policy seam now accepts optional activity metadata while shared engine/controller
  wiring remains a pending additive proposal. Proposals and corresponding integrated-branch behavior are
  available for the engine owner; no engine or contract file was changed here.
- Evidence is mixed and still bounded: live vision quality and non mock reasoning are still
  open. Direct inspection of the existing 13–14 September captures and a current-head 1280x1600
  headless Chrome capture show no visible clipping, overlap or broken text in the inspected viewports;
  live interactive device behavior remains open.
- origin/mridul/engine was fetched at 919ed27 for integrated state review. No engine owned
  files were changed and this branch remains atishay/perception.
- An offline timing-policy replay now compares 0.4-second acoustic candidates with a 2.0-second
  baseline over the recorded held-out pause and fluent VAD timelines. It reports the short
  baseline's internal premature candidate, the long baseline's missed endpoint, and a final-
  revision-gated trailing candidate with 0.62/0.66 seconds of added wait; six focused tests and
  the full branch pass. This is prerecorded timing-policy evidence only, not live endpointing.
- After merging `origin/main` at `3c1619f`, the integrated branch passes 322 owned perception/demo
  tests with one retained conflict xfail and the full repository passes 769 tests with one xfail;
  Ruff passes. The merge introduced no conflict in Workstream B files and no protected file was
  edited by this workstream.
- A fresh 17 September live-vision preflight found no Ollama executable and a refused
  `127.0.0.1:11434` connection. The explicit 12-case `--live` gate processed all cases, returned
  12 classified transport failures with zero captions and zero label recall, and exited 1; the
  gate remains fail-closed and live vision quality is still unmeasured.
- The vision benchmark now verifies each manifest asset's declared byte count and SHA-256 before
  materialization or provider invocation. A tampered case is recorded as one per-case failure while
  the other 11 cases continue; the regression and full integrated suite pass with 770 tests and one
  retained conflict xfail.
- The opt-in vision benchmark now records the backend observed for every completed case and can
  persist its stable JSON report through an explicit `--output` path. A writer regression passes,
  and the integrated branch now passes 771 tests with one retained conflict xfail; live model
  quality remains unmeasured.
- The benchmark also rejects duplicate or blank image case IDs and blank visual labels before a
  run can produce misleading provenance or vacuous recall. The focused benchmark coverage passes
  six tests; the full integrated branch passes 772 tests with one retained conflict xfail.
- The live benchmark now records the configured per-request timeout in its report and exposes an
  explicit `--timeout` option. Invalid timeout environment values no longer break the offline
  opt-in skip path; full verification passes 774 tests with one retained conflict xfail and Ruff.
- Timing replay now selects the newest transcript revision available when each acoustic pause ends,
  so a later provisional revision cannot suppress an earlier eligible final revision. The regression
  and full verification pass 775 tests with one retained conflict xfail and Ruff.
- Vision benchmark case IDs now have to be safe filenames on both POSIX and Windows before any
  temporary asset is materialized. The focused benchmark coverage passes nine tests; full
  verification passes 776 tests with one retained conflict xfail and Ruff.
- Vision benchmark asset payloads are now bounded before base64 decoding, using the same 8 MiB
  image limit enforced by the provider. The focused benchmark coverage passes ten tests; full
  verification passes 777 tests with one retained conflict xfail and Ruff.
- Modality coverage now rejects whitespace-only required and observed labels, preventing blank
  values from entering evidence metrics. Focused metrics coverage passes 16 tests; full
  verification passes 778 tests with one retained conflict xfail and Ruff.
- Cancelled queued perception revisions now restore the prior per-source worker token and revision
  state, so an active result is not falsely suppressed and the cancelled revision can be retried.
  Focused local-perception coverage passes 52 tests; full verification passes 779 tests with one
  retained conflict xfail and Ruff.
- Demo WebSocket cleanup now inserts its end sentinel without waiting on a full input queue and
  cancels a stalled agent when that queue is saturated. The disconnect regression passes; full
  verification passes 780 tests with one retained conflict xfail and Ruff.
- Ollama vision and demo-reasoner responses now require bounded `read(limit)` support; unsupported
  response readers fail closed instead of falling back to an unbounded allocation. Focused vision
  and reasoner coverage passes 45 tests; full verification passes 782 tests with one retained
  conflict xfail and Ruff.
- Demo input admission now fails closed when the bounded agent queue is full, allowing the existing
  shutdown path to cancel a stalled agent instead of waiting forever. Two queue-lifecycle regressions
  pass; full verification passes 783 tests with one retained conflict xfail and Ruff.
- Demo sender cleanup now bounds the wait for a peer send that never returns, cancelling and gathering
  the sender before perception teardown. The sender-lifecycle regression passes; full verification
  passes 784 tests with one retained conflict xfail and Ruff.

## Still required (Workstream B, as recorded 13 September 2026)

- Broader engine race tests and validation of the normalized status reconciliation route.
- Live reasoning execution, official-kit adapter after the kit is supplied, replay and metrics.
- Held-out generated-case ASR and endpoint measurements are recorded; human speech and endpoint quality, live vision service and real multimodal
  benchmark on declared hardware.
- Manual browser/device smoke proof, a completed voluntary feedback session, demo video and final presentation assembly.
- Docker/CI verification, live vision/reasoning execution and scoring of the remaining 42 scenarios,
  reviewed disclosure and final release assembly.

No live model, official compatibility, latency or completion target is currently certified.

## Checkpoint 17 - 13 September 2026: feedback and recording safeguards

Prepared the owned feedback and presentation artifacts for later human-led validation.

- docs/feedback/SESSION_TEMPLATE.md requires voluntary participation, separate capture
  consent and anonymized notes by default.
- docs/presentation/DEMO_RECORDING_SCRIPT.md provides a 4m40s evidence-labeled sequence
  for the current mock/local boundaries.
- No participant feedback or recording was collected in this checkpoint.
- Manual browser/device smoke, engine integration and final presentation recording remain.
## Checkpoint 18 - 13 September 2026: held-out generated speech and endpoint check

Measured three newly generated voice cases after fixing the local evaluation configuration.

- Faster Whisper preserved the fluent request, repeated phrase, correction and two-part
  request through LocalPerception.observe.
- WebRTC produced no internal candidate for the fluent or repetition case.
- On the labeled 1.2 second break, the candidate overlapped the full break but included
  0.669 seconds of early acoustic margin.
- The results are held-out generated-fixture evidence only; human speech accuracy and
  endpoint quality remain unverified.
## Checkpoint 19 - 13 September 2026: opt-in local audio demo path

Added an environment-gated local audio mode to the owned browser demo.

- The default remains demo/mock.
- Setting ACCESSFLOW_DEMO_WHISPER_MODEL to an existing model path routes WAV input through
  LocalPerception and displays the local backend label.
- Text and image inputs remain demo/mock.
- A real checked-in WAV completed the WebSocket route with the cached Faster Whisper model;
  the controller emitted its informational final output.
- Browser permission/device capture and live vision remain unverified.
## Checkpoint 20 - 13 September 2026: presentation content outline

Added docs/presentation/SLIDE_OUTLINE.md as a template-neutral content draft.

- Covers the problem, failure mode, architecture, correction/timing, action safety,
  multimodal boundary, evidence and limitations.
- Ties numbers to the current generated fixtures, local model configuration and test suite.
- Marks the official template, recording, feedback, integration and release work as
  outstanding.
## Checkpoint 21 - 13 September 2026: session path isolation

Hardened the browser media boundary against client-supplied filesystem paths.

- Session WebSocket traffic now roots no-byte fallbacks in the session temporary directory.
- Existing base64 WAV/PNG validation and cleanup remain unchanged.
- The boundary has a focused regression test; no shared contract or dependency changed.
## Checkpoint 22 - 13 September 2026: local model configuration guard

Added explicit validation for the optional local model path.

- Invalid configuration is reported as demo/config before an agent starts.
- The default mock mode and valid local configuration remain unchanged.
- Demo tests cover both the error event and the valid opt-in label.
## Checkpoint 23 - 13 September 2026: opt-in local Ollama vision path

Added an optional Ollama PNG provider and environment-gated demo routing.

- The provider accepts only loopback HTTP(S) endpoints.
- PNG bytes are sent to an already-running service; no model download occurs.
- LocalPerception preserves frame identity and reports the provider backend name.
- Mocked provider and demo tests cover successful responses and configuration/service errors.
- No Ollama executable or loopback service was available on this machine; live model
  availability and vision quality remain unverified.
## Checkpoint 24 - 13 September 2026: WebSocket media protocol smoke

Verified the browser demo's validated media path end to end for base64 WAV and PNG payloads.

- The WebSocket reports the received media kind and preserved source ID after materialization.
- WAV transport reaches the mock controller and emits its expected informational final.
- PNG transport is validated and session-scoped; the current v0.1 agent requires a paired
  transcript before producing a controller final, so image-only planning remains an engine
  integration item.
- Demo tests: 18 passed; full suite: 77 passed; Ruff and git diff --check are clean.

## Checkpoint 25 - 13 September 2026: functional Chrome browser smoke

Ran the local demo through a temporary isolated Chrome session using the actual page controls.

- Text produced the visible mock acknowledgment and informational final output.
- The checked-in WAV file control produced a media-received audio status and mock final.
- The PNG file control produced a media-received frame status; the current v0.1 agent then
  produced a final after a paired transcript.
- The rendered document had no horizontal overflow in the captured viewport.
- The smoke required local-only websockets 17.1 because the committed Uvicorn dependency
  does not currently include a WebSocket runtime. This is recorded as a dependency proposal.
- Physical microphone/device capture, pixel inspection and separate console capture remain
  unverified.
## Checkpoint 26 - 13 September 2026: synthetic microphone browser smoke

Exercised the microphone controls in isolated Chrome with Chrome's synthetic audio device.

- Start entered the recording state and enabled the stop control.
- Stop closed the capture path, encoded the samples as WAV and uploaded them through the
  session WebSocket.
- The browser observed media_received=audio and the mock controller final.
- No person or physical microphone was recorded. Physical device permission, pixel inspection
  and separate console capture remain unverified.
