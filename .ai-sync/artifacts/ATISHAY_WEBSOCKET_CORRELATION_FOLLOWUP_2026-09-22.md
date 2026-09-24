# Atishay follow-up: WebSocket response correlation — 22 September 2026

Owner: Atishay (Workstream B). Report only; no B source, tests or handoff edited.
This is separate from the stale-frame timeout in `ATISHAY_TIMING_FOLLOWUP_2026-09-22.md`.

## Reproduced failure

On `33a9851` with only the diagnostic runner and its A-owned tests modified:

```powershell
uv run --offline --frozen --extra dev pytest -q
uv run --offline --frozen --extra dev pytest tests/demo/test_reasoner.py::test_websocket_environment_reasoner_receives_multimodal_context -q
```

First full suite: **1 failed, 1046 passed, 1 skipped, 1 xfailed**, 60.26 seconds.
Failure is `StopIteration` at `tests/demo/test_reasoner.py:318`: no recorded
reasoner request contains both `screen shows the approval prompt` and
`What did I send you?`.

Three isolated reruns on unchanged source: **failed, passed, passed**, taking
2.69, 2.13 and 2.25 seconds. The final full rerun passed: **1047 passed, 1 skipped,
1 xfailed**, 60.69 seconds, two dependency warnings. The passing rerun does not
close the earlier failures. Exact full-suite XML files and their hashes are in
`../evidence/samsung-unseen-2026-09-22/`. Isolated results were observed in terminal
output; no separate isolated XML was retained.

## Likely synchronization problem; causal proof still needed

The local HTTP stub sets `image_context_received` as soon as it receives a
reasoner prompt containing image evidence, before sending its response. It emits
the same final text for image-only and image-plus-question requests. The test
waits for that event, submits a new transcript, then exits its receive loop on
**any** final or error and closes the connection.

An image-only final can therefore satisfy the loop while the question's planning
is still pending. Closing the session may cancel that pending work. The later
combined-prompt assertion then fails. The final payload assertion compares
`caused_by_event_id` to itself, so it does not demonstrate that the answer belongs
to the new question. Source inspection supports this race hypothesis; no
instrumented event trace yet proves which interleaving caused the recorded run.

The current runner change is not used by this demo test. However, do not infer
that all earlier engine lifecycle changes are irrelevant: the test uses the real
controller, and request scheduling/cancellation affects the interleaving.

## Atishay's next work

1. Capture emitted input IDs, reasoner request contents and final provenance in a
   deterministic gated reproduction. Distinguish image-only responses from the
   combined response in the protocol stub.
2. Give the question a known input event ID if the demo contract supports it.
   Await the final associated with that question, not just the first final.
   Keep the connection alive until its response or an explicit bounded failure.
3. Separate the two valid cases: a completed standalone image answer before a
   follow-up, and a question superseding still-pending image reasoning. Establish
   each ordering with gates rather than sleeps or a longer timeout.
4. Preserve tests that require real combined context to reach the reasoner.
   Removing the combined-prompt assertion or accepting image-only text would
   conceal the problem. Keep native worker capacity/cancellation invariants intact.
5. Run isolated repetitions and the combined suite, recording every failure.
   Loopback services are protocol doubles, not live multimodal model evidence.

## Explicit coordination: both Mridul and Atishay

Atishay owns `tests/demo/test_reasoner.py` and any demo input/correlation repair.
Mridul owns A-controller output provenance and reruns integration after B's fix.
If a correctly correlated demo still receives a wrongly attributed final, agree
on an event/response example together: Atishay supplies the B reproduction and
Mridul adds an A-owned controller regression and fixes only A code. Do not edit
each other's files. No shared schema change should be made unilaterally.
