# Additive contract proposals

Use: date, author, failing example/test, proposed addition, compatibility plan and decision.

Pending considerations: typed output payloads; timer/speech activity observations for
turn policy; structured reconciliation observations; per-modality generation handling.
These are not permission to silently change v0.1. Preserve existing fields and fixtures.

## Accepted additive A-side argument mapping — 2026-09-13

Reproduction: `tests/engine/test_argument_dependencies.py` originally failed seven cases:
untracked read/write parameters, unrelated dependencies, contradictory slot/argument values,
and changing model nonce values splitting a retry's operation identity.

Addition: `ProposedCall.argument_slots: dict[str, str] = {}` maps a tool parameter to its
session slot when names differ. Otherwise the same-name slot is required. Every dynamic
argument must equal its mapped slot and list that slot in dependencies. Writes retain
the existing confirmed-slot and independent authorization requirements. Direct schema
constants/singleton enums, controller-generated idempotency arguments and actual unresolved
operation IDs passed to their declared read-only status tools are narrowly exempt.

Compatibility: Existing valid same-name proposals and all perception/UI contracts remain
valid. Previously untracked dynamic arguments now fail closed with `missing_dependency`;
contradictory values or malformed mappings report `argument_dependency_mismatch`. Two A-side
race fixtures explicitly declare their dummy `day=any` parameter as a schema constant.
No B-owned implementation changes. The field is internal v0.1, not an organizer wire claim.

The controller cannot infer omitted semantic context not represented in arguments. Extra
context dependencies must still be supplied; arbitrary alias guessing is deliberately absent.
The operation signature ignores model-provided idempotency values before controller injection.

## Accepted additive A-side change — 2026-09-13

Problem: The reasoner previously had call IDs in ToolResult but no operation ID needed
for the status tool. The first reconciliation test hid this by reading executor internals.
Addition: `SessionView.calls: list[ToolCall] = []` and optional causal/output operation IDs.
Compatibility: Existing SessionView construction and input/output envelope fields remain
valid. No edits to Atishay-owned components. Verified by contract and reconciliation tests,
including a planner that reads only its public view and a no-effect retry preserving identity.
Timer/speech activity contracts remain proposals; this change does not implement Atishay's policy.

## A-side integration interpretation — 2026-09-13

Reproductions: tests/engine/test_component_integration.py. Final `possible_correction`
was permanently blocked; image-only information never completed. A contradictory
clarification/write proposal could dispatch while asking a question.
Decision: use the existing PlanProposal.request_complete flag to resolve final corrections
only when no clarification remains; require speech readiness for writes and allow image
information independently. No field or version change. B-owned implementations unchanged.
Tests cover correction resolution, clarification, raw WAV provenance and image/write guards.

Review follow-up: correction resolution also requires the matching speech source. A private
controller flag records write intent only from accepted complete-turn speech planning;
image evidence may fill details but cannot invent intent or revive a completed request.
Four regression/positive cases verify image-source isolation and valid multimodal completion.
No new public authorization field; the independent authorization provider still governs effects.
## 2026-09-13 - Speech activity timing signal

- Author: Atishay Workstream B
- Failing example: A partial transcript with a long acoustic gap currently carries only the transcript final flag, so the engine cannot distinguish “user is pausing” from “utterance ended” without overloading turn completion.
- Proposed addition: Add an additive timing event or optional observation metadata carrying activity windows, source utterance ID, source revision, frame start/end timestamps and a pause threshold result. The signal must remain separate from TurnDecision.complete.
- Compatibility plan: Keep v0.1 transcript/audio events and TurnPolicy unchanged. A translating adapter can drop timing metadata for older consumers; the current owned timing summary remains offline until the proposal is accepted.
- Decision: Pending review by Mridul; no shared contract files changed.
