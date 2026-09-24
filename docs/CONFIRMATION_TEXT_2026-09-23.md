# Readable confirmed-action replies — 23 September 2026

Owner: Mridul. Confirmed write results now include deterministic readable text,
while preserving the original result, call ID, operation ID, causal event and basis.
This changes presentation after confirmation, not authorization or execution.

Before, Samsung's fallback said:

```text
The requested action completed with result: {"booking_id": "BK-0001", "flight_id": "FL-DEN-8AM", "status": "success"}
```

The new generic formatter produces:

```text
The mock action is confirmed. Booking ID: "BK-0001". Flight ID: "FL-DEN-8AM". Status: "success".
```

That example describes mock tool data. It is not a real booking or a claim that
voice usability has been measured. Field names remain literal descriptions from
the source; the formatter does not guess that an unfamiliar effect is a booking,
a payment, a device repair or any other specific domain action.

## Authority and source boundaries

Only the two existing confirmed-effect final branches call the formatter:

- Direct write success: after outcome normalization, dependency/invalidation checks
  and explicit committed-effect evidence.
- Status reconciliation: after the declared status tool and operation identity
  match, the normalized outcome is `committed`, and the original call is not invalidated.

The status-check reply starts “The status check confirms the mock action.” Its details
come from that status result, not an invented reconstruction of the original write.

Success without `committed=True` still becomes unknown. Unknown/timeouts, cancelled
or failed results, `no_effect` status checks and late commits after invalidation do
not gain normal success replies. Existing late-effect error reporting and duplicate
prevention are unchanged. No write is dispatched or retried by this formatter.

`confirmation_payload` itself grants no authority. It is a pure presentation helper
whose callers must have admitted the effect already. It does not accept a model
proposal, infer outcome from a field name or route writes through read selectors.

## Exact behavior and limits

Keys are humanized by replacing underscores with spaces and displaying ID in upper
case. Nested objects/array rows retain their path and item number. Strings remain
quoted/escaped, including embedded newlines and instruction-like content. Numbers,
false, zero, null and explicit unit/period fields retain their literal values. No
currency symbol, billing period, total or guarantee is inferred from a bare number.

Bounds are12 leaf fields,4 levels,1200 text characters,80 characters per key and240
characters per string value. Unsupported/nonfinite values or excess bounds cause
one fixed reply that confirms the admitted effect and explicitly says its details
could not be summarized. Partial fields are not silently retained while a later
qualifier is dropped. The full raw result remains in the event even on this fallback.

An empty result confirms the admitted action without fabricating details. Formatting
failure never changes a confirmed effect into a failed/unknown operation or triggers
a second write. The helper does not mutate result evidence.

## Additive event metadata and teammate coordination

The existing `final.payload.text` is now populated for the two confirmed-effect
bases. `result_presentation` adds `status=complete` or `status=omitted` plus a fixed
reason code for omitted details. Existing `result`, `basis`, `call_id`, `operation_id`
and `caused_by_event_id` remain unchanged. The official wire adapter already prefers
text and therefore needs no new wire field. Its old result-only fallback remains
available for older internal producers.

`effect_environment` is `mock` only when the trusted runtime authorizer declares
that environment (the fake executor profile and Samsung mock harness do so).
Otherwise it is `unspecified`, which is not a claim of real external effects.
Mock confirmations say "mock action" in the spoken text. Result fields, model
proposals and tool names cannot select this runtime marker. An optional
`authorization.effect_environment` attribute is additive; existing authorizers
without it continue to work. Custom result equality is not invoked by formatting.

This is enabled for confirmed effects across inference profiles. It does not enable
the separate experimental evidence-selected read-answer mode or compact prompt by
default. No model call, dependency, speech engine or UI implementation was added.

Both teammates must coordinate display/speech adoption: Mridul owns admitted outcome,
text and raw provenance; Atishay owns rendering, playback and optional result cards.
The existing text field is compatible, but detailed presentation and voice usability
are not claimed tested here. Never interpret presentation metadata as action authority.

## Verification and remaining work

The initial owned integration regression reproduced the absence of text
(1failed/4passed) before implementation. Focused confirmation, reconciliation,
conflicting-outcome, safety, request-scope and Samsung-protocol checks then passed.
Full-suite and live evidence are recorded in the linked evidence bundle.

This remains literal field narration, not full natural-language understanding of
arbitrary tool schemas. Repeated official evaluation, media/perception integration,
platform/Docker verification and final human submission work remain open.

[Verification evidence](evidence/confirmation-text-2026-09-23/README.md)
