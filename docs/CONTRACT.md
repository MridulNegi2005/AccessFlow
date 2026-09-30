# Internal event and component contract

Canonical types are in `src/accessflow/contracts.py`; component protocols are in
`src/accessflow/interfaces.py`. This internal queue interface is adapted to LiveKit
for the submission voice runtime. It is not the organizer's wire schema.

## Events and state

`Agent.run(input_queue, output_queue, clock)` consumes input envelopes and emits
output events. Each envelope includes a contract version, session ID, unique event ID,
timestamp, sequence, kind and typed payload. Timestamps use seconds in a shared clock.
Event identities prevent duplicate delivery; source revisions reject stale hypotheses.

Input kinds include session start/end, transcript, audio, speech status, frame,
interruption and tool result. Output kinds include acknowledgment, clarification,
tool call, call cancellation, final response and error. Outputs carry session state
snapshots with intent, provisional/confirmed slots, evidence and pending work.

Partial revisions replace the earlier hypothesis for an utterance. They are not appended
as separate user commands. Repetitions and corrections have distinct meanings.
Speech pending status holds dependent actions until the transcript is resolved.
Frame IDs preserve image identity; image ordering and timestamps support references
to earlier and newer inputs. Evidence content cannot authorize execution.

## Components

- `Perception.observe(event)` streams observations with source event, utterance/frame
  identity, revision, modality, finality, timing and backend provenance.
- `TurnPolicy.update(observation, session_view)` classifies continued speech, completion,
  possible correction, backchannel or stop. Uncertainty remains explicit.
- `Reasoner.plan(session_view, manifests)` proposes intent, slots, calls and clarification.
  A proposal cannot directly execute a tool.
- `ToolExecutor.execute(call)` returns its call ID, status and confirmed commit state.
  Cancellation guarantees are explicit; an unknown outcome is not rollback.

One controller owns authoritative state. Perception, reasoning and tool execution run
asynchronously. Corrections invalidate dependent work; accepted results must match current
dependencies and call status. Unrelated work can continue.

## Tool safety

Manifests declare capabilities, effects, parameter schemas, timeouts and optional
reconciliation/idempotency fields. Arguments are validated outside the language model.
Calls have a call ID and stable logical operation ID. Write authorization defaults to
deny; mock-only authorization must not be attached to a real service executor.

A write timeout may leave its outcome unknown. Use a status capability where available;
do not blindly retry. Cancellation does not undo a committed effect. Final responses
describe confirmed outcomes rather than attempted calls.

Explicit stop-speaking and cancel-action requests are distinct. An ambiguous stop request
requires clarification and a hold on affected actions. Closing a session terminates new
interaction and preserves honest reporting of unresolved work. New rooms have fresh
conversational state.

Contract examples and `tests/test_contract.py` validate compatibility. Fake audio,
scripted observations and mock tools must remain labelled as development fixtures.
