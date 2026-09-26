# Merged verification - 26 September 2026

## Outcome

Merged Atishay's `4c0caa8d05bc309fe24407be9a7e35fc31ebe148` into main
`5dd2a56ce7f063335fb2fcb0fbfe4f127640e9a6`, producing implementation merge
`ac187ba0f6f776b77e042d2e3211554835f026cd`. No conflicts. Both histories are
preserved; merged B implementation/tests match his source branch. No application
code was repaired or tests weakened during this review.

This delivery contains useful functional progress, not just documentation. The
standard regression suite passes. **The agreed product is still incomplete.**
Atishay's latest report explicitly says PARTIAL/BLOCKED, not complete, and the
remaining shared-controller dependencies are real.

## Verification on this machine

Python 3.11.15, Windows, installed repository environment:

| Check | Result |
| --- | --- |
| Entire pytest suite | **1388 passed, 6 skipped, 3 xfailed**, 77.87 seconds |
| Four installed-ASR opt-in tests | **4 passed**, 28.20 seconds |
| Ruff | Passed |
| Seven Node browser checks | All passed |
| Offline developer replay | **4/4**; explicitly fake inference/effects |
| D1 tests with `--runxfail` | **2 failed, 1 passed**; confirms remaining stop failures |
| Merge whitespace and B-source preservation | Passed |

The standard suite skips four installed-ASR tests and two unavailable native
symlink tests. The four ASR skips were exercised separately above. The three
expected failures are vague stop, output-only stop and the existing conflicting
frame case. Two dependency deprecation warnings remain.

ASR verification used `models/faster-whisper-base.en` and
`ACCESSFLOW_TEST_WHISPER_MODEL_PATH`. It covered the actual worker/Agent,
decoder evidence, configured WebSocket preview/final path and reconnect.
Generated audio and mock reasoning were used. This does **not** establish real
Qwen reasoning, live vision, human microphone behaviour or an actual booking.

About 3.35 GiB physical memory was free before this separate ASR run. The earlier
`mkl_malloc` failure reported on Atishay's machine did not reproduce here. This
does not fix or explain his machine's resource problem; retain his failure record.

Evidence: `docs/evidence/merged-2026-09-26/`. No actual-inference Gate 2 attempts,
physical-mic Gate 3 checks, Docker execution or full Samsung evaluation were run
for this review. Those remain unverified, not implicitly passed by unit tests.

## What Atishay actually added

1. **Error recovery:** accepted input IDs are sent before perception, so early
   media errors can correlate with the active request. The browser handles
   authoritative output-stop and rejects stale replies. Existing new Python/Node
   coverage passes; the old September 25 error probe intentionally describes old
   behaviour and must not be treated as a desired acceptance test.
2. **Shared runtime adoption:** `demo/app.py` now calls `build_configured_agent`
   in explicit configured mode, with declared mock tools/authorization and
   actual backend labels. Mock mode remains available. This corrects the previous
   absence of common runtime wiring; actual hosted reasoning is still unmeasured.
3. **Live voice scaffolding:** worklet capture, provisional ASR during speech,
   pending-speech signals, automatic final WAV delivery, bounded previews/turns,
   quiet-reset after capped turns, and End session without flushing unfinished
   audio. There are deterministic tests; physical acoustic behaviour is unverified.
4. **Image handling:** separate perception keys for distinct image IDs, explicit
   queue overflow, session-local receipted thumbnails/status, and late-receipt
   isolation. These are useful prerequisites for D4, not authoritative multi-image
   reasoning or field selection.
5. **Evidence preparation:** fixed generated WAV/PNG development inputs and twelve
   attempt IDs, correctly marked NOT RUN rather than counted as inference success.

## Remaining failures and exact owners

### R26-1: D1 vague-stop and output-only-stop are still failing

**Mridul owns the shared decision/controller additions; Atishay then maps his policy.**

Reproduction:

```powershell
python -m pytest tests/perception/test_confirmed_stop_semantics.py --runxfail -q
```

"Stop" fails the required output-stop/hold/clarification assertions; the controller
still admits an informational planner final. "Stop speaking" times out waiting
for the required acknowledgement. Explicit task cancellation passes. Required
product behaviour is already decided in PRODUCT_DECISIONS_2026-09-25.md; do not
ask the user to make the same decision again. Do not fix this in browser-only logic.

### R26-2: D4 multi-image source selection remains missing

**Mridul owns registry/view/provenance/write guards; Atishay owns perception/UI binding.**

The controller still keeps one `active_frame`, removes the prior observation and
rejects non-active image results. The new browser list does not change that state.
"Take the date from Image 1 and details from Image 2" cannot yet be certified.
Add bounded image history, stable accepted ordinals/timestamps and explicit
field/source dependencies; preserve action-authority and stale-plan guards.

The old conflicting-frame xfail remains expected, not fixed by thumbnails. Its
historical timeout is not proof of an unsafe write. Update the acceptance semantics
carefully when the authoritative multi-image implementation lands.

### R26-3: D2/D3 integration still needs verification and controller work

**Joint: Mridul owns authority/closure; Atishay owns acoustic capture and playback.**

The browser now has real capture/preview code and an End session control. It is
no longer accurate to describe all voice interaction as requiring manual Finish.
However endpointing uses RMS activity and lexical checks with 2.2-second default
quiet and a bounded 4.2-second action pause. These are heuristics, not proof that
all unfinished requests are recognized. Preview text currently goes to the browser;
the final WAV goes through the agent. ASR preview is not full semantic planning
or a new authorization signal.

Verify pause/continuation and speech-triggered interruption on real hardware,
and implement/test authoritative hold/clarification and session-close races with
inference and tools. The client drops late UI messages and discards unfinished
capture, but those properties alone do not certify that the server cannot commit
queued work after closure. Inspect the shared controller and teardown ordering;
do not claim rollback for already committed effects.

### R26-4: real inference and device acceptance remain unrun

**Atishay owns his twelve fixed runs and four human checks; Mridul supplies shared
implementation and supported runtime/package integration.**

The local ASR checks above reduce uncertainty about merged plumbing on this machine.
They do not close the twelve actual reasoning/vision attempts or physical-mic gate.
Configure the approved runtime, address his reproducible resource failure if it
persists, complete D4, then execute the fixed inputs without substituting mocks
or discarding failed attempts. Kit access is a local setup dependency; the original
kit exists on Mridul's machine outside the repository.

## What to do next

1. Mridul: implement D1 scoped stop/hold/clarify with conformance tests. This is
   the first concrete shared blocker; no new model experiment is needed.
2. Mridul: close D2/D3 authority/closure gaps, then D4 registry and source selection.
   Atishay: bind the agreed interfaces and run his owned regressions in parallel.
3. Joint: use the already wired configured demo for real inference/device checks,
   retaining actual backend, hardware, timings and failure outcomes.
4. Mridul: verify the resulting submission package/platform and official evaluation.

Keep these as code-completion work. Defer decorative UI, broad prompt tuning and
accuracy sweeps. No release tag, submission, paid fallback or workflow is implied.
