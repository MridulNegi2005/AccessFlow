# Additive contract proposals

Use: date, author, failing example/test, proposed addition, compatibility plan and decision.

Pending considerations: typed output payloads; timer/speech activity observations for
turn policy; structured reconciliation observations; per-modality generation handling.
These are not permission to silently change v0.1. Preserve existing fields and fixtures.

## Accepted additive A-side change — 2026-09-13

Problem: The reasoner previously had call IDs in ToolResult but no operation ID needed
for the status tool. The first reconciliation test hid this by reading executor internals.
Addition: `SessionView.calls: list[ToolCall] = []` and optional causal/output operation IDs.
Compatibility: Existing SessionView construction and input/output envelope fields remain
valid. No edits to Atishay-owned components. Verified by contract and reconciliation tests,
including a planner that reads only its public view and a no-effect retry preserving identity.
Timer/speech activity contracts remain proposals; this change does not implement Atishay's policy.
