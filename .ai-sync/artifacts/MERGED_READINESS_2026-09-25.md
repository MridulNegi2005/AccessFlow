# Merged code readiness review - 25 September 2026

Later user decision on 25 September: [confirmed D1-D4 requirements](../PRODUCT_DECISIONS_2026-09-25.md)
now settle stop/clarification, hands-free voice, End session and ordered multi-image
history. They supersede open product questions or single-image recommendations in
this earlier review. The updated execution brief is the current implementation
instruction; the audit evidence below remains historical, not a claim of new fixes.

## Verdict

Both workstreams are integrated in the requested order. The combined regression
suite is green with documented exclusions. This is **not yet a code-complete,
submission-ready release**. Atishay delivered useful changes, but his latest
handoff explicitly leaves live interruption, shared runtime adoption and live
vision acceptance open. Those are integration/completion work, not merely
accuracy improvements.

This review changes documentation and adds reproducible diagnostic probes only.
It does not fix either owner's implementation, activate workflows, submit anything,
create a release tag, or alter Atishay's branch.

## Exact integration

| Item | Commit |
| --- | --- |
| Previous main | `749fe23aac10e5d79b74f75fdb257500702fee65` |
| Mridul source | `81699c9c1d656e3ba600372fa168d3e330140749` |
| First merge into main | `00e1975` |
| Atishay source | `469e590296e494a9457730a067595f5b3ceef426` |
| Second merge; tested implementation | `dcd9756` |

Both were real merges preserving history. The only conflict was
`.ai-sync/handoff.md`; both sets of checkpoint text were preserved. Source files
had no merge conflicts. Historical claims such as "unmerged", "uncommitted" or
"push own branch only" describe earlier checkpoints, not this integration.

## Verification performed here

Python **3.11.15**, Windows, repository environment with audio dependencies:

| Check | Result | Scope |
| --- | --- | --- |
| Entire pytest suite | **1368 passed, 4 skipped, 1 xfailed**, 82.13 s | Combined branches |
| Installed ASR opt-in tests | **2 passed**, 9.99 s | Real base.en CPU INT8; generated audio; mock reasoning/no tools |
| Ruff | Passed | Entire repository |
| Four Node browser regressions | All exit 0 | Correlation, speech lifecycle, mic permission, mic disconnect |
| Development replay | **4/4** | Offline fakes; not Samsung scoring |
| Merge whitespace check | Passed | Previous main to merged source |
| Unmasked known xfail | **Still fails** | Timeout waiting for simultaneous conflicting-frame context |
| Fresh audit probes | Reproduced issues below | Deterministic synthetic/injected inputs, not human/live-model results |

The four skips were two native-symlink cases unavailable on this Windows setup
and the two opt-in ASR tests; the latter were run successfully separately.
Two dependency deprecation warnings remain. They did not fail this run.

Evidence and reproduction commands are in
[`../evidence/merged-2026-09-25/`](../evidence/merged-2026-09-25/README.md).
No new physical-microphone session, hosted reasoning benchmark, live vision score,
Docker execution or full official repeated evaluation was performed in this review.

## Findings and ownership

### B25-1 - High: backend failure before an observation is hidden by the browser

**Owner: Atishay.** `demo/index.html:1679-1686` requires an engine error's causal
ID to be present in `requestEventIds`. That map is populated by successful final
`demo_observation` messages at approximately line 1753. Server-generated input IDs
are not otherwise acknowledged to the browser: `demo/app.py` sends media receipt
with source ID only.

The actual WebSocket route with a valid WAV and injected ASR exception emits
`demo_status`, media receipt, then `error(code=backend_failure, detail=RuntimeError,
caused_by_event_id=...)`; it emits no observation. The real browser `show()`
function drops this error, leaves the task pending, and the user only gets the
generic **90-second** timeout. This is a regression in the newly tightened error
filter, not an ASR accuracy problem.

Fix the owned browser/server acceptance correlation before perception starts.
Keep stale-task rejection. Render safe known error codes; controller errors use
`code`/`detail`, while the current browser mostly expects `message`.
Do not expose arbitrary exception details or accept every uncorrelated error.
See the separate B handoff for acceptance tests.

### B25-2 - High: stop meanings are only partly implemented

**Both Mridul and Atishay must coordinate.** B owns classification and playback;
A owns any shared decision/controller change.

The new policy correctly no longer treats "Cancel this booking" or
"Stop the washing machine" as global task cancellation. But bare **"Stop"** and
**"Cancel"** now return `complete` rather than the previous `stop`, so the normal
planner runs. **"Stop speaking"** returns `continue`; the actual controller plans
it but emits no `stop_output` signal. By contrast, **"Cancel this task"** enters
stopped state and emits `stop_output=True` without planning.

The browser's real `show()` also does not consume controller `stop_output=True`;
the probe recorded zero playback cancellations. Button-driven local cancellation
exists, so this is specifically a missing controller-to-playback integration.
These observations do not prove a real model will perform a wrong action, but they
do prove there is no deterministic bare-stop/output-stop behavior in this path.

Agree the meaning of bare stop in an active conversation, preserve ordinary device
commands, and connect explicit output-only stop without discarding useful task
state. Do not repair this by restoring the old blanket `^stop|cancel` classifier.
Keep Samsung's explicit interruption route working; these findings concern
recognized speech and browser playback, not a claim that all interruptions fail.

### C25-1 - Completion gap: browser still differs from the submission runtime

**Both must coordinate.** `demo/app.py:613-657` constructs `DemoPerception`,
`FinalFlagPolicy`, a mock reasoner by default (or its separate optional Ollama
reasoner), and fake tools. It does not adopt A's `build_configured_agent` with
the selected Qwen configuration. B's human-mic screenshot proves capture, local
ASR and an echo from the mock reasoner, not a completed real-agent voice task.

A has now supplied and merged the common factory, actual-ASR warm-up and Samsung
MP3 admission. B should pull this main and use the documented seam rather than
wait for an already-completed factory or rebuild planning in the frontend.
A owns an additive hook if observation callbacks or manifests require one.
B owns the minimal browser integration and end-to-end test. Keep mock effects
clearly labeled; real external bookings are not needed.

### C25-2 - Completion gap: live capture/endpointing remains unimplemented

**Both must coordinate.** Current browser capture holds the WAV until Finish;
the microphone control is locked during an active task. No speech-triggered
barge-in, live partial ASR or calibrated endpoint is established by these changes.
B's own microphone report states this clearly. B's timing replay and raw decoder
metadata are useful diagnostics but do not feed live agent decisions.

Separate two routes: Samsung already supplies explicit `end_of_turn` and
interruption events through A's adapter; the browser needs B's live activity and
capture integration. Do not invent speech end timestamps or equate decoder word
offsets with the session clock. A's `SpeechStatusEvent` is already available and
must be considered when agreeing a narrow browser adapter.

### A25-1 - Completion gate: current merged package/platform needs verification

**Owner: Mridul; B assists with perception failures.** Rebuild from merged source,
verify the official import/setup and media paths in the declared deployment, and
run the official public evaluation repeatedly at its normal timing. Existing
24 September package/setup results remain historical evidence for that source;
they do not certify this newly merged package or full task completion.

Docker/Podman are still absent on PATH here. The generated Docker recipe has not
been executed. A must verify the actual supported platform, vision service/model
provisioning, cleanup, setup budget, scenario budget and failure handling. Do not
claim a Docker pass from static recipe tests or a Windows venv run.

### C25-3 - Unresolved acceptance: visual completion and frame semantics

**Both must coordinate.** Prior real vision evidence missed the official tail;
this review did not rerun it. B owns provider/worker speed and frame grounding;
A owns package service/configuration and controller completion. Deliver an actual
image-grounded final under unchanged evaluator timing before treating vision as
complete. This is a functioning-path issue before fine accuracy tuning.

The retained `test_conflicting_frames_require_resolution_before_write` xfail was
unmasked here. It times out at `tests/demo/test_app.py:3894`, waiting for a context
containing both old and new frames. The controller intentionally replaces the old
active frame, and the neighboring replacement test passes. This particular
failure is **not evidence that an unsafe write happened**. Agree whether sequential
frames replace each other or represent multiple simultaneous evidence items;
A owns that semantic contract, B owns updating the acceptance test accordingly.
Do not remove the xfail or certify conflict handling without a valid replacement
test and a documented decision.

## Completion-first work order

1. **Atishay independently:** fix B25-1 correlation/error recovery, wire controller
   output-stop into playback, preserve existing browser recovery tests. No styling work.
2. **Together, small interface decision:** settle stop scopes and capture clock /
   finality / activity metadata. Record examples and defaults in CONTRACT_PROPOSALS;
   do not change the meaning of existing `final` flags silently.
3. **In parallel:** A rebuilds and validates the merged submission package/runtime;
   B adopts that runtime in the minimal test UI and implements the agreed live voice
   path. Each side uses deterministic fakes for unfinished seams.
4. **Together:** run microphone correction while a response/tool is pending, plus
   actual WAV/MP3 and PNG through the submission path. Exercise timeout, denial,
   disconnect, late result and restart. Do not use canned inference to close gates.
5. **A:** complete repeatable official-kit evaluation, platform/install verification,
   manifest/secret checks and a precise supported launch recipe. Address runtime or
   protocol failures before tuning model prompts, larger models or ASR accuracy.

PPT, video, registration and final submission/tag are outside this code milestone.
Submission-ready code means a reproducibly installable, configured agent with all
required input paths, cancellation/failure handling and a tested official entry;
it does not mean every accuracy metric must be perfect. Conversely, a large green
unit-test count does not establish those delivery properties by itself.
