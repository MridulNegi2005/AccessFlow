# AccessFlow review for Claude — 15 September 2026

## Decision and scope

Keep Qwen as the working hosted model choice. Fix the execution and evaluation issues below before another broad model sweep. The current evidence supports a promising text prototype; it does not establish a complete accessible multimodal agent or a submission-ready system.

This is a review, not an implementation pass. No application code, tests, configuration, credentials, branches, or existing documentation were changed. No model server was started, no hosted inference benchmark was run, no workflow was dispatched, and nothing was committed or pushed. This report is the only deliverable added. The four independent planner probes were neither executed nor opened for their labels.

Reviewed checkout:

- Repository: `AccessFlow`, branch `mridul/engine`.
- HEAD: `92ead42` (`Record every model against every scenario`).
- Working tree was clean before this report. Local branch was nine commits ahead of its **locally cached** remote-tracking branch. No fetch was performed, so this is not a fresh assertion about GitHub.
- Comparison baseline: `d8dbec5`, the prior Codex stop checkpoint.
- The range includes Atishay's merged changes. Those are not automatically attributable to Claude. Git author names alone do not establish which AI wrote a change; attribution here uses the handoff, individual changes, and the baseline.
- Current Python source digest: `8f5d31d859d4a6ad23108114014a173ea985ec8eba562823e9c14c85b00a5fd5` using the repository's `source_evidence` function.

### What I independently checked

```text
uv run --offline --frozen --extra dev pytest -q
258 passed, 2 existing TestClient deprecation warnings, 24.06 seconds

uv run --offline --frozen --extra dev ruff check .
All checks passed
```

I also ran small in-memory reproductions with fake tools and `httpx.MockTransport`. They made no provider requests. Their observed results appear below. A passing existing suite does not invalidate a reproduced missing case.

### What Claude did well

1. Kept provider selection explicit and avoided automatic fallback. The shared hosted transport reduces duplication.
2. Preserved failed measurements and identified real runtime confounders, including controller deadlines and model reasoning overhead.
3. Added a bounded retry for repeated completed calls instead of an unbounded model loop.
4. Kept the controller's argument grounding, action ledger, and independent authorization checks intact.
5. Reported the negative ablation result rather than inventing a demonstrated benefit.
6. Collected enough text evidence to make Qwen a reasonable working choice. Continuing to compare many models is now lower value than integration and correctness work.

## Verified model evidence, with its limits

The selected six Qwen traces are present locally under:

```text
artifacts/sweep27b/qwen-qwen3-8-27b--*.jsonl
```

All six have passing task oracles. All six record the **same Python source digest as the current checkout**. One was collected with a dirty worktree and a different recorded commit; the matching source digest is useful evidence that the Python implementation was the same. It is not a hash of every dependency, script, or machine setting.

The recorded backend identifier is `groq/qwen/qwen3.8-27b`. I retained the project's exact identifier; I did not query a current vendor catalog or independently verify today's quota/model availability.

| Selected fixture | Recorded scenario runtime | Interpretation |
|---|---:|---|
| Device correction before planning | 1.596 s | Passed corrected mock action |
| Lost-response reconciliation | 2.155 s | Passed status recovery |
| Stale read after symptom correction | 28.238 s | Includes deliberately scheduled conversation gap |
| Stale read after device correction | 28.901 s | Includes deliberately scheduled conversation gap |
| Support read followed by service | 1.977 s | Passed read/write chain |
| Text correction | 1.225 s | Passed corrected mock action |

These runs use `json_object`, temperature zero, a recorded output cap of `950`, and a 30-second model HTTP timeout. Individual successful requests include values up to **1.234 seconds**. The often-quoted 0.83–0.99 second figures describe rounded per-fixture averages, not an upper bound on every request.

Across the scoreboard's broader, mixed-era non-ablated Qwen history, I counted **25 runs and 21 oracle passes**. Neither 21/25 nor the selected 6/6 is a held-out estimate. The six selected successes are valid development evidence; the aggregate mixes configurations and failures, including provider admission failures.

## Priority map

P1 means fix before claiming reliable completion or using the result as release evidence. P2 means fix before wider evaluation/submission. These priorities describe project impact, not proof of exploitation in production.

| ID | Priority | Finding | Status / attribution |
|---|---|---|---|
| R1 | P1 | Hosted output bypasses the dynamic continuation schema; false completion prose can reach the user | Reproduced; new continuation/hosted assumptions expose an inherited final-output weakness |
| R2 | P1 | Continuation is not scoped to the active request and write intent can disappear on a follow-up plan | Helper newly added by Claude; flag replacement behavior inherited |
| R3 | P1 | Null response does not require progress; recovery covers only one class of stall | Reproduced schema gap; latest loop diagnostic is a real but partial improvement |
| R4 | P2 | Scoreboard's `Latest` is not chronological and some denominators disagree | Reproduced in Claude's new script |
| R5 | P1 before publication | Raw HTTP error bodies can enter supposedly content-free evidence | Reproduced in the new diagnostics path; no claim that an actual secret was found |
| R6 | P2 | Reconciliation defect is misdiagnosed as the earlier idempotency edge | Reproduced; old guard behavior, incorrect newer explanation |
| R7 | P1 for clean-machine use | Selected Qwen configuration is not delivered as a reproducible profile | Current setup/configuration gap |
| R8 | P1 for release evidence | New model and ablation evidence lives in ignored local artifacts | Verified packaging gap; selected raw files do exist on this machine |
| R9 | P2 | Ablation conclusions and stop rules are broader than the experiment supports | Methodology/documentation issue |
| R10 | P2 | New per-event timing accepts NaN and bypasses the replay-budget comparison | Reproduced validation bug |
| R11 | P1 completion gate | Actual endpointing, vision integration, and corpus use remain incomplete | Inherited/integration scope, not proof Claude broke them |
| R12 | P2 | Handoff, status, contract notes, and setup examples contradict current code | Verified documentation drift |

## R1 — Enforce the exact generated schema locally, and defend final outputs

**Locations:** `src/accessflow/adapters/models.py:140`, `:156`, `:233`, `:319`, `:375`; `src/accessflow/engine.py:371`, `:456`.

### Evidence

The hosted default is `response_format={"type":"json_object"}`. The dynamic schema is included in the prompt, but the post-response validator is only `PlanProposal.model_validate`. That static model permits a string `response` and supplies defaults for omitted fields. It does not implement the current dynamic restrictions on tool names, read-only planning, or final prose.

My mock returned a complete static `PlanProposal` containing `response="The service is booked."` with `view.write_pending=True` and no previous write. Observed:

```json
{"transport":"json_object","schema_accepts_response":false,"adapter_accepted_response":"The service is booked."}
```

A separate controller probe used this sequence:

1. A completed user request asks to check availability and book Wednesday.
2. First proposal has `write_requested=True`, stores Wednesday, and dispatches a read.
3. After the read succeeds, the next proposal contains only the quoted response.
4. The controller emits an informational final containing that text; write effect count is zero.

```json
{"text":"The service is booked.","basis":"informational","backend":"reasoner"}
```

This is an injected bad-model-response test. It does **not** show that the selected Qwen run actually made that claim. It proves the claimed constraint is not enforced through the default hosted path and that the controller cannot rely on that constraint for truthful completion.

### Required change

- Validate the returned object against the **exact schema generated for that request**, before accepting it or recording generation success. Keep static Pydantic validation too.
- Treat provider structured output as an additional aid, not the sole enforcement layer. `json_object` is not sufficient. Simply setting the provider's structured flag also leaves other backends and test doubles relevant.
- Keep action completion separate from informational response generation. If an accepted request still owes an effect, a prose-only proposal must not silently finish it.
- Do not try to solve this with a list of forbidden phrases such as “booked.” A deterministic request/effect state and explicit response basis are more reliable.
- Route rejection into a bounded correction/clarification path, not a silent wait or unrestricted retry.

### Acceptance tests Claude should add

1. Hosted `MockTransport` returns a string when this request's schema requires null: rejected with a specific schema-validation outcome, zero dispatches, zero successful-generation count for that response.
2. Hosted response names a tool outside the current manifest or proposes a write in an unresolved-outcome turn: rejected at the dynamic schema boundary as well as protected by controller checks.
3. Read-then-prose while a current requested write is outstanding: no final success claim and no invented committed effect.
4. Legitimate information-only requests can still answer normally.
5. Confirmed successful and reconciled writes still emit their controller-generated finals.

## R2 — Make continuation state belong to the current request

**Locations:** `models.py:292`, `:332`; `contracts.py:189–198`; `engine.py:202`, `:263`, `:371`.

### Two distinct problems

**A. Historical writes disable the new continuation rule.** `write_outstanding(view)` scans every call in the session. Any old successful write makes it return false, even if `view.write_pending=True` now describes a different request.

My direct reproduction used a view with `write_pending=True` and one old successful write:

```json
{"new_request_write_pending":true,"write_outstanding":false}
```

`ToolCall` exposes operation IDs but no active-request association. The helper's docstring says “for this request”; its implementation cannot establish that relationship.

**B. Write intent is replaced by every model follow-up.** `_apply` assigns `speech_write_requested` from the new proposal's `write_requested` flag even when the plan was triggered by a read result for the same spoken request. A model that omits or changes the flag can erase previously recognized intent. Conversely, a model that never recognizes the initial write never activates the continuation rule at all.

The second behavior was present before Claude's changes; the new `write_pending` projection depends on it. Do not describe that projection as independent evidence of user intent.

### Required change

- Define explicit request lifecycle semantics: accepted request, unresolved details, awaiting read, awaiting effect, outcome unknown, completed, canceled, and superseded. This need not become a large framework.
- Add an additive, documented association between calls and their request, or project only the relevant request's calls to the continuation helper. Preserve whole-session audit history separately.
- Preserve recognized intent across tool-result replanning for the same request. Change it in response to new user evidence or explicit request resolution, not an omitted Boolean alone.
- Keep intent recognition separate from execution authorization. Do not set `write_requested=True` merely because a write tool exists, because a read completed, or because repeated reads were detected.
- Define how a genuinely new request differs from a correction and from an intentional repeated action.

### Acceptance tests

Complete request A, then ask for request B requiring read-then-write in the same session. A must not disable B's continuation. Also cover an information-only follow-up after A, explicit cancellation, two intentional identical bookings, correction of B, unknown outcomes, and a follow-up model plan that drops its earlier flag.

The existing final-output check also considers writes anywhere in the session. Include that inherited behavior in the multi-request tests instead of fixing only the new helper.

## R3 — Require progress or an explicit bounded outcome

**Locations:** `models.py:301`, `:375`; `engine.py:429–473`; `tests/engine/test_dispatch_evidence.py`.

The latest code **does** emit `repeated_completed_call` and allow one recovery attempt. The handoff's claim that repeated calls always disappear silently is stale. Keep the improvement.

However, setting `response` to null does not leave “only a tool call or a clarification,” as the comment claims. A fully expanded `PlanProposal()` with empty calls, null clarification, and null response validates against the outstanding-write schema. I verified that directly.

Other quiescent cases remain: invalid dependencies, incomplete write flags, a second unsuccessful repair, or calls that cannot dispatch. The new diagnostic only triggers when at least one call matched a successful prior call and nothing else dispatches. A mixed proposal with one repeated call plus one invalid call can also make its “every proposed call has already completed” message inaccurate.

### Required change

- Identify whether an accepted plan dispatched work, emitted an answer/clarification, is legitimately waiting on existing work, or made no progress.
- For no-progress plans, provide typed feedback with a bounded recovery budget scoped to the active request/input revision. On exhaustion, emit an understandable clarification or explicit failure state.
- Do not allow recovery to exceed the scenario deadline or to loop on quota failures. Invalidate repair work when newer speech arrives.
- If tightening the schema, express the valid alternatives explicitly. Preserve a legitimate waiting state when work is already pending; do not force duplicate calls just to satisfy a schema.
- Validate the retry outcome, not just that a retry was scheduled.

### Acceptance tests

Empty plan while an action is owed; repeat-read then successful repair; repeat-read then repeat-read again; malformed dependency then one correction; pending tool with no new call; partial speech; a new utterance during recovery; and a second independent request after a prior request used its recovery budget.

Expected result on exhaustion: no false success, no duplicate effect, no unlimited model calls, and no unexplained wait until 115 seconds.

## R4 — Repair the scoreboard before trusting its `Latest` column

**Locations:** `scripts/model_scoreboard.py:18–43`, `:86–108`, `:111–142`; `docs/results/MODEL_COMPARISON.md`.

### Reproduced bug

The script records only the file modification **date**, discarding time. Files are initially traversed in lexical pathname order. A stable sort by that date therefore chooses the lexically last file on a day, not the newest run.

I compared the script's selection with full modification timestamps. **15 model/scenario groups selected a different file; five changed the pass/fail verdict.** Examples:

| Model / fixture | Script selected | Newer file by full mtime | Verdict change |
|---|---|---|---|
| Qwen 2.5 3B / device correction | `live-local-qwen25-original/case-001.jsonl` | `fair-qwen2-5-3b/scenario-001.jsonl` | fail → pass |
| Qwen 2.5 3B / reconciliation | `live-local-qwen25-original/case-002.jsonl` | `fair-qwen2-5-3b/scenario-002.jsonl` | fail → pass |
| Qwen 2.5 3B / text correction | `live-local-qwen25-original/case-004.jsonl` | `fair-qwen2-5-3b/scenario-004.jsonl` | pass → fail |
| GPT OSS 120B / support chain | `groq-gptoss120b/scenario-003.jsonl` | `groq-gptoss120b/redo2_support.jsonl` | fail → pass |
| GPT OSS 120B / text correction | `groq-gptoss120b/scenario-004.jsonl` | `groq-gptoss120b/redo_text_correction.jsonl` | fail → pass |

All paths in that table are relative to `artifacts/`. Full mtime is only a diagnostic comparison, not a reliable long-term run timestamp: copying or extracting files can change it too.

### Other problems in the same script

- The matrix divides by all results, including null/unscored oracles; per-model tables divide only by scored entries. The current report shows different denominators for the same evidence, such as 10/11 versus 10/10.
- Request latency includes only requests marked successful. That can be a useful metric, but `Slowest` and `Mean request` need that qualification. They are not end-to-end latency or a timeout-inclusive service reliability metric.
- Copying a trace inside the scanned tree creates another counted run. There is no immutable run ID/deduplication.
- Malformed JSON and filesystem failures are silently skipped. An evidence tool should report exclusions.
- The code advertises `--artifacts` but makes paths relative to the repository root; an outside-root archive can fail with `ValueError`.

### Required change and tests

Record immutable `run_id`, full UTC start/end timestamps, source/config/scenario identifiers, and an explicit eligibility classification. Select the latest using the run timestamp. For old traces without one, label ordering unknown or use an explicitly disclosed fallback. Do not silently invent chronology from filenames.

Use the same scored denominator everywhere; separate unscored infrastructure failures and canceled runs while retaining overall attempted-run reliability. Report successful-request latency separately from total scenario time and failure latency. Deduplicate by run ID and retain both evidence and exclusion reasons.

Add tests with opposite lexical/time order on the same day, a copied file with a changed mtime, a duplicate run ID, a null oracle, a malformed trace, and an outside-root evidence directory. Regenerating the table should not modify historical raw traces.

## R5 — Bound and sanitize diagnostics, not just their length

**Location:** `models.py:120–130`; `JsonBackend.evidence` promises evidence without model content.

`response.text[:400]` preserves arbitrary provider error text. Providers can echo request content, generated text, identifiers, or other sensitive information in an error. A 400-character limit does not remove that content.

An in-memory HTTP-error reproduction containing `SYNTHETIC_PRIVATE_USER_TEXT` retained that marker in `evidence()['requests'][0]['error_detail']`. No real key or private transcript was used, and this review did not inspect `.env` values. This is a demonstrated logging property, not an assertion that a real secret is currently committed.

Before copying evidence into the public submission:

- Prefer allowlisted provider error codes/types and normalized categories such as rate limit, authentication, output limit, invalid JSON, and timeout.
- Keep useful safe numeric quota information where it can be parsed without copying the whole response body.
- If raw diagnostics are needed locally, separate them from exportable telemetry with explicit retention/export rules.
- Add tests for synthetic secret-like strings, echoed prompt text, malformed response bodies, and legitimate rate-limit diagnostics.
- Capture safe `finish_reason`/truncation information and output cap so a length-limited JSON response is not mislabeled as an unexplained reasoning failure.

## R6 — Fix the reconciliation explanation and namespace handling

**Locations:** `engine.py:475–508`; handoff's `missing_dependency` entry; `tests/engine/test_reconciliation.py`.

The correct unresolved operation ID is already allowed as a literal argument to its declared read-only status tool. The failure occurs when the planner also puts the status parameter name, such as `receipt`, in the **slot dependency list**, although that slot does not exist.

With an unresolved write, a declared read-only status tool, and no idempotency field on that read, I observed:

```json
{"dependencies":[],"guard_error":null}
{"dependencies":["receipt"],"guard_error":"missing_dependency"}
```

That is **not** the 13 September review's different edge: a read manifest declaring its lookup target itself as a controller-generated idempotency parameter. Do not conflate them.

### Next action

Teach/project the distinction between conversational slot dependencies and ledger operation identity. Improve diagnostic feedback so a model can repair this specific invalid proposal once. If introducing an explicit ledger-dependency field, make it additive and validate it against the matching unresolved write and declared status tool.

Do not “fix” this by ignoring all missing dependencies, creating user slots from arbitrary tool arguments, accepting any UUID-like string, or exempting every read tool. Preserve the existing tests that reject stale and unrelated identities. Document that a status lookup target and an independently generated read idempotency key must be separate concepts.

## R7 — Deliver the chosen model as a tested profile

**Locations:** `models.py:50–59`, `:192–211`; `.env.example`; `docs/RUNNING.md`; `scripts/start-local-ollama.ps1`.

Current defaults still select `gemma3:4b` for Ollama and `llama-3.3-70b-versatile` for Groq. `.env.example` contains those older choices and omits the newly essential `ACCESSFLOW_MAX_OUTPUT_TOKENS=950` profile setting. The CLI does not itself load `.env`; a file sitting in the repository is not proof that its values reach `os.getenv`.

There is also contradictory GPU guidance: `.env.example` recommends leaving placement unset because auto-fit selects all layers, while the later results/handoff say auto-fit was unreliable and require a model-specific pin. The portable server's project port also needs to match the client's URL; a user's default Ollama port is not automatically the dedicated project endpoint.

### Required deliverable

Provide a named, reproducible hosted-Qwen profile and an explicitly selected local profile. Document exact model ID, endpoint, response mode, output cap, HTTP/controller deadlines, and how variables enter the process on PowerShell. Do not place credentials in the committed profile.

The hosted profile should correspond to the measured values, for example the recorded model identifier, cap 950, and tested request deadline. Those numbers are a starting configuration from this evidence, not a guarantee about future quota availability. Validate cap type/range early and record the resolved settings once per run.

Test the documented profile in a clean environment that has no inherited project variables. Verify the request's model, cap, URL, and deadline with `MockTransport`, then perform a separately labeled live check when authorized. No automatic provider/model fallback should appear.

For local Qwen, resolve `think`, layer placement, cache, context, and model digest explicitly. Current evidence records `num_gpu` but not all server/think settings needed to reproduce the performance discussion. Larger-model universal claims should be narrowed to tested configurations.

## R8 — Make evidence portable before calling it reproducible

**Locations:** `.gitignore`, `scripts/model_scoreboard.py`, `docs/results/MODEL_COMPARISON.md`, `docs/results/ABLATION_2026-09-15.md`.

`git ls-files artifacts` returns only `artifacts/.gitkeep`. New Qwen and ablation reports reference ignored `artifacts/` files. The previous 13 September work preserved selected raw traces under tracked `docs/results/`; the newer evidence has not received equivalent packaging.

This does not make the local results fabricated: I read the selected Qwen files and verified their recorded passes/source hashes. It means another clone cannot independently regenerate the current table or inspect the selected evidence from the committed Markdown alone.

### Required evidence bundle

- A manifest of the selected runs and all exclusions, including full UTC times, run IDs, commit/source hash, scenario hash, resolved configuration, backend/model version, and declared hardware.
- Reviewed and sanitized raw input/output/metadata traces for the fixed evaluation cohort, plus relevant failed runs. Keep training/development exposure labels.
- A scoreboard invocation that reads that immutable bundle, not whatever happens to be under a user's `artifacts/` directory.
- A replay/analysis command that recomputes the published table without new provider calls, keys, local untracked fixtures, or invented timestamps.
- An exported-source/patch reference for any dirty run not fully explained by its source hash. The existing Python digest does not include every script, dependency lockfile, or environment setting.

Preserve both overall attempted-run reliability and model-quality-eligible results. An infrastructure failure is not automatically evidence of wrong reasoning, but it still matters to whether an evaluation task finishes. Conversely, not every `backend_failure` is infrastructure: validation/JSON failures can originate in generated output. Classify by specific evidence rather than blanket exclusion.

## R9 — Keep the negative ablation, narrow the claims

The code disables `_invalidate_dependencies`; it does not remove `_result`'s independent currency check, write cancellation, argument grounding, or other safety rules. For already accepted reads, this is a useful isolated mechanism test. It is not an ablation of every stale-result defense.

The main stated cohort is 18 runs: 12 GPT OSS 120B runs across two fixtures/arms, plus six GPT OSS 20B runs on the device fixture. The prose “three trials per arm per fixture per model” would imply 24 runs; enumerate the actual cells instead. The directory also contains additional controls/pilots/local runs, so globbing the whole folder is not the cohort definition.

Required methodological corrections:

1. Predefine run IDs in each arm and exclusions. Both new fixtures currently allow the ablation marker in their oracle, so the scoreboard's explanation that the marker necessarily fails those oracles is stale. Excluding ablated runs from primary model rankings is still reasonable because they are a different condition.
2. Record/assert that the first read was accepted before the correction. A fixed 26-second gap schedules an event; it does not prove the intended internal state was reached on every backend.
3. Report final effects, premature clarifications, wasted work, and latency separately. The documented negative final-effect result should remain negative.
4. “No difference in these runs” is supported. “The model does not need the mechanism,” “no local model can ever finish,” and a universal hardware bound for every model above 4B are not established by this small set.
5. Do not invent a misleading fixture to force a win. Equally, a realistic API response that lacks an echoed device identifier is not automatically deception; many real APIs rely on request provenance rather than repeating their arguments. Such a case can be valid if selected from a real interface contract and specified before testing.
6. A pending-read latency/cancellation study is a separate experiment with a different outcome measure. Preserve the late-result rejection checks when measuring how much work early cancellation saves.

A practical stop condition is to defer further ablation expansion until basic multimodal integration and request correctness pass. It is not necessary to keep spending quota until a positive result appears.

## R10 — Reject non-finite per-event gaps

**Location:** `src/accessflow/evaluation/scenarios.py:30–33`, `:72–79`.

The added list uses unconstrained floats and checks `gap < 0 or gap > 60`. Both comparisons are false for NaN. The summed 114-second budget comparison is also false for NaN.

I loaded the ordinary device-correction fixture, replaced its gaps with `[float('nan'), 26]`, and validated it:

```json
{"accepted":true,"sum_is_nan":true}
```

The normal controller deadline still exists; this is not proof the controller's own hard limit is bypassed. It is proof the scenario's advertised pacing/budget validation accepts an invalid schedule.

Use finite constrained element values or an explicit finite check, plus a finite total. Test NaN, positive/negative infinity, negative gaps, wrong list length, exact boundary values, and a sum above the replay budget. Consider strict JSON parsing for nonstandard NaN/Infinity literals. Validate public CLI timeout inputs for finite values as well.

## R11 — The biggest remaining product gate is actual multimodal turn handling

This is unfinished scope, largely inherited. It should not be described as a regression introduced by Claude.

### Current evidence

- `LocalPerception` has an injectable vision seam, but `perception_worker._serve` constructs it with only `model_path`. The normal process adapter therefore has no configured vision provider; `FrameEvent` raises `Image perception requires an explicit vision provider` on that path.
- Audio fixtures and adapter measurements exist. That is not an end-to-end demonstration that long pauses do not cause premature turn completion.
- `HeuristicTurnPolicy` consumes transcript finality/correction words. The WebRTC/activity utilities are not by themselves an acoustic endpointing integration. The shared timing proposal remains pending.
- `Start.corpus` is declared, but the controller does not expose it to the planner or implement the planned lexical manual retrieval. Fixed mock lookup rows are a different capability.
- Directory counts are four `scenarios/dev`, six `scenarios/live_dev`, and four independent planner probes. Several are variants of the same underlying workflow. A count of eight unique development scenarios needs an explicit inventory; file count alone is not independent coverage.

### Claude's A-side responsibilities

Coordinate the additive timing/vision interface with Atishay, without editing his implementation unilaterally. Wire the real providers through A-owned process/adaptor boundaries. Preserve source IDs, cancellation, and session cleanup. Distinguish transcript input, actual WAV transcription, and actual PNG perception in every result.

For the core research question, collect both failure and waiting-time measures: premature response rate, correct final slots/effects, time from actual speech end to substantive response, acknowledgments separately, clarification count, total task time, and resource/provider failures. A fast hosted text plan does not prove patient turn-taking.

Implement or explicitly resolve the planned corpus capability. A session's allowed references must constrain which installed documents are available; document contents remain evidence, not instructions. Do not let a corpus reference become permission to read arbitrary machine paths.

## R12 — Update the handoff once, from current facts

Examples of drift that can misdirect the next coding session:

- Handoff: branch/main at `ad04bca`, ablation uncommitted, 254 tests. Actual reviewed HEAD is `92ead42`, working tree clean, 258 tests pass, and the ablation/loop changes are committed.
- Handoff and ablation text: duplicate reads emit nothing. Actual code emits `repeated_completed_call` and performs one bounded retry.
- `docs/STATUS.md` still starts with 13 September and reports 204 tests/older model status, while later sections discuss newer work.
- `.env.example` and later inference documentation disagree on automatic layer fitting.
- `docs/CONTRACT.md` and `docs/CONTRACT_PROPOSALS.md` do not describe `SessionView.write_pending` or `repeated_completed_call`, despite their role in cross-agent behavior.
- `MODEL_COMPARISON.md` claims the adapter sends no `max_tokens`; current code sends it when the cap variable is set. Describe the uncapped path specifically.
- Older artifact copies and current canonical documents can disagree. Identify the canonical version and date rather than treating every copy as current.

Do not erase historical measurements. Separate a short current-state summary from immutable historical notes. When reporting remote branch synchronization, perform a fresh read-only check first; do not copy an earlier “pushed” claim over new local commits.

## Bounded next work for Claude

Do these as reviewable slices, with exact tests and a stopping point. This is proposed future work, not permission for the reviewing Codex session to implement it.

### Package 1 — Correctness before more model tuning

Resolve R1, R2, and R3 together because schema validation, request ownership, and continuation interact. Include the R6 receipt namespace case. Preserve default-deny execution authorization and all existing stale-result/idempotency protections.

Deliver:

- An additive contract note defining active request identity, pending effect, and legitimate waiting.
- Regression tests that first reproduce the failures, then pass with the fix.
- Hosted mock tests that violate the dynamic schema deliberately.
- Two-request-in-one-session tests, bounded no-progress recovery, and correction during recovery.
- Full offline suite and lint results, plus limitations.

Do not proceed by changing expected fixture answers, granting missing authorization, or deleting failing safety checks. Do not retune against the independent probe labels.

### Package 2 — Configuration and evidence that another clone can use

Resolve R4, R5, R7, R8, R10, and the current-state parts of R12. This package should largely be independent of model quality.

Deliver a tested Qwen profile, safe diagnostics, validated limits, immutable evidence manifest, corrected scoreboard tests, and one documented clean-clone analysis command. Keep old failures with explicit classifications. A passing output-cap run must record that cap; a truncated response must not disappear from evidence.

### Package 3 — One real multimodal path at a time

With Atishay's agreed contract, establish:

1. Raw WAV → actual ASR → controller → real reasoning → confirmed mock tool effect.
2. Raw PNG → actual vision → sourced observation → corrected state → confirmed mock effect.
3. Replacement/cancellation while perception or inference is running, including a late result.
4. Session reset and cleanup with no conversation carry-over.
5. Actual timing/endpoint observations, followed by the same reasoning/tool stack under baseline policies.

Do not substitute an unlabeled supplied transcript for failed WAV inference or a scripted caption for failed vision. Use installation assets and team/synthetic media with recorded provenance. Keep B ownership explicit.

### Package 4 — Freeze a fair evaluation and prepare release evidence

Create a scenario manifest that distinguishes base cases, variants, faults, modalities, development exposure, and held-out status. Expand toward the planned 30 text / 18 audio / 12 visual distribution and 40 development / 20 held-out split. Preserve the four existing independent AI probes for their first scored evaluation; they are not a replacement for the final teammate-authored held-out set.

Once the request contract and primary profile stabilize, run those four probes once, save all results, then inspect failure labels. Subsequent tuning makes them development data; do not keep calling them unseen.

Compare fixed short silence, fixed long silence, semantic completion, and AccessFlow using the same underlying perception/reasoning/tools where possible. Report task quality and waiting time together. Keep the current ablation's negative result separate from endpointing claims.

Finally verify actual Docker execution on a capable host, implement the official adapter only from the real kit, and align README, deck, video, AI disclosure, configuration, and results to one release candidate. Do not enable Actions, create the final tag, or submit forms during these coding slices without the corresponding user instruction.

## Copy-paste instruction for Claude

> Review `docs/reviews/CLAUDE_REVIEW_2026-09-15.md` against the current checkout before editing; its audited baseline is `92ead42`. Keep Qwen as the working primary model. Start with Package 1: enforce the exact per-request output schema locally, prevent false completion prose, scope continuation to the active request, preserve recognized intent across tool-result replans, and give no-progress plans a bounded explicit outcome. Add reproducing tests before changing behavior. Fix receipt dependency namespace handling without weakening slot/operation validation. Do not treat a write tool's existence as user authorization. Preserve corrections, stale-result rejection, default-deny authorization, and stable idempotency identities. Document additive contracts for Atishay and avoid B-owned edits. Then complete configuration/evidence work, real multimodal integration, and fair evaluation in the order described. Do not read the independent probe labels before their first scored run. Report exact commands, failures, commit/configuration, and honest limitations for each slice. Keep GitHub Actions disabled. Do not change expected outcomes merely to make the suite pass, run another broad model sweep as a substitute for these fixes, or claim release completion from development-set scores.

## Reproduction recipe for the main schema finding

This is an offline test outline, not application code added by this review. Use the existing pytest environment and a dummy test-only key; do not load `.env`:

```python
monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "audit-dummy")
monkeypatch.delenv("ACCESSFLOW_GROQ_STRUCTURED", raising=False)
view = SessionView(
    session_id="test", state=Snapshot(), observations=[], results=[],
    write_pending=True,
)
bad = PlanProposal(response="The service is booked.").model_dump(mode="json")
# Mock /chat/completions with choices[0].message.content = json.dumps(bad).
# Use a valid write ToolManifest and httpx.MockTransport; no network.
schema = ModelReasoner.output_schema([write_manifest], allow_final_response=False)
assert not Draft202012Validator(schema).is_valid(bad)
# Current code nevertheless returns this proposal from ModelReasoner.plan().
# The regression should instead require a specific dynamic-schema rejection.
```

For the controller half, use the helpers in `tests/engine/test_safety.py`: first return a complete proposal with `write_requested=True` and a grounded read call, then return the bad prose-only proposal. Current code emits the quoted informational final with zero write effects. The repaired test should require a truthful non-success outcome or continued bounded work.

## Claude CLI check

`claude --version` succeeded: **Claude Code 2.1.220**. Its local help supports print mode, disabling tools, disabling session persistence, and an empty strict MCP configuration.

I attempted a small review of a self-contained, secret-free design summary from a neutral temporary directory, with tools disabled, no session persistence, and no project settings. It failed before returning a review:

```text
Failed to authenticate. API Error: 401 OAuth access token is invalid.
```

No Claude-generated review was obtained, and none of the findings above is attributed to such a review. Credentials/login state were not changed. Claude CLI access can be tried again after the user restores its login; the audit itself is complete without that dependency.
