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
