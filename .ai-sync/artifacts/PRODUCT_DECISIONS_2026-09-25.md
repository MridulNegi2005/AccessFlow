# Confirmed product decisions - 25 September 2026

Status: explicitly confirmed/corrected by Mridul in conversation on this date.
These are accepted requirements, **not implemented capabilities or test results**.
They supersede earlier recommendations for newest-image-only context and a required
Finish/Send recording interaction. No comparison with another product's internals
is implied: the requested experience is an opt-in, hands-free live conversation.

## D1. Stop, clarification and action authority

| Input | Required behaviour |
| --- | --- |
| "Stop speaking" | Stop assistant playback; preserve task context and existing valid authorization. This is not cancellation of a booking. |
| "Stop", "stop right there", "wait", or otherwise unclear stop/cancel intent | Stop playback, hold new actions, preserve the draft, and ask what the user means. Do not guess output-stop versus task/booking cancellation. |
| "Cancel this task" | Cancel pending task work and abandon that task; keep the voice session open unless the user also ends it. |
| "Cancel this booking" with a uniquely identified target | Treat the explicit request as cancellation authorization, subject to ordinary tool/target validation. Do not ask the same authorization question again. |
| "Cancel this booking" with an ambiguous/missing target | Ask which booking. Explicit cancellation intent is not evidence identifying the target. |
| User starts speaking while assistant output/work is pending | Stop playback promptly, admit pending speech, and hold new state-changing dispatches until the user's intent is resolved. Do not assume the whole task was cancelled. |

An incomplete hypothesis such as "cancel..." does not authorize cancellation.
Only a confirmed, resolved command authorizes a state-changing operation. Stable
partial input may start bounded reversible reads, as described in D2.
That does not permit additional task-tool dispatch while a vague stop is awaiting
clarification; interpretation needed to ask the clarification may continue.
Work based on superseded input must be cancelled where possible and its late
results must not become accepted effects or a current answer. Already committed
effects are not rolled back by stopping speech; uncertain writes must not be
blindly retried. Use mock external effects for development.

Clarification is a legitimate new response while a vague-stop session remains
open. It must wait for the speaker to finish the stop request, rather than speak
over continuing input. Do not resume the paused action before the ambiguity is
resolved. This is distinct from D3, which closes the session entirely.

## D2. Live voice and work during speech

- The user explicitly starts a voice session; microphone activity is visible.
- Within that session, the user can speak, pause, correct and interrupt hands-free.
- The system determines turn completion automatically. Pressing Finish/Send/Stop
  must not be required to get each utterance processed or answered.
- Begin bounded background work while the user speaks: activity detection, ASR,
  provisional interpretation and, where independently allowed, reversible reads.
  Do not wait for a manual button to start all processing, and do not make a model
  request for every audio sample/chunk. Coalesce obsolete work and reject old results.
- Allow time for pauses and self-corrections. A silence threshold alone is not
  authorization for an action. Use acoustic and available semantic evidence;
  measure premature response and added waiting separately on fluent controls.
- No single magic pause duration or perfect endpointing accuracy is promised by
  this decision. Choose bounded, configurable settings, test them, and document
  remaining failures. A whole-recording upload can remain as an alternate input
  route but cannot be reported as the live-session implementation.
- Preserve utterance/revision identity during corrections; completion/finality
  and permission to execute remain distinct concepts.

## D3. The manual Stop control ends the session

Label the live-session control **End session** (a stop icon is acceptable) so it
cannot be mistaken for "finish this utterance and send it".

On activation: stop capture and playback immediately, revoke further session
input/dispatch, cancel owned inference/tool/perception work where possible, close
queues/workers and release microphone tracks/audio contexts. **Do not flush the
unfinished recording as a final user message or generate one last AI response.**
Leave the already displayed conversation visible; a local "Session ended" status
is permitted. Discard late callbacks/results and do not display/speak them or
dispatch new actions. Starting again creates a fresh session.

Physical cancellation may not reverse an effect already committed by an external
system, and in-flight native/network work may take bounded time to terminate.
Report these limits honestly. End-session acceptance requires immediate logical
closure and bounded resource cleanup, not the impossible claim that every remote
operation can be undone. Retaining a diagnostic/outcome record is allowed; it
must not restart inference, play a final response or revive the closed session.

## D4. Ordered, timestamped image history within a session

Keep **multiple accepted images**, not only the newest active frame. Maintain a
session-scoped registry with immutable image ID, stable admission ordinal (Image 1,
Image 2, Image 3), server receipt timestamp/order, available capture timestamp with
provenance, processing revision/status, and grounded evidence associated with that ID.

- Number by accepted input order, never by inference completion or an untrusted
  camera clock. Equal/out-of-order timestamps must not reorder those ordinals.
- Upload/receipt time identifies an attachment; it is not a date read from pixels.
- A new image becomes the default current image for an otherwise unambiguous
  "this/new/latest image" reference, while older accepted images remain addressable.
- Understand ordinal and contextual references: "first image", "second image",
  "keep the date from the old image but use the details from the new image".
- If "old" or a requested field is ambiguous, missing or illegible, ask a focused
  clarification. Do not guess which earlier image/field the user meant.
- Preserve field-level provenance when combining sources. Example: date comes
  from Image 1; address comes from Image 2. A later caption must not silently change
  the selected source for either field or create authorization for an action.
- Late perception of Image 1 is not stale merely because Image 2 arrived. It may
  fill Image 1's pending record if its own event/revision/session is still valid.
  It must never be mislabeled as Image 2, override explicit source choices or
  revive an obsolete plan. Explicit replacement/correction invalidates the
  relevant version; receipt of a separate image alone does not delete history.
- Keep existing resource limits or explicitly configure bounded replacements.
  Reject an over-limit attachment clearly rather than silently evict/reindex an
  image that the user may reference. Failed perception keeps its identity and an
  honest unavailable status; it must not shift subsequent image numbers.
- The registry is session memory, not cross-session personal storage. Clear it
  for a fresh session; do not add a database or persistent image gallery for this.
- Image contents and metadata remain untrusted evidence, never agent instructions.

This changes the previously implemented single-active-frame contract. Preserve
compatibility through defaulted/additive fields or an adapter. The official wire
protocol and evaluator timing remain unchanged. Do not simply remove old safety
guards or enable arbitrary history-based writes to satisfy a new UI test.

## Implementation division: both workstreams must coordinate

| Area | Mridul | Atishay |
| --- | --- | --- |
| Stop/clarification | Shared decisions, dispatch holds, controller/task effects | Detection/classification, current-session playback, visible clarification |
| Live voice | Pending-speech/finality interpretation, queue/runtime hooks | Live capture/activity/ASR, automatic turn policy, browser wiring |
| End session | Logical closure, inference/tool cancellation and stale-result rejection | Stop capture/playback, close transport, ignore late UI callbacks |
| Image history | Shared image registry/view, explicit source selection, provenance and write guards | Stable attachment identities/order in UI, per-image perception and owned tests |
| Evidence | Controller/integration and official package verification | Perception/browser, actual images and human-device acceptance |

Product behaviour above is settled. The agents should agree exact additive field
names, clock mapping and lifecycle hooks with examples and conformance tests; they
do not need to ask the user to reconfirm these product choices. Until A's new
contracts are merged, B can test the agreed seam with explicitly labeled fakes.
Neither owner may silently edit the other's implementation or claim a fake proves
the integrated feature. Error-correlation and other independent work can proceed.

Backend selection stays as already configured; no new model/paid fallback is
authorized here. Full shared-runtime, multi-image, endpointing and physical-mic
acceptance remain open until implemented and measured.
