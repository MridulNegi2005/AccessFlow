# My execution instructions for AccessFlow - 25 September 2026

## Who is speaking and what I want

I am **Atishay**. These are my instructions to my coding agent. **Mridul** is my
teammate and owns the engine, shared contracts and submission infrastructure.

I want you to finish my working voice/perception integration against our merged
project. Prioritize submission-complete code before accuracy experiments. Do not
spend this session on design, animations, additional UI variants, slides or a video.
Do not stop after a plan or another audit: implement and verify work in my ownership.
Continue independent work when one specific interface needs Mridul's input.

Be direct about outcomes. A pushed commit, a clean test suite, an ASR transcript,
a screenshot or a mock echo is not proof that the requested product works.
Do not tell me my part is done while a required capability below is missing.
Do not blame or credit a model name in place of technical evidence.

## The end product I expect

Using our existing minimal browser, I can deliberately enable my microphone,
speak a request, pause and correct it, and receive a substantive answer from the
**same configured agent used by our submission**, with actual backend labels.
Speaking during output or pending work reaches the agreed interruption path.
An outdated request cannot become an action or replace the corrected result.

For example: with a test timezone and calendar manifest explicitly configured,
I say "Schedule the meeting on Tuesday at 3 PM ... actually Wednesday at 5 PM."
The agent resolves the corrected request or asks about genuinely missing details.
In a fully specified deterministic test, exactly one confirmed **mock** calendar
effect uses Wednesday 17:00; no Tuesday effect is committed. The interface shows
what actually happened, not a hard-coded meeting card or a transcript echo.

The same integrated runtime must also answer an informational request and process
an actual PNG. Errors must be visible and recoverable. No real calendar booking,
payment, external service action or private recording publication is needed.

This is the desired integrated result. It includes shared dependencies: you must
not quietly implement Mridul's part or mark my portion complete while integration
is untested. Identify the precise dependency and prove what works independently.

## 1. Pull the merged code before debugging anything

At the time of this brief, main contains the ordered merges of Mridul `81699c9`
and my `469e590`, implementation merge `dcd9756`, and review `f103008`.
These are minimum known baselines, not instructions to pin an older checkout.

1. Inspect `git status`, current branch, remote URL and recent history. Preserve
   uncommitted changes; do not reset, clean, overwrite or auto-stash unknown work.
2. Run `git fetch origin --prune`. Inspect divergence for local main and my branch.
3. With a clean tree, update main using `git switch main` and
   `git pull --ff-only origin main`. If main has unique local commits, inspect them
   instead of discarding them to force a fast-forward.
4. Switch to `atishay/perception`, reconcile its remote history without rewriting
   it, and merge **the fetched `origin/main`** into it. Create a tracking branch only
   if mine does not exist locally. Do not cherry-pick isolated files out of main.
5. Verify `git merge-base --is-ancestor origin/main HEAD` succeeds. Record the full
   main SHA and my branch SHA. Preserve both sides of any meaningful conflict.

Do not work against my pre-merge clone and then report that Mridul's factory or
Samsung audio route is missing. They are now on main. If fetching fails, report
the exact failure and distinguish it from missing implementation.

Read, in this order:

- `AGENTS.md`, `.ai-sync/handoff.md`, current `docs/STATUS.md`, and the relevant
  recent `.ai-sync/context.md` entries and artifacts.
- `docs/reviews/MERGED_READINESS_2026-09-25.md`.
- `docs/reviews/ATISHAY_COMPLETION_2026-09-25.md`.
- `docs/CONFIGURED_RUNTIME_2026-09-24.md` for the factory/API, then the newer
  `docs/SAMSUNG_AUDIO_ADMISSION_2026-09-24.md` and
  `docs/MEDIA_COMPLETION_COORDINATION_2026-09-24.md` for completed audio work.
- `docs/PACKAGE_HOSTING_2026-09-24.md`, `docs/CONTRACT_PROPOSALS.md`, and the actual
  source files implementing the routes you will use.

Treat old dated "next steps" as historical when a newer document/code completes
them. Read the original kit's WALKTHROUGH, PROTOCOL, SCORING and SUBMISSION files
when available. Mridul's kit is outside the repository at
`Samsung GenAI/participant-kit/participant-kit`; that Windows path need not exist
on my machine. Locate my copy or request the kit location. Do not commit organizer
assets or say the organizer has not supplied the kit merely because my copy is absent.

## 2. Ownership is strict; debugging visibility is not restricted

My editable areas are perception, turn policy, demo, their tests and feedback docs:
`src/accessflow/perception/`, `src/accessflow/turn_policy/`, `demo/`,
`tests/perception/`, `tests/demo/`, and my workstream handoff.
The explicitly assigned exception is `src/accessflow/adapters/perception_worker.py`.

Mridul owns shared contracts/interfaces, engine, model/execution adapters, process
parent, Samsung adapter, evaluation infrastructure, dependencies/lockfile and packaging.

**Read and run Mridul's code to debug my integration.** Trace a failing request
through the browser, WebSocket, input queue, perception child, controller, reasoner
and output queue. Record the first incorrect boundary, not just the final symptom.
Reading his files and running the full suite is required; editing his implementation
is not authorized by this brief. Do not duplicate his planner, authority checks,
retry logic or action ledger inside my frontend to avoid an interface change.

**Both Mridul and I must coordinate** where a shared contract/controller change is
necessary. Prepare a narrow proposal with failing input, expected output, relevant
source locations, compatibility/defaults and an owned reproducer. Say exactly what
Mridul needs to implement and what I can finish without it. Do not wait on a vague
"C24 coordination" label when the existing API already supports the work.

## 3. Establish a reproducible starting point

Use Python 3.11 and the existing locked environment. Inspect interpreter/dependency
versions and model paths. A broken local launcher is an environment problem to
diagnose, not a reason to silently change our supported Python version or lockfile.
Request missing secrets securely; never print, commit or copy them into reports.
Use existing approved providers/models. No paid fallback, hidden mock fallback or
automatic model change to turn a failed run green.

Run baseline checks relevant to each slice before editing. The merged review
recorded 1368 pass / 4 skip / 1 xfail, with 2 real-ASR tests passing separately.
Those numbers are historical, not a quota to match or proof for my new commit.

Reproduce the current findings from repository root:

```powershell
python docs/evidence/merged-2026-09-25/probe_error_transport.py
node docs/evidence/merged-2026-09-25/probe_browser.cjs
python docs/evidence/merged-2026-09-25/probe_stop.py
```

These probes assert **the old problematic behaviour**. Their successful exit is
not the desired product result. Preserve this historical evidence; write new
permanent acceptance tests which fail before the repair and pass after it.
Do not edit the probe or expected result simply to say the bug is fixed.

## 4. Implement these slices in this order

### Slice A: observable, correctly correlated failures

Fix the reproduced error-filter regression first. A valid WAV whose ASR fails
produces an engine error before any `demo_observation`. The browser does not yet
know its server-generated event ID, drops the error and waits 90 seconds.

Establish a bounded task/source/revision/event association at input acceptance,
before perception. Carry that association through failure and recovery. Keep
previous-task, previous-session and stale-revision protection. Handle defined
`code`/`detail` versus browser `message` shapes with safe user-facing text.
Do not expose raw exception content or accept every uncorrelated error.

**Done means:** an injected ASR/vision failure before observation produces a visible
current-task error and usable controls as soon as that failure is delivered; a
subsequent request succeeds. It must not rely on the 90-second fallback timer.

### Slice B: stop semantics and playback connection

Preserve the useful distinction between "Cancel this booking", "Stop the washing
machine" and "Cancel this task". Bare "Stop"/"Cancel" currently go to planning;
"Stop speaking" currently produces no output-stop signal. The browser also ignores
controller `stop_output=True`, although local button cancellation exists.

**Both Mridul and I must coordinate** the meaning of bare stop, output-only stop,
task stop and partial hypotheses. I own classification and playback; he owns any
new shared decision/controller behaviour. Wire existing authoritative stop-output
events into playback with correct current-session handling now. Do not reintroduce
the blanket stop-prefix regex or translate every stop into a new task cancellation.

**Done means:** output-only stop cuts playback and preserves the agreed task state;
task cancellation invalidates pending work; old callbacks cannot restart speech;
normal cancellation/device requests still reach reasoning. A committed effect is
reported honestly, never described as undone merely because output was stopped.

### Slice C: adopt the shared real agent

Use `src/accessflow/adapters/configured_agent.py::build_configured_agent` from main.
Read its actual signature, warm-up, lifecycle and configuration instead of guessing.
Mridul's documentation shows root, authorization, executor and tool documentation;
the browser must supply declared mock external tools/authorization and send matching
manifests. Samsung's harness-executed tools are a different adapter arrangement.

Keep an explicit fake mode for fast independent tests. In real mode use the actual
configured ASR, reasoning and vision; display their provenance. Do not leave
`DemoReasoner`, `FinalFlagPolicy` or a separate planner on the real path and claim
it is equivalent. If process observation callbacks are missing, propose an additive
hook to Mridul and prove my UI against a fake implementing that exact seam.

Close session-owned workers, microphone tracks and audio contexts on failure and
disconnect. Do not kill unrelated model services or leak a child after a failed setup.

**Done means:** the same recorded input through the browser adapter and common
agent has matching request identity and intended outcome with the same configuration.
A mock echo or fixture-provided answer cannot satisfy this gate.

### Slice D: minimum live microphone and image behaviour

Capture currently uploads a finished WAV. That is useful upload/ASR support, but
not streaming, acoustic endpoint detection or speech-triggered barge-in.
Implement the smallest agreed live capture/activity path that interrupts current
output/work, preserves an internal pause and admits a superseding corrected request.
Continuous streaming partial ASR is not a separate requirement if the chosen bounded
capture design genuinely meets these behaviours; describe its actual limitations.

**Both Mridul and I must coordinate** capture/session timebases, source/revision,
pending speech and finality. Use the existing controller-only `SpeechStatusEvent`
where appropriate; never feed it into perception or invent audio timestamps.
Samsung's explicit `end_of_turn` bridge already exists and is not evidence that my
browser endpointing works. Raw decoder probabilities are not calibrated confidence.

Run the actual image backend on PNG bytes and reach a substantive, grounded answer.
Measure the full path, not just provider startup. Address missing responses/timeouts
before broad vision accuracy tuning. Do not lengthen official evaluator timing or
use filenames/reference captions as recognition. Worker options requiring package
changes are a joint interface task, not permission to edit Mridul's configuration.

## 5. Acceptance gates: explicit cases, not an inflated test count

Create an acceptance checklist with stable IDs below, test names/commands and result
paths. Existing tests may satisfy a case if they assert the actual required outcome.
Do not create 20 superficial duplicates merely to hit a number.

### Gate 1: all 20 deterministic behavioural cases pass

| ID | Required behaviour |
| --- | --- |
| E01 | Valid WAV + ASR exception before observation: current failure displayed, controls recover. |
| E02 | Empty ASR transcript: honest recoverable failure, no invented request/effect. |
| E03 | Valid PNG + vision exception before observation: current failure displayed. |
| E04 | Old-task or old-session failure cannot terminate a new task. |
| E05 | Duplicate current failure is handled once; next valid request succeeds. |
| E06 | One failed media item with another successful item is not silently presented as full success. |
| S01 | Current output-stop event calls playback cancellation without waiting for an LLM. |
| S02 | A late TTS callback after stop cannot resume or relabel stopped playback. |
| S03 | Output-only stop preserves the jointly agreed task context. |
| S04 | Task cancel during pending mock write produces no subsequently accepted obsolete effect. |
| S05 | Booking cancellation and washing-machine stop remain ordinary requests. |
| S06 | Bare stop and incomplete stop hypotheses follow documented agreed semantics. |
| V01 | Fully specified Tuesday-to-Wednesday correction: one Wednesday 17:00 mock effect, zero Tuesday effects. |
| V02 | Internal pause followed by continuation does not finalize an unfinished request. |
| V03 | Repetition without correction neither duplicates an effect nor silently changes quantity. |
| V04 | Superseded delayed ASR cannot overwrite newer speech or restore stale authority. |
| L01 | Pending/denied microphone permission is recoverable; late grants leave no live track. |
| L02 | Disconnect while recording/processing cleans up owned capture/session resources. |
| L03 | Reconnect starts cleanly; old-session output cannot appear as the new result. |
| L04 | New frame supersedes late old-frame output under the agreed frame contract. |

Use injected failures, deterministic clocks and gates to control races. Test seams
through the real controller where required, even though inference/tools are fakes.
Report a shared-controller failure as a joint blocker with a reproducer; do not
weaken assertions or implement Mridul's fix inside my UI.

The old conflicting-frames xfail expects simultaneous old/new frames while the
controller replaces the old frame. **Both must resolve that semantic mismatch.**
Do not delete its marker or claim it proves an unsafe effect without inspecting
the actual failure. Keep any unresolved acceptance explicitly open.

### Gate 2: nine recorded runs through real inference

Use three fully specified development cases, **three attempts each**:

1. Recorded WAV with pause/repetition and Tuesday-to-Wednesday correction.
2. A simple informational WAV with an independently checkable answer.
3. Actual PNG plus spoken/text question requiring information from its pixels.

Use real installed ASR, selected reasoning and declared vision on applicable paths.
External tools remain mock. Every attempt must record commit/configuration, backend,
input provenance/hash, output/causal IDs, outcome, elapsed time and failure reason.
Predeclare the small fixture set; do not throw away failures or substitute easier
cases after observing results. These are exposed development smokes, not held-out
evaluation or a substitute for Mridul's official repeated Samsung run.

**Minimum functional gate:** at least one genuine completed task for each of the
three paths, all nine outcomes retained, zero known wrong/duplicate/obsolete mock
writes. A path with no completion, a crash, protocol break or unhandled failure is
not complete. Record remaining recognition/answer variability separately for later
accuracy work; nine perfect answers are not a prerequisite for reporting a working
path, and one successful answer is not evidence of reliable accuracy.

If credentials, quota or models prevent a run, mark it NOT RUN with the exact
dependency. Do not silently substitute fake inference, buy quota or rerun endlessly.

### Gate 3: three physical-microphone checks after implementation

With my agreement to capture speech, run: (M01) pause then correction, (M02) speak
during audible output, (M03) correction during an intentionally delayed mock tool.
Record browser/device, configuration, recognized text, corrected state, output-stop
and substantive-response timing, effects and any observed limitations. Separate
local stop-signal dispatch from actual audible playback stopping.

All three must demonstrate their named behaviour before claiming physical-mic
acceptance. A screenshot of ASR plus mock echo is insufficient. If I am unavailable,
finish independent code/tests and label this gate NOT RUN; do not invent a manual
test or ask for recordings before there is implemented behaviour to verify.
Anonymized written observations are acceptable; public voice recordings are not
required. Synthetic audio cannot be relabeled as a human test.

### Gate 4: final combined regression and reproducibility

Use my final implementation commit, Python 3.11 and the supported environment:

```powershell
python -m pytest -q
ruff check .
node tests/demo/answer_correlation_check.cjs
node tests/demo/speech_lifecycle_check.cjs
node tests/demo/microphone_pending_check.cjs
node tests/demo/microphone_disconnect_check.cjs
```

Run any new owned regression scripts too. Run installed-model opt-in tests using
an explicit valid `ACCESSFLOW_TEST_WHISPER_MODEL_PATH`; do not count skipped tests
as passes. Record exact skips/xfails/warnings and whether they affect my deliverable.
Provide one tested launch recipe, configuration names without secrets, expected
backend labels, model installation prerequisites and a restart/cleanup check.
Respect the kit's unmodified timing and verify its current limits; the documented
setup/scenario caps are 300/120 seconds. Mridul owns package/official compatibility.

## 6. Report brutal truth, with evidence and the next concrete action

Create `docs/feedback/ATISHAY_DELIVERY_RESULTS_2026-09-25.md` (use the actual date
if finishing later). Link it from my handoff. For each slice and gate report:

| Item | PASS / FAIL / NOT RUN / BLOCKED | Evidence and command | What works | What does not | Owner / next action |
| --- | --- | --- | --- | --- | --- |

Use **BLOCKED** only with a specific missing dependency or agreed ownership change;
show the attempted command/reproduction and why independent work cannot resolve
that item. "Needs coordination", "model weak", "tests green" or "not on PATH"
alone are not an adequate diagnosis. Check documented installations before claiming
a tool/model is absent. Do not run an unbounded filesystem scan or expose secrets.

If you cannot solve something, say: "I reproduced X; tried Y; observed Z; still
cannot establish W; the next needed change/input is Q, owned by R." If a task is
beyond what you can complete, identify the unresolved code path and give the next
agent an executable reproducer. Do not hide uncertainty behind optimistic prose.

Distinguish **implemented**, **deterministically verified**, **real-model verified**,
and **human-device verified**. Do not invent a completion percentage. Summarize the
gates individually and say plainly whether my deliverable is complete or partial.
Do not imply Mridul's packaging/release work is complete because my tests pass.

## 7. Commits and handoff are checkpoints, not completion certificates

Make small commits on my branch after relevant checks. Preserve test evidence and
failure history; never rewrite a known failure as success. Follow my existing push
authorization: push only my branch when authorized, never main, a final submission
tag or forms. If authorization is missing, leave reviewable local commits and say so.

A partial, tested checkpoint can be useful to share, but its summary must explicitly
say PARTIAL and list the open gates. Never say "push this, my work is done" solely
because a commit is ready. Do not add AI names/coauthors/signoffs to commit metadata
or new authored repository text; preserve existing history and accurate generic
AI-use records. Keep secrets and private recordings out of commits.

Update my handoff and shared sync log with the actual outcome, not an optimistic
plan. Finish with: what now works for a user, the gate results, exact outstanding
work for me versus Mridul, and the commit/branch/evidence paths. Continue all
independent owned tasks that remain feasible; request narrow coordination instead
of declaring the whole assignment complete when only one part is blocked.
