# Additive contract proposals

Use: date, author, failing example/test, proposed addition, compatibility plan and decision.

Pending considerations: typed output payloads; timer/speech activity observations for
turn policy; structured reconciliation observations; per-modality generation handling.
These are not permission to silently change v0.1. Preserve existing fields and fixtures.

## 2026-09-13 - Speech activity timing signal

- Author: Atishay Workstream B
- Failing example: tests/perception/test_turn_policy.py::test_turn_policy_accepts_activity_timing_without_using_pause_as_completion
  originally recorded the missing timing channel. It now passes for the owned policy seam: HeuristicTurnPolicy.update
  accepts optional ActivitySummary and keeps a detected pause separate from TurnDecision.complete. Shared
  engine/controller wiring still cannot supply this metadata and remains the pending contract gap.
- Proposed addition: Add an additive timing event or optional observation metadata carrying activity windows, source utterance ID, source revision, frame start/end timestamps and a pause threshold result. The signal must remain separate from TurnDecision.complete. The optional owned policy seam is implemented; shared timing-event and controller integration remain pending.
- Compatibility plan: Keep v0.1 transcript/audio events and TurnPolicy unchanged. A translating adapter can drop timing metadata for older consumers; the current owned timing summary remains offline until the proposal is accepted.
- Decision: Owned policy seam implemented on 2026-09-16; shared contract/controller integration pending review by Mridul; no shared contract files changed.

## Additive image-only informational response

- Observed example: tests/demo/test_app.py::test_image_only_informational_response_needs_additive_controller_support
  is a strict expected failure on atishay/perception. A frame reaches DemoPerception and the
  reasoner returns an informational response, but the current controller does not emit its final
  because latest_complete is derived from speech completion.
- Proposed additive change: Add an optional informational-response basis to the planning
  proposal, for example informational_evidence: Literal["speech", "image", "multimodal"] | None.
  The controller may emit an informational response for image or multimodal evidence when the
  proposal opts in, while retaining the existing completed-speech and authorization gates for every
  state-changing call.
- Compatibility: The field defaults to None, does not alter existing writes or turn-policy
  decisions, and keeps frame-only responses explicitly informational. The engine owner should
  implement and review this on mridul/engine; this branch intentionally contains only the
  failing example and proposal.


## Conflicting visual evidence requires resolution

- Author: Atishay Workstream B
- Failing example: tests/demo/test_app.py::test_conflicting_frames_require_resolution_before_write
  sends a completed spoken request followed by frames whose captions disagree. The current controller
  retains both frame observations and can accept a write proposal without a structured conflict state.
- Proposed additive change: Add optional frame provenance and conflict metadata, such as
  supersedes_source_id and an evidence status of consistent, conflicting or uncertain. The controller
  should retain the latest frame for ordinary replacement, mark unresolved visual conflict as
  correction-pending, and require clarification or a new resolving observation before any write.
- Compatibility: All fields are optional and default to the current v0.1 behavior. Existing frame IDs,
  timestamps and image observations remain valid; older adapters can omit the metadata. This branch
  contains the failing example only and does not modify the controller or shared contracts.
  The integrated engine at origin/mridul/engine 919ed27 now replaces the prior active frame before
  planning, so conflict detection must compare or record the superseded frame before that removal if
  conflicting visual evidence is still required.
