# Internal contract v0.1

Canonical types: `src/accessflow/contracts.py`; protocols: `interfaces.py`.
This document and types define a team contract, not the unreleased official kit.

`Agent.run(input_queue, output_queue, clock)` consumes typed input envelopes and emits
`OutputEvent` through two asyncio queues. Each agent instance runs one session at a time.
Envelopes contain contract_version, session_id, event_id, timestamp, sequence, kind and
payload. Timestamp units are seconds in a shared monotonic scenario clock, not milliseconds.
Sequence is producer metadata; event IDs deduplicate and source revisions reject old input.

Input kinds: session_start, transcript, audio, frame, interrupt, tool_result, session_end.
Output kinds: acknowledge, clarify, tool_call, cancel_call, final, error. Each output carries
a full state snapshot; output payload is currently extensible JSON. Schema hardening must
remain additive while Atishay starts.

`Perception.observe(event)` is an async iterator. Observations require origin event ID,
source_id, revision, modality, text, final, speech_start/end, backend. Transcript and audio
share the same utterance revision namespace. An equal revision is duplicate, so a changed
hypothesis needs a strictly larger revision. Images use frame IDs and revision 0. Do not
reuse a frame ID for different pixels. Cross-modality stale-observation behavior is being
tested in the engine; clients must not depend on partial state mutation from workers.

`TurnPolicy.update(observation, view)` returns continue/complete/possible_correction/
backchannel/stop with uncertainty. It must not block. The bootstrap policy merely follows
the final flag; adaptive timing belongs to Atishay. No semantic pause claim is made yet.

`Reasoner.plan(view, manifests)` returns intent, slot_updates, proposed calls, optional
clarification/response, request_complete, write_requested. A proposal cannot execute tools
itself. `ToolExecutor.execute(call)` returns matching call_id, status and committed flag;
cancel returns `cancelled_before_commit` only when that guarantee is real, else `unknown`.

Dynamic manifests declare name, description, effect, JSON Schema parameters, optional
status_tool, idempotency_parameter and timeout. Every call has call_id and operation_id.
Write authorization defaults to deny; MockOnlyAuthorization is test-only. Tool cancellation
does not undo committed effects. Unknown outcomes must not trigger automatic write retries.

Golden examples and `tests/test_contract.py` are the shared compatibility gate. The fake
perception accepts text or explicitly scripted observations; fake audio is never live ASR.

## Additive engine updates, 13 September

- `SessionView.calls` defaults to an empty list for existing constructors. It exposes
  detached ToolCall snapshots, including operation_id/status, so a reasoner can request
  status reconciliation without reaching into the executor. Observe-only clients need no changes.
- Output payloads may include `caused_by_event_id`; confirmed write finals include
  operation_id. These are additive fields inside the existing extensible payload.
- Perception must echo the original input event_id as already required. Results from an
  interrupted or superseded utterance/frame are rejected. Previously accepted completed
  utterances remain session context; a late result from an older utterance cannot start a plan.
- Session views, perception input and policy arguments are detached copies; component
  mutation never constitutes an authoritative state update.
- Provisional slot/intent changes are associated with the input source that triggered the
  plan. Replacing that hypothesis restores earlier confirmed values or removes new tentative
  ones, and invalidates dependent reads. Fine-grained model-provided field evidence remains
  future work; this is trigger-source provenance, not a claim of perfect semantic attribution.
- Partial planning is debounced by 80 ms by default; final observations bypass that delay.
  EventReasoner binds fake proposals to event IDs so coalescing doesn't shift script answers.
- A model-proposed retry after a definitively failed/no-effect attempt is bounded to one
  retry and keeps operation_id with a fresh call_id. Unknown/cancelled outcomes block writes.
  A new user request after a terminal write failure/success starts a new operation identity.

## Completed corrections and image readiness

A final speech observation classified `possible_correction` remains unresolved until a
fresh, accepted semantic plan originating from that speech source sets `request_complete=True` without a clarification.
Partial speech cannot be promoted by that flag. A clarification may be emitted for a
final unresolved correction; a proposal containing a clarification cannot dispatch writes,
even if it also claims completion and requests a write. Existing authorization and
confirmed-dependency checks still apply.

An image may support an informational answer when no speech is active. It does not finish
partial speech or resolve another source's possible correction. An image cannot independently
supply write intent. A current final speech-origin proposal may establish `write_requested`
without complete details; a later image-origin proposal may complete those details. Both
still require the independent environment authorization. Clarification blocks dispatch.
The controller clears spoken write intent on new speech, interruption or a new request
after a committed action. Informational speech and completed old requests cannot authorize
image-origin writes. These are controller interpretations of existing v0.1 fields;
Atishay's policy and public wire schema are unchanged.

## Optional resource ownership hook

Replay owns its injected perception instance once a run starts and invokes async `aclose()`
when provided. The existing Perception.observe protocol is unchanged; stateless implementations
need no new method. Direct Agent callers own provider cleanup, using an async context manager
or `finally`. A closed ProcessPerception is not reusable; suite factories create fresh instances.
The controller requests cancellation on superseded same-utterance revisions, replaced frames
and explicit interruption, while retaining all stale source/revision/epoch checks.

## Grounded tool arguments

`ProposedCall.argument_slots` is an optional parameter-to-slot mapping, default `{}`.
For example, `arguments={"visit_day": "Wednesday"}`, `argument_slots={"visit_day": "day"}`
and `dependencies=["day"]` require the authoritative `day` slot to equal `"Wednesday"`.
Without a mapping, each dynamic argument uses its own name as the slot name. Arguments
do not create slots: the proposal must include any new slot values in `slot_updates`.

Both read and write dispatch check dependencies and JSON value equality. Writes additionally
require confirmed slots and the existing completion/authorization gates. A mapping key must
be a supplied argument. Include contextual dependencies even if absent from tool arguments;
the engine cannot infer hidden semantic relationships. Unrelated correctly tracked reads
can continue when other slots change.

Direct manifest `const` or singleton `enum` arguments may be literals. The controller owns
the idempotency parameter, strips any model value before deriving operation identity, and
injects its stable identity. A declared read-only status tool may use an actual unresolved
write operation ID directly, regardless of its parameter name. Arbitrary operation strings
or unrelated tools receive no such exception. Full manifest argument validation still applies.

Error codes: `missing_dependency` for absent/unlisted required slots;
`argument_dependency_mismatch` for contradictory values or extraneous mapping keys.
These errors prevent dispatch; they are not confirmed tool effects.

## Request identity and bounded recovery, 15 September

These fields are additive. Each one has a default value. An existing reasoner,
fake or test double that ignores them stays valid. No existing required
parameter changed.

- `SessionView.write_pending: bool = False`. The controller sets this field.
  A value of `True` means the current spoken request asked for a
  state-changing effect. No call has performed or confirmed that effect yet.
  A reasoner should treat `True` as an instruction to continue the plan. A
  reasoner must not answer with a read result alone while this field is `True`.
- `SessionView.repeated_completed_call: bool = False`. The controller sets
  this field. A value of `True` means the previous accepted proposal
  proposed only calls that had already completed. A reasoner should not
  repeat those calls. A reasoner should read their results from
  `SessionView.results` and take a different step.
- `SessionView.no_progress: bool = False`. The controller sets this field.
  A value of `True` means the previous accepted plan advanced nothing. It
  dispatched no call, gave no clarification and gave no answer. No earlier
  call was still pending. A reasoner should not repeat an empty result. A
  reasoner should call a tool, ask a clarifying question, or answer the user.
- `SessionView.active_request_id: str = ""`. The controller sets this field
  to the identity of the currently open request. Use this field to select
  which `SessionView.calls` entries belong to the current request. An empty
  string is a valid ID. It matches only calls that also carry the default value.
- `ToolCall.request_id: str = ""`. The controller sets this field when it
  creates a call. The field records which accepted request produced the
  call. A new request starts once the previous request is fully resolved
  (completed, cancelled or superseded) and fresh speech arrives. A
  correction amends the still-open request under the same ID. Filter
  `SessionView.calls` by `request_id == active_request_id` to reason about
  only the active request.
- `ModelReasoner.output_schema(..., require_progress: bool = False)`. The
  controller-side reasoner sets this argument to `True` for the current turn
  when `write_pending`, `repeated_completed_call` or `no_progress` applies,
  and no reconciliation is outstanding. When `True`, the generated JSON
  Schema adds an `anyOf` clause. The clause requires at least one of: a
  `calls` array with one or more entries, a non-null `clarification`, or
  (when a final response is still allowed) a non-null `response`. An
  all-empty `PlanProposal` no longer validates against this schema. The
  schema states the valid alternatives. It does not only forbid one field.

All five items keep their default value when a caller does not set them.
Existing `SessionView` and `ToolCall` construction stays valid. A reasoner
that does not read these fields stays valid.

### Controller error codes

The controller emits these codes as `error` output events, inside the
existing extensible payload. Each code is a `code` value on the existing
`error` output kind. None of these codes adds a new output kind.

- `plan_schema_rejected`. The controller emits this code when the
  reasoner's generation fails the exact dynamic schema built for that turn:
  `await self._emit("error", code="plan_schema_rejected", detail=message.value)`
  (`engine.py:353`). This code is not terminal by itself. The controller
  offers one bounded automatic re-plan through `_offer_recovery`.
- `write_owed_not_progressed`. The controller emits this code when a
  proposal drops a previously established write intent for the same
  request, without new user evidence. This happens on an empty plan, or a
  prose-only response, while a state-changing effect is still owed:
  `await self._emit("error", code="write_owed_not_progressed", message="A requested state-changing effect is not complete; an empty or prose-only response cannot finish it.")`
  (`engine.py:597`). This code is not terminal by itself. The controller
  restores write intent and offers one bounded re-plan.
- `repeated_completed_call`. The controller emits this code when every
  proposed call, or every proposed call that could be dispatched, already
  completed earlier in the same request
  (`engine.py:614` and `engine.py:621`). This code is not terminal by
  itself. The controller offers one bounded re-plan. This is also the code
  that sets `SessionView.repeated_completed_call` to `True` for the retry.
- `no_progress_exhausted`. The controller emits this code when the single
  shared bounded-recovery budget for the current
  `(request_id, request_input_epoch)` pair is used up, and the request has
  still made no progress:
  `await self._emit("error", code="no_progress_exhausted", message="No progress after one bounded automatic retry; this request will not retry again on its own.")`
  (`engine.py:421`). This code is terminal. The controller sets
  `Snapshot.status` to `"no_progress"` and ends the request. The controller
  does not retry the request again on its own. This code differs from the
  non-terminal `no_progress` and `no_dispatchable_call` codes, which mark a
  single stalled turn before the bounded retry runs.
- `ablation_skipped_invalidation`. The controller emits this code only when
  the `dependency_invalidation` ablation is active
  (`Agent(disabled=("dependency_invalidation",))`, for research and
  evaluation runs only). The controller emits this code instead of its
  normal cancellation and staleness handling, when a changed slot would
  otherwise have cancelled a pending call or staled an accepted read
  (`engine.py:728`). This code is not terminal. It is a diagnostic marker
  for the ablated run. The affected calls keep running. The affected reads
  stay in evidence.

The codes below are older than the 15 September work. They are listed
here so that this section is the complete set of controller error codes.

- `session_already_started`. A second `session_start` arrives for a session
  that already started (`engine.py:136`). The controller ignores the
  duplicate. Not terminal.
- `duplicate_manifest_names`. A `session_start` supplies two tool manifests
  with the same name (`engine.py:141`). The session does not start. Terminal
  for that session.
- `invalid_status_tool_manifest`. A manifest names a status tool that is not
  a declared read tool (`engine.py:147`). The session does not start.
  Terminal for that session.
- `wrong_session`. An event arrives for a different session id
  (`engine.py:156`). The controller ignores the event. Not terminal.
- `backend_failure`. The reasoner raises an error that is not a schema
  violation, such as a transport or provider failure
  (`engine.py:303`). Not terminal by itself. The evaluation runner treats
  this code as a run-ending condition.
- `unknown_tool`. A proposal names a tool that the session manifest does not
  declare (`engine.py:506`). The controller drops that call and continues.
  Not terminal.
- `invalid_tool_arguments`. Proposed arguments fail the tool's own parameter
  schema (`engine.py:553`). The controller drops that call and continues.
  Not terminal.
- `unknown_call_result`. A tool result arrives for a call id that is not in
  the ledger (`engine.py:782`). The controller ignores the result. Not
  terminal.
- `effect_committed_after_invalidation`. A tool confirms a committed effect
  after the controller cancelled or invalidated that call
  (`engine.py:790` and `engine.py:811`). The controller keeps the effect in
  the ledger. A cancelled acknowledgement does not erase a real effect. Not
  terminal.
- `inconsistent_tool_result`. A tool confirms a committed effect while it
  reports a status that is not success (`engine.py:800`). The controller
  trusts the committed effect. Not terminal.
- `write_outcome_unknown`. A write ends without a definite outcome
  (`engine.py:822` and `engine.py:833`). The controller sets
  `Snapshot.status` to `"needs_reconciliation"` and plans a status lookup.
  No new write dispatches until the outcome resolves. Not terminal.
- `tool_failed`. A tool reports a failure (`engine.py:854`). The controller
  records the failure. Not terminal.

None of the fields or codes above is a proposal to Workstream B. Every
source is inside `contracts.py`, `engine.py` and `adapters/models.py`,
which are Workstream A components. The existing envelope, `Perception`,
and `TurnPolicy` interfaces are unchanged.
