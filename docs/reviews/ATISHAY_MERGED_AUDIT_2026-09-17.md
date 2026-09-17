# AccessFlow: Atishay's merged-code audit

Date: **17 September 2026**

Reviewed shared checkout: **`main`, `476a7b5`**, following merge `0805777`

Companion: [Mridul's audit](MRIDUL_MERGED_AUDIT_2026-09-17.md)

Copy-paste prompt: [ATISHAY_CODEX_PROMPT_2026-09-17.md](ATISHAY_CODEX_PROMPT_2026-09-17.md)

## Assessment

The B-side merge contains substantial repairs. Do not treat the earlier 16 September report as a list of entirely unfixed issues. The current merged suite is **799 passed, 1 xfailed**; Ruff passes. This is the code now present in the shared repository, not an assumption about further work on Atishay's machine.

Fresh probes confirm that header-only PNG/WAV inputs are rejected, supplied audio timestamps survive translation, and the energy baseline treats equivalent 8-bit/16-bit signals consistently. Code/tests also show corrected browser utterance revisions, safe text rendering, input bounds, interruption controls, AudioWorklet capture and stronger worker queue management.

The remaining problems are at integration and lifecycle boundaries: native work survives timeout/close; broad speech stop detection confuses different actions; microphone upload still lacks actual speech timing; the evaluation worker remains unwired; and the optional browser reasoner is a separate, weaker protocol implementation than A's reasoner.

This was review-only. No B implementation or tests were changed. No live ASR/vision/model or microphone session was executed during this audit. Existing recorded B measurements are attributed to their original runs, not claimed as new results.

## Ownership

Atishay owns perception, turn policy, demo, their tests and media/feedback/presentation material. **The explicit exception assigning `src/accessflow/adapters/perception_worker.py` to Atishay remains in force.** It does not transfer the other adapters, controller, contracts, root lockfile or evaluation harness to him.

Mridul owns those A components and the new argument-authority defect in his report. Do not patch his engine to make a B test pass. Use the C1–C4 coordination items below whenever the change needs a common decision.

## B17-1 — P1 integration gap: evaluation worker still rejects vision options

**Owner: Atishay, explicit worker exception.**

**Source:** `src/accessflow/adapters/perception_worker.py`, `main()` and `_serve`.

The parser still accepts only `--model-path`, and the worker constructs `LocalPerception` without the vision-provider seam. The parent CLI's configured vision flags therefore remain incompatible with the child. Browser vision improvements do not fix this separate evaluator/process route.

**Required slice:** accept the agreed provider/model/URL/deadline options, construct/pass the provider, preserve `none` as the default, stdout isolation, JSONL protocol and lifecycle behavior. Coordinate exact configuration with Mridul under C3. There are now A and B vision providers with different interfaces (`url`/`timeout` versus `endpoint`/`timeout_s`, and chat versus generate API paths); choose the contract explicitly instead of forwarding similarly named options blindly.

**Acceptance:** test actual child startup, not just direct provider calls; default audio path works; a configured frame yields an observation through the process adapter; invalid options/backend failure are explicit; no canned caption substitution. Run live inference separately only when the agreed model is available, and record its identity honestly.

## B17-2 — P1 lifecycle defect: timeout frees the async worker while native work continues

**Owner: Atishay for `LocalPerception`; coordinate process reuse with A if needed.**

**Sources:** `src/accessflow/perception/local.py:_run_with_timeout`, `_LatestWorker._run`, `aclose`, `_transcribe`.

`asyncio.to_thread` runs the native provider. On timeout, canceling its asyncio wrapper does not stop the underlying thread. `_LatestWorker` then accepts more work, and `aclose()` can return while those native calls continue.

**Fresh bounded reproduction:** use an injected transcriber waiting on a threading event; set `timeout_s=0.02`; submit three distinct audio utterances sequentially. Each await times out. After `aclose()`, the probe observes **three active native calls, peak concurrency three**. All gates were then released and the probe cleaned up. No speech model was loaded.

This defeats the intended one-worker resource bound and can concurrently call one native ASR model after repeated timeouts. Even when stale observations never enter the controller, CPU/memory/file activity may continue after session shutdown.

**Required behavior:** choose an explicit native-work lifecycle. Either retain a real in-flight permit until the native call finishes, or use a killable process boundary for hard cancellation. A canceled await must not create unlimited replacement native work. Make `aclose` semantics clear: bounded close with tracked outstanding work is different from “all native activity stopped.” Account for session media files while providers may still read them.

**Acceptance:** repeated timeouts cannot exceed the declared native concurrency limit; stale work yields no observation; close does not silently leave untracked work; new sessions remain usable; provider errors remain bounded. Tests must track the actual injected thread/process, not only canceled asyncio tasks. Do not edit A's adapter without agreement.

## B17-3 — P1 semantic mismatch: speech stop detection collapses distinct requests

**Owner: Atishay's policy; controller/contract scope requires C2 with Mridul.**

**Source:** `src/accessflow/turn_policy/heuristic.py`, `_STOP_REQUEST` and its branch.

The prefix regex `^\s*(stop|cancel)\b` returns `TurnDecision(kind='stop')` for all of these fresh probe inputs:

```text
Stop speaking
Cancel noise reduction on this device
Stop
```

The controller's stop-decision branch clears retained write intent and cancels pending writes. It cannot distinguish a speech-output interruption from canceling the task through this decision. “Cancel noise reduction” may itself be a device command rather than an instruction to abandon the interaction. Partial hypotheses can also trigger the branch before the phrase finishes.

**Required behavior:** define conservative scope handling with Mridul. Preserve separate explicit UI interruption scopes. Do not infer task cancellation from every prefix or every unfinished partial. Ambiguous cases should remain unresolved or be clarified according to the agreed policy.

**Acceptance:** stop-speaking stops output without silently deleting an authorized task; cancel-this-booking cancels that task; device commands and quoted content are not mistaken for global cancellation; partial “stop…” followed by continued speech follows a specified rule. Test both emitted policy decisions and resulting controller behavior after the C2 agreement.

## B17-4 — P2: microphone capture is real, but actual speech timing is still missing

**Owner: Atishay capture/perception; C2 for metric integration.**

**Sources:** `demo/index.html:stopMicrophone`, `LocalPerception.observe`, `HeuristicTurnPolicy.update`.

The page now records real PCM and uploads WAV, which closes the old fake-microphone finding. However, the upload includes `data_base64`, filename and utterance ID, not `speech_start`/`speech_end`. The server can now preserve these fields when supplied, but the actual browser capture path supplies neither.

Manual stop time is not actual speech end. Whole-file ASR still produces `final=True`, while the controller calls `TurnPolicy.update(observation, view)` without the optional `timing` argument. A standalone activity summary or VAD table does not connect endpointing to actual conversational turn completion.

**Required slice:** preserve capture timing separately from transport timing; define/calibrate speech-end evidence and continued-pause behavior through C2. If only whole-file upload is supported for now, label that limitation explicitly. Do not populate speech-end metrics with upload receipt or default zero and call them live latency.

**Acceptance:** nonzero capture timestamps survive end to end; missing speech-end data remains unknown; long internal silence followed by continuation is not mistaken for a finished live turn; fluent speech measures added waiting time. Compare matched short/long-silence and proposed policies before claiming a patience advantage.

## B17-5 — P2: browser reasoning duplicates A's protocol and can accept an empty plan

**Owner: Atishay's demo wiring; C3 with Mridul for shared factory/protocol.**

**Sources:** `demo/reasoner.py:OllamaReasoner`, `_prompt_for`, `_request_plan`; `demo/app.py:621–627`.

The optional demo reasoner asks for a JSON object “matching the AccessFlow PlanProposal schema” but does not include that schema. It sends `format='json'`, then validates only the static model. A mocked provider response with `response='{}'` is accepted as a proposal with no calls, no answer and all default flags. The captured empty-session prompt contains no `slot_updates` schema field.

It also omits shared planner context such as ledger calls, active request identity and required-next-step handling. This does not establish that the controller can be bypassed; it means the demo is testing a different, less-informed planner than the selected A profile. A's bounded no-progress recovery may still reject/stall such output.

The actual WebSocket app also starts with `Start()` containing **no tool manifests**, `FakeTools` and `FinalFlagPolicy`. Tests that manually construct an Agent with service tools do not prove that the served UI can demonstrate a booking workflow.

**Required behavior:** agree an A-owned configured agent/reasoner factory, then wire it through the B-owned demo. Preserve a clearly labeled mock default if desired. Share actual dynamic schema/continuation logic rather than growing a competing copy in `demo/reasoner.py`. Select backend/profile explicitly; never silently substitute a local model for the chosen hosted profile.

**Acceptance:** the served WebSocket route receives agreed manifests, performs one real configured planning path with mock external effects, handles corrections and shows actual state/effects. Empty/malformed model output is rejected or explicitly recovered. Observed backend labels and the reported evaluation profile match.

## B17-6 — shared test defect: the frame-conflict xfail fails before testing a write

**B-owned test:** `tests/demo/test_app.py:3612–3733`; controller semantics are A-owned. **C1 required.**

Running the test with `--runxfail` fails at line 3725 waiting for both frames to appear in the planner context. The engine intentionally removes the previous frame, and the adjacent passing test explicitly expects that replacement behavior. The xfail never reaches its no-call/no-effect assertions.

Its initial fake plan is also empty, so it does not clearly establish the retained write authorization needed to test an unsafe conflict-driven action. A passing no-write assertion could otherwise be explained by missing permission rather than conflict resolution.

Do not label this as demonstrated premature booking. Agree replacement versus independent/conflicting evidence with Mridul. Then update this B test so it reaches the intended decision with a valid precondition, asserts no effect before resolution, and asserts the right effect after resolution. Keep a separate passing replacement test and stale-frame test. Do not edit the engine yourself or simply remove the expected-failure marker.

## B17-7 — evidence handoff: 60 media cases are not 60 completed service tasks

**B owns media/provenance; A owns executable task oracles. C4 required.**

The new catalog is useful: 30 text, 18 audio and 12 image entries, with generated-media provenance and stored results. Its own replay documents correctly disclose that:

- Offline replay uses injected ASR/vision labels to verify routing and metadata.
- The mixed 60-case Agent run uses real ASR, injected vision, mock informational reasoning and no state-changing tools.
- All cases are run in one Agent session; this does not demonstrate 60 independent task outcomes or per-case session isolation.
- VAD timing tables cover all 18 audio cases, including entries labeled held out.

Preserve those honest qualifiers. The split label alone no longer establishes untouched ASR/VAD evidence for cases already measured. Track exposure per experiment/component; do not retroactively claim the catalog proves held-out end-to-end reasoning or live vision grounding.

**Required handoff:** provide stable media IDs, hashes, intended input timing, provenance and already-used split status. Agree A's task/terminal/effect expectations separately. Keep clinical/accessibility benefit claims limited until actual feedback supports them. Generated team speech is not representative clinical data.

## COORDINATION REQUIRED — MRIDUL + ATISHAY

These are the same coordination IDs as Mridul's report. Neither person should implement the other's files.

| ID | Decision both must make | Mridul implements | Atishay implements | Joint completion evidence |
|---|---|---|---|---|
| **C1: image evidence and action authority** | Replacement versus independent frames; conflicts with user-fixed slots; how ambiguity is represented/resolved | Controller/contract provenance and write guards; engine tests | Frame metadata/perception/UI and B integration tests | Reach the conflict decision, no premature write, one correct write after resolution; replacement remains supported |
| **C2: speech timing and stop semantics** | Clock domain, actual speech end versus upload stop, continued pauses, stop-output versus stop-task | Typed contract and harness/metrics interpretation; controller scope handling | Capture/activity/turn policy and input events | Matched fluent/pause/correction cases; missing timing is unknown; correct interrupt scope |
| **C3: one configured agent path** | Shared reasoner/provider protocol, demo factory, dynamic tool manifests and worker flags | A adapter/factory/configuration and execution contract | Demo wiring and explicitly assigned perception worker | Actual child startup and browser → agreed reasoner → mock tool effect, with backend labels |
| **C4: media catalog into task evaluation** | Which media IDs map to independent executable tasks; terminal/effect oracles; split exposure bookkeeping | Executable scenarios, oracle/metrics, reproducible evidence packaging | Media assets, capture/ASR/vision provenance and labels | Modality-specific task results, not just routing/ASR scores; consumed cases never relabeled unseen |

Each decision should produce one written example/event trace before code changes. While awaiting a decision, Atishay can still implement the native-work regression and agreed worker parser wiring without changing Mridul's code.

## Suggested B-side order

1. Compare this report to Atishay's actual current branch; preserve newer work.
2. Fix the native-work lifecycle with thread/process-aware tests.
3. Complete the assigned process-worker integration against agreed options/provider.
4. Agree C1/C2; repair the conflict test setup and speech stop/timing behavior in B-owned files.
5. Agree C3; connect the served UI to the shared agent configuration instead of expanding a second planner protocol.
6. Deliver C4 media/evidence mapping and exposure status; run real image/model experiments only when available and explicitly labeled.

Run owned tests and then the full merged suite after integration. Keep mock, injected, ASR-only, live vision and end-to-end task results separate. No source repair was made by this audit, and no “all security issues closed” verdict is implied by the green tests.
