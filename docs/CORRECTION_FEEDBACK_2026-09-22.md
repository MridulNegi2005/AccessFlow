# Correction feedback and failure speech — 22 September 2026

Owner: Mridul (engine and Samsung protocol). No perception, turn policy, demo,
process-worker or B-owned tests were changed. Existing stop-speaking versus
stop-task and conflicting-frame decisions remain coordination work.

## Problems reproduced

The first live Samsung `pub_02_text_interrupt` run searched New York after the
user corrected Boston, and cancelled the obsolete search. However, its only
spoken state snapshots still said Boston, the initial filler repeated, and the
final model request hit HTTP 429. The user received no explanation of that failure.
Supplied scorer total: 65.3. This was a real model run with organizer mock tools.

## Implemented behavior

- A fresh, complete spoken proposal that changes existing slots and prepares tool
  work receives a short acknowledgment after dependent work is invalidated. The
  snapshot contains the accepted values. The text reports the interpretation;
  it never claims a booking or other tool effect completed. Only up to four scalar
  details are spoken, with bounded names/values. Partial, image-origin and
  tool-result-origin proposals cannot produce this acknowledgment.
- The Samsung boundary suppresses repeated filler text within a session. Explicit
  stop-output acknowledgments are preserved. State and suppression history reset
  with a fresh participant/protocol instance.
- Known `backend_failure` and `no_progress_exhausted` diagnostics also produce a
  bounded clarification. Raw error detail stays out of speech. The message does
  not assert that an outstanding action succeeded, failed or was rolled back.
  Repeated error/source pairs are suppressed; at most 128 are retained. Other
  diagnostics remain diagnostics, not arbitrary speech.
- A final observation already flagged as a possible correction goes straight to
  semantic reasoning instead of waiting through the partial-input debounce. It
  still has to pass the existing semantic readiness and authorization checks.
  Partial speech keeps its debounce. Images keep their existing treatment.

The first feedback-only rerun scored 84.3 with recovery and safety fractions 1.0.
The updated city was spoken at 3688 ms and the error explanation at 6063 ms.
The final useful answer remained absent due to input-token quota, and the early
city-acknowledgment checkpoint was still missed. This prompted the separate
finished-correction debounce fix above; neither issue was hidden or labelled fixed
merely because the overall score improved.

## Verification and next work

Owned tests exercise accepted corrected state, cancellation before acknowledgment,
partial-speech silence, repeated filler versus explicit stop, honest error speech,
unknown diagnostic suppression, and final-versus-partial debounce with explicit
event gates. No test relies on faster machine sleeps to make a timing race pass.

Live development reports and final validation are recorded in
`evidence/samsung-interruption-2026-09-22/README.md`. These exposed runs do not
prove repeated performance or hidden/multimodal coverage. Remaining A-side work
includes reducing repeated model-input overhead while preserving source/authority
checks, useful final answers under the declared provider quota, broader public
text cases, and follow-up informational requests after completed actions.
