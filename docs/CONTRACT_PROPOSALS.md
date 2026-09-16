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

## 2026-09-15 - Vision provider in the perception worker

- Author: Mridul Workstream A
- Failing example: `LocalPerception` accepts a `vision_provider` callable and uses it for
  every `FrameEvent`. The process worker never supplies one.
  `src/accessflow/adapters/perception_worker.py` builds `LocalPerception(model_path=...)`
  only, so `--components local` raises
  `RuntimeError("Image perception requires an explicit vision provider")` on any frame.
  No image scenario can run through the process adapter.
- Proposed addition: Accept an optional vision provider in the worker and pass it to the
  existing `LocalPerception(vision_provider=...)` parameter. Four optional command-line
  options select it: provider name, model, URL and timeout. The default is `none`, which
  keeps the present behaviour exactly.
- Compatibility plan: The change is additive. `_serve` gains one optional parameter with a
  default of `None`. With no option supplied, the worker builds the same object it builds
  today. No existing caller changes, and `process_perception.py` needs no change because its
  `worker_args` sequence already carries extra options to the child.
- Workstream A has prepared the other side: `src/accessflow/adapters/vision.py` supplies
  `OllamaVisionProvider`, a plain `Callable[[Path], str]` with unit tests and no network in
  tests. `src/accessflow/cli.py` already accepts the options and records the resolved value
  in run metadata. `scenarios/live_dev/frame_device_panel.json` is ready to run.
- Evidence that the approach works: the full path was measured once on 15 September with a
  temporary local edit to the worker. Raw PNG, real Ollama `gemma3:4b` inference, a sourced
  image observation and a committed mock effect. The model read `PANEL-B` from the image.
  That edit is reverted. The measurement is recorded in `docs/results/VISION_E2E_2026-09-15.md`
  and is not reproducible until this proposal is accepted.
- Decision: Assigned to Workstream B on 15 September 2026 by Mridul. The proposal stands.
  Workstream A does not edit the worker. See the ownership note below.

### Ownership note, 15 September 2026

Two documents gave different owners for `src/accessflow/adapters/perception_worker.py`.

- `AGENTS.md` assigns all of `src/accessflow/adapters/` to Mridul, Workstream A.
- This proposal and `.ai-sync/handoff.md` treated the same file as Workstream B property.

`AGENTS.md` is the authoritative ownership document, so the directory rule puts the file in
Workstream A. Mridul reviewed this contradiction on 15 September 2026 and decided that the
change stays with Atishay. The decision is deliberate and overrides the directory rule for
this one file. Workstream A does not edit the worker.

The Workstream B boundary at `src/accessflow/perception/` is unchanged. `LocalPerception` in
`src/accessflow/perception/local.py:84` already accepts a `vision_provider` callable and
already calls it for each frame. That seam is complete and needs no change.

Work that remains for Atishay, in his own file:

1. Accept the optional provider options in `src/accessflow/adapters/perception_worker.py`.
2. Pass the constructed provider to `LocalPerception(vision_provider=...)`.
3. Keep the default `none`, so the audio-only worker behaviour does not change.

Workstream A has already supplied everything on its side: `src/accessflow/adapters/vision.py`
provides `OllamaVisionProvider`, `src/accessflow/cli.py` accepts and records the options, and
`scenarios/live_dev/frame_device_panel.json` is ready to run.

Until item 1 and item 2 are done, the parent CLI advertises `--vision-provider` and the child
rejects it with exit code 2. Finding A2 in `docs/reviews/MRIDUL_REAUDIT_2026-09-15.md` stays
open, and no vision scenario runs through the process adapter.

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

## Resolution note, 16 September 2026

The two proposals above were written while every image path stalled. The cause was the
image branch in `HeuristicTurnPolicy`, which returns `continue` for a frame, combined with a
controller that read that verdict as image readiness. The controller no longer asks the turn
policy about a frame. See `docs/INTEGRATION_NOTE_2026-09-16.md`.

An image now completes as evidence and can produce an informational answer. An image alone
still cannot authorize a write; that gate is unchanged and verified.

"Additive image-only informational response" is therefore already the engine's behaviour, and
it predates both branches. The open question is the opposite one: whether a lone image should
stay silent until the person speaks. That is a contract decision for Mridul and Atishay
together, not a test fix.

"Conflicting visual evidence requires resolution" stays open. Replacement frames are handled
by source and revision freshness, but the controller does not represent two frames that
disagree.
