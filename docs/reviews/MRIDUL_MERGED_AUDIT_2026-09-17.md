# AccessFlow: Mridul's merged-code audit

Date: **17 September 2026**

Reviewed checkout: **`main`, `476a7b5`**, following merge `0805777`

Previous review baseline: `919ed27`

Companion: [Atishay's audit](ATISHAY_MERGED_AUDIT_2026-09-17.md)

Handoff prompt: [Atishay's first-person Codex prompt](ATISHAY_CODEX_PROMPT_2026-09-17.md)

## Verdict

The merged project has made real progress. The current suite is **799 passed, 1 xfailed**, with Ruff clean. Several defects from the previous audit are repaired, and Atishay's media/demo implementation is substantially more complete. Neither the older 411-test snapshot nor the 769-test first-merge snapshot represents this checkout.

The main remaining A-side correctness issue is **argument authority**: preventing a read result from inventing initial write permission does not prevent it from changing the target of an already authorized write. A controlled reproduction changed a Wednesday booking to Friday after reading a document, without another user utterance.

The outstanding frame test also needs careful interpretation. It fails before its safety assertions because it expects retained history that the engine intentionally removes. Both teammates need to agree replacement-versus-conflict semantics before treating that test as an implementation specification.

This is an audit, not an implementation change or full release/security certification. The user authorized publishing these audit documents. No source changes, live model requests, downloads, CI runs, release tags or submission actions are part of this review.

## Evidence and scope

| Check | Result |
|---|---|
| `uv run --offline --frozen --extra dev pytest -q` | **799 passed, 1 xfailed**, two existing deprecation warnings, 54.68 s |
| `uv run --offline --frozen --extra dev ruff check .` | Pass |
| `uv run --offline --frozen --extra dev pytest tests/demo/test_app.py::test_conflicting_frames_require_resolution_before_write --runxfail -q --tb=short` | Fails at `reasoner.conflict_seen.wait()`, line 3725, with `TimeoutError`; does not reach write/effect assertions |
| Controlled corpus/result-influenced planner | One mock write with `day=Friday` after the user requested Wednesday |
| B perception timeout probe | Three native transcriber calls still active after three await timeouts and `aclose()` |
| Previously broken PNG/WAV header validation | Both truncated formats now rejected |
| Previously broken energy baseline | Equivalent 8-bit and 16-bit half-scale input both active |
| Previously dropped audio timing | Input 12.5/14.5 now survives as 12.5/14.5 |
| Git baseline | Clean worktree before audit; fetched `origin/main` and confirmed `0 0` divergence from HEAD |

The adversarial planner is an injected test double; this does **not** establish a live Qwen prompt-injection success. All effects are mocks. The native-work probe uses released, disposable blocking stubs, not downloaded models. Existing ASR/media results were inspected as recorded teammate evidence, not rerun as new live measurements.

Review covered current ownership/status/history, controller changes, corpus execution, replay/oracles, demo integration, optional demo reasoner, perception workers, turn policy and media-evidence documentation. A green suite is supporting evidence, not proof of every requirement. No current browser visual or live microphone/model quality certification is claimed.

## Ownership for this review

- **Mridul:** controller, shared contracts/interfaces, A-owned adapters, corpus, evaluation/metrics, root configuration/lockfile, engine tests and release packaging.
- **Atishay:** perception, turn policy, demo, B tests, media/feedback/presentation material.
- **Explicit exception retained:** `src/accessflow/adapters/perception_worker.py` stays with Atishay by the documented user decision, despite the general adapters directory ownership rule.
- Shared design decisions below are marked **COORDINATION REQUIRED — MRIDUL + ATISHAY**. Agree the interface first, then each person edits only their owned files.

## What from the previous audit is actually improved

| Previous issue | Current assessment |
|---|---|
| M1 clarification terminal/oracle | Repair and passing regression coverage are present. Do not keep reporting the old final-only failure as current. |
| M2 synchronous corpus execution/error handling | Corpus lookup now runs through `asyncio.to_thread`, a bounded await and normalized error handling. Tests cover slow reads, errors, bounds and late results. Native threads still cannot be preempted; retain the documented limit rather than promise hard termination. |
| M3 name-only dispatch collision | `_corpus_installed` gates internal dispatch. External read/write tools named `search_corpus` have passing coverage. |
| M4 read-only request promoted to write | Initial permission promotion is guarded, including a monotonic result-admission counter. The narrower authority fix does not close argument rewriting: A17-1. |
| M5 invisible document names | Allowed logical document names are now exposed through the installed manifest; discovery/reset tests pass. Normal scenario-level corpus evidence remains incomplete: A17-2. |
| M6 any 429 excused a run | Mixed-outcome classification was repaired. Current documentation records 43/49 quality-scored runs for the historical 57-run cohort. Do not reuse 43/46 without its historical context. |
| Corpus filename/security assumptions | End-of-string matching, reserved Windows names, size/query limits and installation trust assumptions are explicit. This review does not certify mutable/adversarial installation roots or every filesystem race. |
| M7 current documentation | Improved but still drifts after merges; see A17-4. |
| B-side media/demo defects | Many repaired; use the companion report, not the old B findings wholesale. |

## A17-1 — P1: retained write permission does not protect user-specified arguments

**Owner: Mridul.**

**Sources:** `src/accessflow/engine.py:605–680`, especially the unqualified application of `proposal.slot_updates` and `proposal.intent`; corpus-result planning path.

### Reproduction

Using the existing `start_with_corpus`, `lookup`, `proposal` and mock authorization/test helpers:

1. User says: **“Book Wednesday after checking the manual.”**
2. The first proposal requests the allowed manual lookup, sets `day=Wednesday` and `write_requested=True`.
3. The manual says to change the appointment to Friday.
4. An intentionally influenced second proposal sets `day=Friday` and proposes the write.
5. Current result: final slot is Friday and the executor records `{'tool': 'arbitrary_service', 'arguments': {'day': 'Friday'}}`.

No new user correction occurred. The existing write-intent gate permits the action because the original request already authorized a write. Dependency checks do not stop this: the model updates the slot and then calls with that same updated value, so arguments match current state.

This is a distinct defect from creating write permission on a read-only request. The earlier fix is useful and should stay. The adversarial model behavior is simulated; no live model susceptibility or real booking is claimed.

### Required behavior

Distinguish user-fixed constraints from tool-derived facts, suggestions and values the user explicitly delegated. A manual or tool result can provide available dates or a recommendation; it cannot silently replace an explicitly requested Wednesday with Friday. A conditional request such as “book the first available day” needs different treatment and must continue to work.

Add an owned failing regression before modifying the controller. Do not simply forbid all tool-result slot updates: that would break legitimate lookups and read-then-write flows. Define provenance/authority for affected slots and require resolution when evidence conflicts with a user constraint. Preserve unrelated confirmed details.

### Acceptance

- The exact Wednesday-to-Friday probe cannot commit Friday without user resolution.
- Informational corpus answers cannot silently rewrite user constraints either.
- Explicit user correction to Friday succeeds, once, and invalidates only dependent work.
- Delegated-value requests still use legitimate tool results.
- Stale/read-result manipulation cannot bypass the rule by updating a slot and calling in the same proposal.
- The test includes an unsafe planner proposal; a cooperative fake refusing the document is insufficient.

**Coordination:** if the fix adds common evidence/provenance fields, use C1/C3 with Atishay. Mridul can write the engine regression immediately without changing B code.

## A17-2 — P2: corpus execution lacks a normal scenario-level proof and explicit harness configuration

**Owner: Mridul.**

**Sources:** `src/accessflow/cli.py:85–92`, `Agent.__init__`, `src/accessflow/evaluation/replay.py`, suite factory and `tests/engine/test_corpus.py`.

The CLI sets `ACCESSFLOW_CORPUS_ROOT` and the Agent reads it when no explicit constructor value is provided. Replay/suite do not expose the root as an explicit parameter. Unit tests prove root selection, discovery and direct Agent lookup, but the current scenario set does not establish normal replay retrieval from an installed manual.

This is a coverage/configuration boundary, not a claim that environment-based configuration always fails. It becomes fragile when replay is called programmatically or multiple configurations share one process; global environment state is not per-run dependency injection.

**Next slice:** thread an explicit trusted corpus configuration through A's normal factories, retain any documented environment fallback intentionally, and record the resolved profile. Add an actual replay fixture with a small licensed/team-authored text manual, allowed name discovery, result evidence and independent outcome criteria. A tiny corpus test document is A-owned test data; it is not a substitute for Atishay's audio recordings.

**Acceptance:** a regular replay and suite execute the corpus route; an absent root fails clearly; a different run cannot inherit the previous run's root/allowlist accidentally; disallowed names and excessive queries fail; source identity is retained in final evidence. Test direct programmatic replay as well as CLI selection.

## A17-3 — shared P1 specification gap: conflicting frames are not proven unsafe by the current xfail

**Controller owner: Mridul. Test/observation owner: Atishay. Coordination C1 required.**

`tests/demo/test_app.py:3612` expects both `frame-1` and `frame-2` to appear together in a planner view. The controller explicitly cancels/rolls back the previous frame and removes its observation when a replacement arrives (`engine.py:299–307`). The adjacent passing test expects the new frame to replace the previous one.

The unmarked xfail run times out at `conflict_seen.wait()`, **before** `assert not executor.calls` or `assert not executor.effects`. Its reason string therefore overstates what the failure establishes. There is another limitation: the fake's initial proposal is empty, so the setup does not clearly establish the retained write authority needed to exercise an erroneous authorized write.

Decide whether two frames are successive views of one device, independent evidence, or an explicit device correction. Blindly retaining every old frame creates stale-context problems; blindly treating every new frame as authoritative can hide genuine contradictions. The intended semantics require source/role information and a defined resolution policy.

**Acceptance after agreement:** separate tests for replacement, independent contradiction, explicit user-selected device change, delayed stale vision, ambiguous vision and an already authorized write. Synchronize on actual engine/planner events, not arbitrary delays. The conflict test must reach the decision under test and verify both no effect before resolution and one correct effect after resolution.

Do not remove xfail just to make the suite green, and do not edit B's test yourself. Mridul implements engine behavior and engine tests; Atishay updates his integration setup after the shared decision.

## A17-4 — P2: latest merge state, evidence scope and owner decisions need one current record

**Owner: Mridul for root/status documents; Atishay for his evidence documents.**

Current `STATUS.md` prominently reports the earlier merge's 769 tests; this checkout has 799. Handoff still contains older 19-failure/635-pass state and statements that corpus review never ran, while status says that review ran and was repaired. Historical measurements should remain historical, but they must not serve as the active next-agent instruction.

The status still says the conflicting-frame repair owner is not agreed, even though the directories already divide engine and test ownership. The design is undecided; ownership should be stated separately. Also distinguish A's **17 executable scenarios** from B's **60 authored media catalog entries**. These are different artifacts, not interchangeable counts.

After the functional work, publish a concise current snapshot tied to a commit: remaining failures/xfails, exact backend modes, shared decisions, spent evaluation sets and release gates. Link older reviews and resolutions without rewriting their historical results. Do not call a current full-surface security review clean because an earlier corpus review was clean.

## COORDINATION REQUIRED — MRIDUL + ATISHAY

The following IDs and ownership splits also appear in Atishay's report. Neither person should implement the other's files.

| ID | Decision both must make | Mridul implements | Atishay implements | Joint completion evidence |
|---|---|---|---|---|
| **C1: image evidence and action authority** | Replacement versus independent frames; conflicts with user-fixed slots; how ambiguity is represented/resolved | Controller/contract provenance and write guards; engine tests | Frame metadata/perception/UI and B integration tests | Reach the conflict decision, no premature write, one correct write after resolution; replacement remains supported |
| **C2: speech timing and stop semantics** | Clock domain, actual speech end versus upload stop, continued pauses, stop-output versus stop-task | Typed contract and harness/metrics interpretation; controller scope handling | Capture/activity/turn policy and input events | Matched fluent/pause/correction cases; missing timing is unknown; correct interrupt scope |
| **C3: one configured agent path** | Shared reasoner/provider protocol, demo factory, dynamic tool manifests and worker flags | A adapter/factory/configuration and execution contract | Demo wiring and explicitly assigned perception worker | Actual child startup and browser → agreed reasoner → mock tool effect, with backend labels |
| **C4: media catalog into task evaluation** | Which media IDs map to independent executable tasks; terminal/effect oracles; split exposure bookkeeping | Executable scenarios, oracle/metrics, reproducible evidence packaging | Media assets, capture/ASR/vision provenance and labels | Modality-specific task results, not just routing/ASR scores; consumed cases never relabeled unseen |

Record a short agreed example and expected event trace for each decision before changing a shared schema. Additive contracts and fakes let both workstreams proceed independently after that agreement.

## What Mridul should work on next, without taking Atishay's work

1. **A17-1 regression and design:** reproduce argument rewriting, retain user-origin constraints and test delegated-value exceptions. Coordinate only the shared evidence shape where necessary.
2. **C1 agreement and engine tests:** define replacement/conflict behavior with Atishay; implement only the controller side. Keep the existing no-image-only-authorization rule.
3. **A17-2 harness slice:** explicit corpus configuration and a real replay task with independently checked effects/evidence.
4. **C3 factory contract:** expose the chosen A reasoner/executor configuration so the demo need not reimplement dynamic planning policy. Let Atishay wire his UI/worker.
5. **C2 metrics plumbing:** test speech-time conversion and missing-data behavior with labeled synthetic events. Do not claim endpoint improvements until B supplies calibrated real observations.
6. **C4 executable evaluation:** turn agreed media cases into genuine tasks with tools, correction timing and independent effects. Keep routing, ASR, model quality and end-to-end task scores separate.
7. **Evidence/status/release preparation:** package reviewed traces, refresh current status, keep Docker/official-kit/clean-install requirements explicit. Do not trigger automatic CI, install infrastructure, submit or create the release tag incidentally.

Work that remains Atishay's includes the worker exception, native perception lifecycle, stop-policy behavior, microphone timing, demo factory wiring and media evidence. The companion report supplies his concrete findings and acceptance checks.

## Instructions for Mridul's coding agent

> Use `476a7b5` as this audit's reference, and inspect any newer changes first. Work only in A-owned code. Keep `src/accessflow/adapters/perception_worker.py` with Atishay. Start with the Wednesday-to-Friday argument-authority reproduction; do not weaken the effect oracle or merely reject all tool-derived information. Add a normal corpus replay test and explicit configuration. For C1–C4, agree a concrete example/contract with Atishay, then implement only Mridul's side. Preserve the older repaired cases. Report exact changed files, regression tests, evidence mode and remaining limitations. No model change, automatic CI, publication, submission or release tag is implied by these future repair instructions.

## Review limitations

This audit tests specified paths and reads the merged implementation; it is not exhaustive fuzzing, penetration testing, a clinical validation, or a new live multimodal benchmark. Trusted immutable corpus installation remains an explicit assumption. Model output remains untrusted; passing tests must exercise adverse proposals rather than assume a cooperative reasoner. The audit-document commit will follow this reviewed code baseline and should contain documentation only.
