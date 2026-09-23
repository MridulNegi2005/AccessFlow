# Atishay follow-up: intermittent stale-frame timeout — 22 September 2026

Owner: Atishay (Workstream B). Report only; no B-owned source or tests were edited.

## Observed evidence

A combined run on Mridul's uncommitted read-retry slice based on `01d271c` returned
**1 failed, 1020 passed, 1 skipped, 1 xfailed** in 62.26 seconds. Failure:

`tests/perception/test_local.py::test_stale_frame_timeout_is_suppressed_when_newer_frame_succeeds`

The second frame timed out acquiring the native semaphore in
`src/accessflow/perception/local.py:571`, then raised
`RuntimeError: image perception timed out after 0.05s` at line573. The test failed
at `await asyncio.gather(first_task, second_task)` (line1065).

Three immediate isolated runs on unchanged files each passed: 0.67s, 0.67s, 0.74s.
The final complete rerun also passed: 1021 passed, 1 skipped, 1 xfailed in
71.79 seconds. This does not close the intermittent failure.
`git diff -- src/accessflow/perception/local.py tests/perception/test_local.py`
was empty. This is evidence of intermittent behavior under the combined run,
not proof that the root cause is harmless or that the new engine caused it.
The test constructs LocalPerception directly; it does not use the new retry engine.

## What to investigate in your lane

Trace when frame2 starts acquiring the permit relative to frame1's await timeout,
native thread completion, callback-driven permit release and the test's two sleeps.
The test uses a50ms perception timeout and releases frame1 after50ms+10ms;
real scheduler/thread timing can influence that boundary. Determine whether the
product intends a queue wait deadline, a provider execution deadline, or one total
budget. Preserve the invariant that stale native work keeps its permit until it
actually finishes; do not fix the test by restoring overlapping native work.

Replace timing guesses with explicit gates/observations where possible, then add
separate tests for genuine queue expiry and successful admission after stale work
finishes. Report repeated isolated and combined results, including any failures.
Simply raising the timeout until a single run passes does not establish correctness.

## Coordination

Atishay owns the perception semantics/test repair. Mridul owns only recording this
failure and rerunning integration afterward. Coordinate if the chosen deadline
semantics change the public perception contract or the Samsung media budget.
This report does not authorize Mridul to edit B files or fabricate media evidence.
