# Informational follow-ups after actions — 22 September 2026

Owner: Mridul. Engine and engine tests only; no B-owned code or tests modified.

## Reproduction

After a confirmed mock booking, ask an unrelated question such as support hours.
The controller acknowledged the new question but discarded the model's answer.
An existing test explicitly recorded that inherited limitation by expecting silence.
Changing that test to require the informational final reproduced a timeout on
the original source (`c1ab2af`) before the engine fix.

Cause: the informational-final gate tested whether any write existed anywhere in
the session's ledger. A successful action from an earlier finished request therefore
blocked every subsequent informational answer. The same history check suppressed
bounded recovery for an empty follow-up plan.

## Implemented behavior

The final-answer guard now distinguishes current requests from historical effects:

- A resolved write on an older request does not block a later informational answer.
- A write belonging to the current request still requires actual tool-result
  confirmation; model prose cannot replace it.
- Unknown or cancelled write outcomes remain a session-wide barrier, even if the
  active request has changed. No retry, rollback or completion is inferred.
- A retained requested write that has not dispatched is still protected by the
  owed-write check and bounded recovery budget. This includes write intent first
  established by the current proposal, not only earlier proposals.
- A valid informational final closes that request internally, allowing the next
  admitted input to start its own request and recovery budget. Conversational
  slots and their value provenance retain the existing rotation behavior.
- The external session status remains `listening` after an informational answer,
  matching the existing demo contract. This means the conversation accepts another
  turn; it does not mean the old informational request is still unfinished.

An empty complete follow-up plan now receives the ordinary bounded no-progress
recovery instead of silently stalling due to an unrelated historical write.

## Verification scope

The revised historical test now asserts the actual desired follow-up answer,
request identity and one unchanged confirmed mock effect. Six new cases cover
confirmed failed-write history, three successive informational questions, bounded
recovery for an empty follow-up, unknown/cancelled historical outcomes, and an
initial write proposal that claims completion without dispatch.
The last two are explicitly labelled ledger fault injections; they do not establish
real cancellation or rollback behavior. Existing authority, unknown-write and
read-then-write tests remain intact.

The first combined run caught an implementation compatibility error: the new
informational final changed the exposed status from `listening` to `completed`.
That failure came from the A-side change, not a new B bug. The engine was corrected
to preserve `listening`; the original demo assertion was not weakened or edited.
Initial combined result: 1 failed, 1042 passed, 1 skipped, 1 xfailed (60.59 seconds).
After compatibility repair: 1043 passed, 1 skipped, 1 xfailed (60.81 seconds).

A subsequent adversarial test exposed a pre-existing first-plan gap: a proposal
could establish write_requested and say "Booked Wednesday" before any tool dispatch.
The prior-only owed-write calculation did not yet see that newly established intent.
The reproduction returned a false informational final. The guard now also checks
retained intent after applying this proposal in an environment with write tools,
when the proposal claims understanding or supplies response prose, and sends it
through bounded recovery or clarification. Incomplete plans with no response may
still wait for promised input. A read-only environment can still explain its
capabilities. No success claim is inferred by inspecting arbitrary response text.
The first broader guard attempt caused two A-side regressions (promised-image
waiting and a read-only fixture's answer). The refined condition preserves both
original tests. That intermediate full run had 2 failed, 1042 passed, 1 skipped,
1 xfailed in59.71 seconds; the following focused suite passed78 tests.
Final results after this additional repair are recorded in the current checkpoint.

This is controlled software evidence, not live-model accuracy or media validation.
The separately tracked frame xfail and intermittent native-frame timeout remain
open. The full prompt stays default; compact-profile quality and provider quota
remain separate unfinished work. No official submission or release tag is created.

Final source verification: 1044 passed, 1 skipped, 1 xfailed, 2 dependency warnings
in54.82 seconds; focused78 passed; Ruff and diff checks passed.
