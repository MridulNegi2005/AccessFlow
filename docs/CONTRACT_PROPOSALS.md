# Additive contract proposals

Use: date, author, failing example/test, proposed addition, compatibility plan and decision.

Pending considerations: typed output payloads; timer/speech activity observations for
turn policy; structured reconciliation observations; per-modality generation handling.
These are not permission to silently change v0.1. Preserve existing fields and fixtures.

## 2026-09-13 - Speech activity timing signal

- Author: Atishay Workstream B
- Failing example: A partial transcript with a long acoustic gap currently carries only the transcript final flag, so the engine cannot distinguish “user is pausing” from “utterance ended” without overloading turn completion.
- Proposed addition: Add an additive timing event or optional observation metadata carrying activity windows, source utterance ID, source revision, frame start/end timestamps and a pause threshold result. The signal must remain separate from TurnDecision.complete.
- Compatibility plan: Keep v0.1 transcript/audio events and TurnPolicy unchanged. A translating adapter can drop timing metadata for older consumers; the current owned timing summary remains offline until the proposal is accepted.
- Decision: Pending review by Mridul; no shared contract files changed.
