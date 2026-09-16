# AccessFlow: Mridul / Claude follow-up audit

Date: 15 September 2026  
Reviewed checkout: `mridul/engine`, commit `30ed402`  
Previous audit baseline: `92ead42`  
Previous report: [CLAUDE_REVIEW_2026-09-15.md](CLAUDE_REVIEW_2026-09-15.md)  
Separate teammate report: [ATISHAY_AUDIT_2026-09-15.md](ATISHAY_AUDIT_2026-09-15.md)

## Verdict

Claude made substantial, useful repairs. The claim that **all twelve findings are closed is not supported by this checkout**. Seven original findings are addressed within their tested scope; five remain partial. There are also newly reproduced defects and incomplete integration paths below.

The engine now validates each generated plan against its actual dynamic schema, scopes write continuation to a request, bounds no-progress recovery, and exports normalized provider diagnostics. Those are meaningful improvements. Keep them. This audit is not a recommendation to rewrite the engine or change the chosen Qwen model.

The immediate priorities are the clarification/image deadlock, the broken vision-worker invocation, the test collection regression, and misleadingly permissive evaluation criteria. More model benchmarking should follow these repairs, rather than compensate for them.

## Scope and evidence limits

- This was a local, review-only audit of code, committed documents, tests and existing traces. No implementation, tests, dependencies, credentials, CI triggers, branches or remote repositories were changed.
- Only this report and the separate Atishay report are new deliverables. Historical audit and handoff files are preserved so the reviewed claims remain inspectable.
- No new hosted inference, ASR inference, vision inference, model downloads, Docker runs, official-kit runs or participant sessions were performed. Existing live results are attributed to their recorded runs, not to this audit.
- The checkout was clean on entry. Remote tracking references were not refreshed, so this is a judgment about `30ed402`, not an assertion about a newer GitHub or teammate checkout.
- Temporary offline probes used disposable files and mocks. An oracle mutation probe below changes the evidence supplied to a scoring function; it does not mean the controller actually performed the substituted actions.
- Severity: **P1** blocks a central behavior or materially misleads an acceptance claim; **P2** is a bounded correctness, reproducibility or usability defect; **P3** is lower-priority cleanup. These are project priorities, not security severity ratings.

## What was verified

| Command / probe | Observed result |
|---|---|
| `uv run --offline --frozen --extra dev python -m pytest -q` | **328 passed, 1 xfailed**, two existing TestClient deprecation warnings; 29.34 s |
| `uv run --offline --frozen --extra dev pytest -q` | **Collection fails** in two test modules: `ModuleNotFoundError: No module named 'scripts'` |
| `uv run --offline --frozen --extra dev ruff check .` | Pass |
| `uv run --offline --frozen --extra dev python -m pytest tests/engine/test_known_defects.py --runxfail -q` | **1 failed**, clarification followed by image times out |
| Worker launched with the newly exposed vision option | Exit 2, `unrecognized arguments: --vision-provider ollama`; no model loaded |
| Current audio oracle evaluated against altered independent effects | Passes with **zero effects** and with **two wrong-time effects** |
| Scoreboard reading committed evidence bundle | 57 records, 43 passes, **57 scored**; contradicts documented quality exclusions |
| Evidence copied to a temporary directory with checkout-like replacement mtimes | Latest selection changes in 6/21 model/scenario groups, including 2 pass/fail changes |
| Profile verification expression applied to an existing replay trace | `KeyError: 'reasoner_evidence'`, because it selects the last output row |

These commands used the existing Python 3.11 development environment and locked dependencies. They are not fresh-machine or Linux CI certification.

## Status of the original twelve findings

“Addressed” means the original defect has a credible implementation fix and passing relevant offline coverage. It does not prove every possible variant or establish live model quality.

| Original ID | Status now | Assessment |
|---|---|---|
| R1: per-request schema and false completion | **Addressed for original reproduction** | `ModelReasoner.plan` validates the exact generated schema locally, including alternative backends. The controller guards final prose while a recognized write remains owed. `tests/engine/test_r1_schema_enforcement.py` covers the original bypass. This is not a universal proof that arbitrary generated prose is factually true. |
| R2: request-scoped continuation | **Addressed for original reproduction** | `ToolCall.request_id`, `SessionView.active_request_id`, `write_outstanding` and controller checks prevent an old request's write from satisfying a new request. A tool-result replan no longer erases recognized intent. The related clarification/image lifecycle remains broken: A1. |
| R3: forced-null stall / bounded progress | **Addressed for tested proposal outcomes** | The schema requires a useful alternative when needed; controller no-progress paths share a bounded recovery budget. `test_no_progress.py` covers empty plans, repeated calls, bad dependencies, pending calls and interruption during recovery. This does not close A1, where readiness prevents the intended continuation. |
| R4: chronology and scoreboard correctness | **Partial** | Recorded timestamps, disclosed mtime fallback, null-oracle handling and duplicate-run reporting are improvements. Portable ordering, eligibility consistency and malformed-record resilience still need A4/A5/A8. |
| R5: provider-body leakage into exported telemetry | **Addressed for current error export** | Allowlisted error types/categories and numeric quota extraction replace raw provider bodies in `evidence()`. Raw details remain explicitly local-only. Passing diagnostic tests support the fix. Historical raw traces must still be sanitized before publication; full interaction traces are not content-free telemetry. |
| R6: ledger receipt dependency | **Addressed for original and alias regressions** | The argument validator permits an unaliased parameter dependency when its value matches an unresolved ledger operation, while retaining slot/alias validation. The latest commit fixes matching the parameter name instead of the alias target. Relevant reconciliation and argument tests pass. Recorded live 8/8 is historical evidence, not a rerun by this audit. |
| R7: reproducible model profiles | **Partial** | Named hosted Qwen and local Qwen profiles now exist. Their verification instruction fails, some resolved values are not exported as promised, and fallback setup is incomplete: A6. |
| R8: portable evidence | **Partial** | 57 sanitized, indexed traces are now committed. This is a real improvement. They are a defined text/Groq subset, not all audio, vision, local or ablation evidence. Legacy ordering does not survive checkout reliably: A5. |
| R9: overbroad ablation claims | **Addressed as a claims correction** | The report narrows the cohort and withdraws unsupported claims. This closes the documentation overclaim, not the unfinished matched timing-baseline experiment. |
| R10: non-finite gaps / timeouts | **Addressed for audited inputs** | Scenario and CLI validation reject NaN/infinity and invalid gaps; relevant tests pass. This is not a claim that every public numeric constructor in the application is hardened. |
| R11: actual multimodal and corpus integration | **Partial** | One audio scenario now has existing real-ASR/real-reasoner/mock-effect traces. A PNG fixture and provider exist, but the committed worker route is broken. Clarify/image still fails, corpus is unused and timing evidence remains incomplete: A1/A2/A3/A9. |
| R12: contradictory current documents | **Partial** | Contract documentation improved substantially, including error codes and request fields. Current status, handoff, inventory and vision ownership still contradict each other: A7. |

## A1 — P1: clarification followed by an image still cannot complete the requested write

**Owner:** Mridul; controller state and authorization lifecycle.  
**Evidence:** `src/accessflow/engine.py`, especially `_apply` around lines 425–471; `tests/engine/test_known_defects.py:17–40`.

Reproduction already exists in the repository:

1. Speech requests a write: “Book the date shown in this image.”
2. The first proposal recognizes `write_requested=True` but asks “Which date is shown?”
3. An image supplies the missing date and a later proposal attempts to complete the request.
4. No final completion arrives. Running the test with `--runxfail` independently reproduced the timeout.

The first clarifying plan couples recognized write intent to immediate readiness: `speech_write_requested` becomes false because clarification is present. Later visual evidence cannot supply spoken authorization on its own. The result is a request that the user authorized in principle but which the controller cannot resume after the missing evidence arrives. The existing strict xfail is honest documentation of an open defect; it is not a passing acceptance result.

**Requested repair:** represent the distinction between retained user intent, unresolved required information, and permission to dispatch now. Clarification should block a write until resolved, without deleting the user's scoped request. An answering image may fill missing evidence for that same active request; it must not independently authorize a new write or revive a canceled/completed request.

Do not fix this by setting `speech_ready=True` for every image, trusting an image's `write_requested` flag, removing authorization checks, or deleting the xfail test.

**Acceptance checks:**

- Existing test passes without xfail; exactly one appropriate mock effect and an honest final result.
- Clarification followed by a spoken answer also completes.
- Unrelated or ambiguous image leads to another clarification, not a write.
- Partial speech, unresolved correction, explicit task cancellation and already-finished request do not gain write authority from a later image.
- Rapid replacement frames and late perception results still honor source/revision freshness.
- A request that remains impossible to complete has an explicit waiting/clarification/error state rather than unexplained silence until the scenario deadline.

## A2 — P1: the CLI advertises vision options that the subprocess rejects

**Integration sites:** `src/accessflow/cli.py:35–39,73–82`, `src/accessflow/adapters/perception_worker.py:30–33,67–70`, `src/accessflow/adapters/vision.py`.

The parent CLI forwards `--vision-provider ollama` and optional model/URL flags through `ProcessPerception.worker_args`. The child parser accepts only `--model-path`, and `_serve` constructs `LocalPerception` without its existing `vision_provider` injection.

Offline reproduction, which exits before inference:

```powershell
uv run --offline --frozen --extra dev python -m accessflow.adapters.perception_worker `
  --model-path audit-nonexistent-model --vision-provider ollama
```

Observed: exit 2, `unrecognized arguments: --vision-provider ollama`.

The recorded vision experiment is explicitly documented as using a temporary edit that was subsequently reverted. Credit it as a feasibility experiment. It does not establish that the submitted checkout supports the command. The top-level configuration can report a selected vision model even though the child never accepts the configuration.

**Ownership conflict to resolve explicitly:** `AGENTS.md` assigns all `src/accessflow/adapters/` to Mridul. `.ai-sync/handoff.md`, `docs/CONTRACT_PROPOSALS.md` and the vision result document call this particular worker Atishay-owned. The repository therefore contains conflicting instructions. Under the declared directory ownership, this is A-side integration using an already available B-side constructor seam. Do not put it on Atishay's mandatory fix list or silently change his perception implementation. Confirm/document any actual ownership transfer before implementing against the conflicting handoff.

**Requested repair after ownership is settled:** wire the provider into the existing worker constructor, keep the default no-vision path intact, propagate model/URL/deadline configuration consistently, and retain process cancellation, stdout isolation and generic error handling. Resolve timeout behavior at the parent and provider layers rather than exposing an option that is ignored.

**Acceptance checks:**

- Offline test starts the actual child entrypoint and verifies parser/constructor wiring, not only a direct provider unit test.
- Default audio-only invocation remains supported.
- Explicit vision configuration yields a frame-sourced observation with no canned caption substitution.
- Invalid provider/configuration and backend failure produce bounded, truthful errors.
- Existing worker lifecycle/cancellation tests remain green.
- A subsequent explicitly scheduled live run succeeds from the committed code, records the real backend and produces the correct mock effect. Preserve the old temporary-edit result as historical.

## A3 — P1: the audio task oracle can pass an incorrect or absent appointment

**Evidence:** `scenarios/live_dev/audio_correction.json`, `src/accessflow/evaluation/oracle.py:29–78`, `docs/results/AUDIO_E2E_2026-09-15.md`.

The scenario asks for a service appointment, but its expectation checks only confirmed `day=Wednesday` and `final_basis=confirmed_tool_effect`. It omits `effects` and the appointment hour. The tool requires a 24-hour `HH:MM` value; the recording says “at five,” without AM/PM or a declared default.

The existing traces record real ASR and Qwen-backed reasoning, followed by mock appointment effects at `17:00`. That is useful ingestion/integration evidence. It does not establish that `17:00` was the intended authorized time.

**Independent mutation check:** using the actual run's output rows unchanged, calling `evaluate_task` with the current expectation returns `passed=True` both for `effects={}` and for two substituted Wednesday appointments at `03:00`. This proves the current oracle cannot detect those failures. It does not assert that those effects occurred in the live run.

**Requested repair:**

1. Decide what this fixture measures. If it is an ASR/plumbing smoke test, label its pass as such rather than full booking correctness.
2. For a task-completion fixture, assert the independent executor effects, exact relevant arguments, count and final state. The generic oracle already supports exact effect checks; the fixture must use them.
3. Resolve ambiguous time through clarification or explicit scenario context. Do not silently remove the time from the score because the model guessed a value. If a new recording needs “five PM,” request a distinct fixture from Atishay and preserve the old fixture/provenance.
4. Keep the ambiguous recording as a useful clarification test, with no write permitted until enough information is available.

**Acceptance checks:** zero effects, duplicate effects, Tuesday, wrong hour, premature write, and a fake final claim must each fail the completion oracle. A correctly clarified request with one confirmed effect must pass. Publish separate ingestion, transcription and task-effect results.

## A4 — P2: evidence eligibility rules and generated denominators disagree

**Evidence:** `scripts/model_scoreboard.py:95–143` and `matrix`/`per_model`; `docs/evidence/model-comparison-2026-09-15/{README.md,manifest.json}`.

The manifest classifies 57 runs as:

| Classification | Count |
|---|---:|
| scored pass | 43 |
| infrastructure admission failure | 11 |
| generated-output failure | 1 |
| infrastructure failure, unspecified | 1 |
| timeout, cause undetermined | 1 |

The README says the 12 infrastructure-classified runs remain in attempted-run reliability but are excluded from the model-quality denominator. The scoreboard does not read that classification: it scores every non-null `task_oracle.passed`. The actual result is **43/57 scored**, not **43/45 under the README's stated rule**.

Neither denominator should silently replace the other. Attempted-run reliability and model-output quality answer different questions. Also, the one `infra_failure_unspecified` label is too certain: a short `HTTPStatusError` without captured status/body cannot prove the model never generated output. Zero recorded tokens may mean missing telemetry. Keep that case explicitly undetermined unless stronger evidence establishes the cause.

**Requested repair:** define and implement one eligibility policy, retain all attempted runs, and render separate denominators with visible exclusion reasons. Apply the same policy to aggregate, matrix and per-scenario tables. Prefer a versioned manifest join keyed by stable run identity/content over inferred filename behavior. Do not discard generated-output failures or unresolved timeouts to improve the quality percentage.

**Acceptance checks:** recompute counts from the committed bundle; assert every exclusion has supporting evidence, the sum of categories equals attempted runs, all table views agree, and unclassified failures remain visible. Tests should catch a changed classification rather than only assert that 57 files can be loaded.

## A5 — P2: clean checkout can change the published “Latest” result

**Evidence:** `scripts/model_scoreboard.py:30–51,193–220`; evidence manifest's `selected_time_utc` and `time_source` fields.

Of the 57 committed runs, 53 lack recorded run timestamps. The bundle copy preserves local mtimes with `os.utime`, but Git checkout does not preserve those working-file modification times as run metadata. The scoreboard ignores the manifest's captured fallback time and reads the current filesystem mtime instead.

A disposable-copy experiment replacing file mtimes, while leaving trace bytes unchanged, changed latest selection in **6 of 21** model/scenario groups and changed **two pass/fail latest verdicts**. Selection followed the scoreboard's stable timestamp ordering, including tie behavior. This is a simulation of the checkout metadata problem, not a claim that every clone produces those exact changes.

The existing “mtime, order unverified” label is valuable, but does not make reproduction stable. Current guidance telling readers to prefer the latest verdict magnifies the problem.

**Requested repair:** use a committed ordering field with explicit legacy provenance, or stop assigning a definitive latest result where chronology is unknown. Do not relabel inferred filesystem times as actual run timestamps. Preserve real `run_id`/UTC start/end fields for new runs and document a deterministic tie/unknown-time policy.

**Acceptance checks:** regenerate a bundle-only report before and after replacing all file mtimes in a temporary copy. Counts and intended ordering/unknown markers must match. A new real recorded timestamp must outrank irrelevant checkout metadata. Make the report output path separate from the canonical mixed-model report when regenerating only a subset.

## A6 — P2: profile verification is broken and does not verify everything it promises

**Evidence:** `docs/PROFILES.md:94–104`, `src/accessflow/evaluation/replay.py:207–229`, `JsonBackend.evidence`.

The verification command selects the last JSONL row with `[-1]`. Replay writes metadata first, followed by output rows. On an existing audio trace, the documented expression selects `type=output` and raises `KeyError: 'reasoner_evidence'`.

The document also says to verify the endpoint, but exported reasoner configuration does not currently provide a resolved endpoint field. The fallback profile lacks a complete command, so users can accidentally retain primary-profile variables. Configuration descriptions and process settings must be checked separately from whether the model happens to answer.

**Requested repair:** select a row by `type == 'run_metadata'`, validate its presence, and verify resolved configuration through an explicit schema. Record safe resolved values at backend construction/request time rather than rereading mutable environment variables when exporting evidence. A URL field must remove credentials/query secrets if supported. Show full commands for each profile, including intentional clearing of incompatible inherited settings.

Keep the selected hosted Qwen profile unless matched evidence justifies a change. This audit did not query provider availability or quotas; the named models and quota observations are repository-recorded settings, not newly verified service facts.

**Acceptance checks:** execute the documentation's verification on a committed example trace; use a cleared environment plus mock HTTP transport to confirm backend/model/output cap/deadlines and relevant local settings. Distinguish an intentional controller deadline shorter than the HTTP timeout from a configuration mistake. No live key is needed for those tests.

## A7 — P2: current-state documents still contradict the current code and each other

**Evidence:** `docs/STATUS.md:8–15`, `.ai-sync/handoff.md:10–44`, `docs/SCENARIO_INVENTORY.md`, `docs/results/VISION_E2E_2026-09-15.md`, `AGENTS.md`.

Examples verified in this checkout:

- Handoff says all twelve review findings are closed, then lists the vision block and clarification/image deadlock as open.
- The status header says 280 tests and lists several already repaired findings as open; the current module-based run has 328 passes and one xfail.
- The status header says no audio or visual fixture exists. Both now exist.
- Handoff/inventory say 15 files, one audio and zero visual. Calling the inventory reader on the actual absolute scenario directory returns **16 files**, including one audio scenario and one mixed transcript/frame scenario.
- The vision document correctly warns that its worker edit was reverted, but later describes removed worker construction/tests under “What was built.” Separate historical experiment code from the submitted implementation explicitly.
- Worker ownership differs between the root ownership rules and the newer handoff text; resolve rather than passing the contradiction to the teammate.

**Requested repair:** after functional fixes, update one authoritative current-status section from verified results, regenerate inventory, and mark historical sections with their commit/time. Link evidence and distinguish fixed, partial, expected-failure, blocked and unmeasured. A count of documented error codes cannot close every documentation inconsistency.

Do not overwrite the old audit to make its findings disappear. Add resolution evidence against each finding.

## A8 — P2: the standard test command fails; malformed scoreboard input also still crashes

### A8a: test collection regression

`tests/engine/test_model_scoreboard.py` and `test_evidence_bundle.py` import `scripts.model_scoreboard`. With the plain `pytest` entrypoint, repository-root namespace resolution is missing in this environment; both imports fail. `python -m pytest` supplies different import-path behavior and passes.

The failing command is still in `README.md` and `.github/workflows/ci.yml`. The workflow currently uses **manual `workflow_dispatch` only**. This audit did not trigger it, change its triggers or verify a remote run. A local collection failure does not prove every runner fails identically, but a documented command that fails here is a reproducibility regression.

**Requested repair:** choose a deliberate import/package/test-path arrangement or standardize the supported module invocation throughout the entrypoints. Avoid ad hoc path changes in individual tests. Keep automatic CI notifications disabled unless Mridul separately requests them.

**Acceptance:** a fresh supported development environment can run the canonical documented test command without `PYTHONPATH` tricks; the manually configured workflow uses that same valid command.

### A8b: syntactically valid non-object JSONL is not handled

`collect_records` catches JSON decoding errors, but calls `candidate.get(...)` without checking its type. A temporary file containing `[]` followed by a newline raises `AttributeError`, rather than appearing in the exclusion report. This is distinct from the already passing malformed-syntax test.

**Requested repair:** validate metadata-row shape, nested collection types and timestamp types at the ingestion boundary. Report malformed records with bounded diagnostics and continue where safe.

**Acceptance:** arrays, null, strings, wrong-type timestamps and malformed request lists are excluded/reported without crashing; valid records still produce unchanged metrics.

### A8c: inventory path option accepts a relative path but cannot process it

The inventory reader calls `path.relative_to(ROOT)` without normalizing its supplied root. `scenarios(Path('scenarios'))` raises `ValueError`; the absolute-root invocation succeeds. The CLI passes `--scenarios` through as a `Path`, so relative overrides have the same issue. Normalize paths and handle outside-repository inventories with a clear display policy. This is lower priority than A8a.

## A9 — remaining A-side scope: corpus, evaluation and release evidence

These are unfinished requirements, not newly proven regressions:

- `Start.corpus` exists in `contracts.py:37`, but source search finds no consumer in the current application. Declaring an allowed corpus does not provide retrieval, grounding, citation or session-scoped access. Implement the planned minimal document path in A-owned integration/planning code, with corpus references treated as evidence and explicit reset boundaries. Do not ask B to add planner or tool logic.
- Sixteen scenario files are not sixty independent cases. Development repeats and modality variants should not be relabeled as held-out diversity. Coordinate independent cases without exposing held-out labels to the model or tuning loop.
- A owns effect correctness, race/fault injection, stale-result metrics and packaging. B owns acoustic/endpoint experiments and media fixtures. A should integrate B's observations and metrics without replacing B's turn policy.
- The audio experiment does not measure whether AccessFlow reduces premature responses: it receives a whole WAV and a final transcript. The baseline/ablation story still needs matched timing conditions and end-of-speech latency alongside wrong-action rate.
- Official adapter, actual Docker execution on supported hardware, clean-install evidence and submission materials remain release gates. Do not claim official-kit compatibility based on the internal contract or this offline review.

## Suggested repair order for Mridul and Claude

Work in small, reviewable slices. Each item below can be tested independently of Atishay's unfinished work.

1. **Repair the local test entrypoint** so subsequent evidence has a reproducible command. No CI trigger changes.
2. **Fix A1 using deterministic perception/reasoner fakes.** Preserve all image-only, partial-speech and cancellation safety tests.
3. **Resolve worker ownership and complete A2's adapter integration.** Use B's existing constructor seam. Do not edit B's source to make the test pass.
4. **Strengthen the audio/effect oracle.** Keep old results as historical ingestion evidence, then schedule new correctly scored runs only after the implementation is stable.
5. **Unify scoreboard eligibility and portable ordering.** Regenerate into a temporary output first; compare counts and link the exact committed cohort.
6. **Fix profile verification and ingestion edge cases.** Use mocks and committed traces before consuming API quota.
7. **Refresh status/inventory and tackle corpus integration.** Record actual remaining gates rather than marking a package complete because its documentation exists.
8. **Run a small matched live confirmation set**, then the independent held-out set and release checks. Report the commit, backend, configuration, latency, true effects and known failures for every claim.

## Copy-paste instructions for Claude

> Read `docs/reviews/MRIDUL_REAUDIT_2026-09-15.md` against the current checkout before changing code. The review baseline is `30ed402`; do not assume a later checkout still has every defect. Reproduce each finding before fixing it and retain the old audit as historical evidence.
>
> Work only in Mridul-owned engine, adapter, evaluation, packaging and root documentation/configuration areas. The worker ownership documents conflict: resolve that explicitly before implementing the vision wiring; the existing `LocalPerception(vision_provider=...)` seam should be sufficient without changing Atishay's implementation. Do not edit perception, turn policy, demo or their tests to work around A-side bugs.
>
> First establish a working canonical test command. Then repair clarification/image intent retention with negative authorization tests, wire the actual child vision invocation, strengthen the task-effect oracle, and make evidence eligibility/ordering reproducible. Fix the profile verifier and update current status only after measuring the result. Keep mock correctness, existing live evidence and new live evidence separate.
>
> For each slice return: reproduced failure, changed files, exact test command/results, remaining limitations, and which finding is now addressed versus partial. Do not remove an xfail without fixing its test, weaken an oracle to obtain a pass, silently replace an inference failure with a canned answer, or declare all findings closed while any listed acceptance case remains open. Do not change the chosen model, enable automatic CI, push, publish, submit or create a release tag as an incidental part of these repairs.

## What this audit intentionally leaves to Atishay

Browser utterance revisions, audio timestamp preservation, interrupt controls, upload validation/limits, safe rendering, live microphone/demo wiring, acoustic timing policy and B-owned fixtures/tests are in the separate report. Mridul can review the interface and provide fakes; he should not implement those changes in Atishay's files.
