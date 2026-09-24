# Current-frame readiness guard — 24 September 2026

Base: `749fe23` on Mridul's branch. This completes the previously preserved controller
patch; it is not an Atishay perception/frontend change or a live-media benchmark.

## Behavior

- Track the current image by frame ID, event ID and perception epoch. Speech plans and
  read results may proceed, but pending image interpretation blocks terminal answers
  and new writes. Completed speech authority remains separate from image readiness.
- Admit a frame into authoritative planning only after a matching final revision-zero
  observation. Partial image descriptions cannot become confirmed slot values through
  a later speech plan. Speech-based reversible reads may still prefetch.
- Empty, partial-only, wrong-revision or failed/timed-out streams produce a current-frame
  failure instead of leaving a pending gate forever. Stale failures cannot clear a newer
  frame. Replacement, explicit interruption and shutdown discard unresolved evidence.
- On current-frame failure, invalidate pending planning and require fresh user/media
  evidence before a final/write. Completed speech receives a resend/continue clarification;
  partial speech is not interrupted with that question. A successful replacement image
  can reuse the already authorized spoken intent. Read results may still be acknowledged
  and inform bounded read-only planning; they cannot bypass the final/write restriction.
- Completed image evidence can support provisional request slots while speech is still
  partial. Replacing it still rolls those slots back and invalidates dependent reads.

## Verification history and limits

The merge audit already retained four failures against the unpatched main controller.
Expanded tests against the unfinished first patch then found five failures/eight passes:
unsafe failure continuation, partial evidence retention and unmatched-final revision.
These drove the additional guards. A late-read test initially required an empty output
queue; inspection showed the legitimate successful-read evidence acknowledgment, so its
assertion now permits that acknowledgment while retaining no-final/no-write assertions.

The first broad integration run had one failure/991 passes/two skips/one xfail: an older
A-owned rollback fixture ended an image stream with only a partial observation and relied
on that incomplete image entering planning. The fixture now provides a completed frame
while the user's speech remains partial, preserving and strengthening its original
provisional-slot rollback and dependent-call cancellation assertions. No B test was edited.

Focused final coverage: 25 passing tests across pending-frame and source-ownership files.
Includes controlled timeout/recovery, shutdown, replacement, late results, partial speech,
read completion after image loss, write authority on image retry and malformed finality.
Final whole suite: **1,216 passed, 2 skipped, 1 xfailed**, 71.49 seconds; Ruff clean.
Exact evidence is retained in `docs/evidence/pending-frame-2026-09-24/README.md`.

This does not resolve image-conflict semantics, semantic stop-scope classification,
browser causal-response matching, Samsung MP3 support or model configuration. Those
remain assigned in the merged-readiness review. No claim of real ASR/vision quality,
physical microphone usability, measured 50 ms cancellation or official repeated scores.

## Next priority

The user's latest priority is code completion and submission readiness before additional
accuracy tuning; presentation/deck/video work is excluded from that code milestone.
After this correctness repair, implement missing Samsung media/runtime/package paths.
Defer prompt experiments, broad accuracy optimization and cosmetic frontend work.
