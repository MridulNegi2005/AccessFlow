# Controller completion checkpoint — 26 September 2026

## Implemented on Mridul's branch

- Direct final text and transcribed audio recognize explicit playback stop and vague
  stop/hold controls at the controller boundary. Image/tool contents cannot invoke
  these controls. An unresolved hold blocks planner starts, proposal application,
  and fast read retries. Late read outcomes can be retained without dispatching
  more task tools. Ambiguous answers retain the hold.
- Explicit task cancellation revokes task authority and requests cancellation.
  Its acknowledgement waits at most 250 ms for cancellation delivery in a worker,
  keeping the dispatcher responsive; it is not a claim of rollback.
- Resolving the hold as an explicit action such as cancelling a booking returns
  to ordinary target/schema/authorization validation. Missing targets may clarify.
- Audio transport admission still conservatively cancels pending writes while
  speech is unresolved. A matched playback-only final can restore semantic
  readiness/authorization only for an unchanged request, slots, intent and frame.
  It never restores a cancelled ledger entry, erases an unknown outcome, changes
  evidence provenance, or treats control speech as fresh write permission.
- Shutdown now lets bounded cancellation requests reach the executor before
  cancelling worker tasks. It discards queued late results and emits only an
  unspoken ended/stop-output control, not a last spoken answer.

## Still being built by Mridul

The standalone bounded image registry and its tests exist, but it is NOT yet
connected to controller state, planning or snapshots. It therefore does not make
D4 complete. Next integrate ordered image records, valid late results on their
own records, field/source bindings and plan/write invalidation. Then verify the
configured runtime, package and Samsung evaluation path. Do not start broad
accuracy tuning or declare our work complete from this checkpoint.

## Atishay coordination — no owned files edited

Run `tests/perception/test_confirmed_stop_semantics.py --runxfail`: its three
checks now pass. Two carry explicit strict expected-failure markers that are now
obsolete; remove those markers on the B branch after pulling this implementation.
Do not suppress real failures globally. The normal test command will report those
strict XPASS markers as failures until that owned test maintenance lands.

The controller recognizes conservative complete control phrases, not every
possible paraphrase or every acoustic error. Physical microphone testing and the
12 fixed actual reasoning/vision attempts are still unrun. B should consume the
upcoming authoritative D4 projection, then run the agreed integration acceptance.
No model training, hosted inference, Docker execution or human-mic evidence is
claimed by these deterministic tests.
