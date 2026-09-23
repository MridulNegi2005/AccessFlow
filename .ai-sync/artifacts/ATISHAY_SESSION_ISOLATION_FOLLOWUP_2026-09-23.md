# Atishay follow-up: perception session-isolation test — 23 September 2026

Owner: Atishay. Report only; no perception/demo implementation or tests changed.
This is an observed regression-suite failure, not an established cross-session leak.

The failure was observed on Mridul's current checkout, not on Atishay's latest branch.
`origin/atishay/perception` at `ed9d581` additionally contains `967e39d`, which changes
native-capacity timeout handling and other tests. Those changes were inspected but
not merged or executed here. The specific session-isolation test body is unchanged
in that branch comparison, but the newer worker may affect its behavior. Reproduce
on the integrated/current B source before attributing the failure to that version.

## Observed result

During the compact-v2 A-side profile validation, the full suite reported:

`tests/perception/test_local.py::test_pending_work_isolated_between_sessions`

At line865, `first_b_result == []` failed. The list contained an Observation with
`source_id='first-b'`, modality image, revision0, backend `local/injected-vision`
and text `evidence from first-b`. The first A observation had already passed its
empty-list assertion. This is a stale-within-session expectation failure; the output
does not by itself demonstrate that A's contents appeared in B's session.

Full result:1failed/1091passed/2skipped/1xfail,102.22s, two dependency warnings.
Three immediate isolated reruns on unchanged files passed in1.08s,1.14s and1.26s.
The final full rerun passed1092tests/2skips/1xfail in85.48s; this does not close the observation.
The original failure XML is retained with hashes in
`docs/evidence/samsung-compact-v2-2026-09-23/`.

## Investigation for Atishay

The test uses provider-side `release_a.wait(1)` / `release_b.wait(1)`, waits for
start events with their own one-second timeouts, then sleeps50ms before release.
The boolean returns from `started_a.wait`/`started_b.wait` are not asserted.
These are source observations, not proof of which ordering caused this failure.
A source/profile change elsewhere cannot be ruled in or out just from a green isolated run.

1. Reproduce with logged/admitted work identities and deterministic gates. Distinguish
   provider start, latest-frame admission, provider completion and result acceptance.
2. Ensure the test establishes latest-B admission before expecting first-B rejection.
   A wall-clock timeout that releases a worker is not proof of that ordering.
3. Inspect whether the stale result is a legitimate earlier completion or an actual
   perception worker invalidation defect. Preserve per-session/native-work bounds.
4. Add/fix tests only in the owned B areas; do not weaken stale-result assertions or
   merely extend sleeps until the suite goes green. Preserve actual useful semantics.

## Coordination

Atishay owns this test and LocalPerception. Mridul owns integrating the tested result
and repeating A/shared regression checks. Both need to coordinate only if the
reproduction exposes a shared event/controller contract issue. No request is made
for Mridul to change Atishay's worker or for Atishay to alter the engine.

This new observation does not close or replace the earlier frame-timing and WebSocket
correlation reports. The profile work remains independent of repairing this test.
