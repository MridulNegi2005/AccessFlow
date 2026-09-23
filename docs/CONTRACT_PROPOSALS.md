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
it predates both branches. The open question was the opposite one: whether a lone image should
stay silent until the person speaks.

Decided on 16 September 2026: neither. A frame that arrives with nothing spoken yet waits
`Agent.frame_debounce_s` (0.4 s by default) before it answers on its own. Speech inside that
window cancels the frame-only plan, so a frame and the question that follows it fold into one
answer. A frame that answers speech already in progress does not wait, so the clarification
path keeps its latency. Silence would lose a described-image task; answering instantly would
talk over a question that was already coming.

"Conflicting visual evidence requires resolution" stays open. Replacement frames are handled
by source and revision freshness, but the controller does not represent two frames that
disagree.

## A-side additive planner failure context — 22 September 2026

`SessionView.tool_failures: list[ToolResult] = []` is an optional internal planner
field. Existing callers can omit it. It does not change the official queue
protocol, output snapshots, or perception/worker inputs.

The controller records a failed current read separately from usable `results`,
strips its result payload and committed flag, and offers the reasoner another
planning step. The existing call-signature attempt budget still permits at most
two identical attempts. Errors are not successful evidence and never create
write authority. Every admitted failure advances the monotonic outcome counter
used by authority guards. At most 12 failures are retained, and planner views
filter them by active request and current dependency revisions.

Ownership: Mridul's contracts/controller and engine tests. Atishay need not
change perception, policy or demo files for this field. This is not resolution
of C1-C4 media/endpoint coordination or of delegated tool-argument authority.


## 22 September 2026 — A-side delegated argument contract

Additive internal fields: `PlanProposal.write_contracts`,
`ProposedCall.result_sources`, and `SessionView.write_contracts`. All default
empty, preserving the original proposals and B-side callers. Model generation
still requires every original completion/action decision; the extensions are
optional. No official wire schema changes.

A fresh complete speech plan may declare a target write, fixed parameter-to-slot
mappings, and delegated parameters selected from a specific read. Source references
are either a call index in that same proposal (resolved only if dispatched) or an
explicit current read call ID. The controller exposes captured contracts with
actual call IDs. A continuation must supply each delegated parameter's source ID
and the selected value in its tracked slot. It cannot create or broaden a contract.

Selection uses bounded JSON pointers and one unique row with exact typed scalar
matches to user-fixed slots. `True`, `1`, and `1.0` are distinct. No time/fuzzy
normalization or positional selection exists. New observations clear the exception;
fresh speech can replace it, explicitly reusing a current read when appropriate.
The controller checks source success, accepted evidence, revisions, all fixed
mappings and existing authorization gates. Bound constraints are added to actual
write dependencies even when omitted by the planner.

Owner: Mridul. Atishay needs no implementation change for these defaulted fields.
Tool result structures must be known to declare selectors; runtime public manifests
may omit them. Live generality remains to be verified; this contract is not proof
that the model understood the original speech or that a tool's data is truthful.


### Validation and lifecycle follow-up, 22 September

`SessionView.last_plan_error` is optional bounded controller-generated shape
feedback. It is deep-copied into views and cleared on new evidence or a valid plan.
Pydantic, JSON parsing and dynamic-schema failures share the existing single retry
budget. A rejected fresh plan retains its speech provenance only with the same
source and admitted-result counter; no input epoch bump grants extra retries.
Non-fresh retries cannot create spoken authority. The generated ResultBinding
schema now exposes the same exclusive-source and match-count limits as Pydantic.

Expired contracts remain target barriers across images and partial speech; only
fresh complete spoken supersession clears/replaces them. This closes a reproduced
fallback into legacy image-origin argument aliases. No B-side changes are needed.


## 22 September 2026 — controller-issued read retry lineage

`ToolCall.retry_of_call_id` is an optional physical-parent identifier (default null).
The controller may retry once on exact transient error codes `timeout`,
`TimeoutError`, or `temporary_unavailable`, only for a current failed read with
unchanged arguments, manifest, dependencies, request and input epoch. Corrections,
unfinished speech, invalidation and stopped tasks block dispatch. The model and
controller share the existing two-attempt allowance; writes never use this path.

Only current captured write contracts may transfer their source reference from
the failed read to this exact replacement with the same logical operation ID.
Selectors, mappings and spoken authority do not change; expired records remain
barriers. The old failed result and late duplicate deliveries are never accepted.
This additive internal field requires no B implementation or official wire change.
Owned tests cover late results, guard permutations, retry budget and bound writes.


## 23 September 2026 — opt-in evidence-selected read finals

Owner: Mridul. Additive `PlanProposal.evidence_answer` defaults null; older producers
may omit it. `EvidenceAnswer.selections` holds bounded `ReadSelection(call_id, pointer)`
references, never model-provided values. The answer-only variant excludes prose,
clarification, intent/slot changes, calls and write intent/contracts. Controller
validation precedes state mutation and checks source status/request/dependencies.

Internal final payload adds `basis=read_evidence`, `backend=literal_renderer` and
`evidence_sources`; existing text and state remain. No Samsung wire changes. The
experiment is explicitly enabled through `ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE=evidence`;
prose remains the default. The same mode must reach ModelReasoner and Agent.

Both Mridul and Atishay must coordinate before enabling this in the browser or
introducing cards/voice formatting. Mridul supplies the checked result and metadata;
Atishay renders existing text safely and owns frontend/voice treatment. No B source
or test changes were required or made in this slice. The proposal does not ask either
person to duplicate the other's implementation.

See READ_ANSWER_EXPERIMENT_2026-09-23.md for limits: source fidelity is not factual
truth, completeness, relevance or validation of free-form clarifications.


## 23 September 2026 — readable confirmed-effect text

Owner: Mridul. Both existing confirmed-effect final branches now populate the
existing text field and add result_presentation metadata (complete, or omitted with
a fixed reason). Raw result/call/operation/causal identifiers and basis are preserved.
No proposal, input queue or official Samsung wire fields change.

Only already-admitted committed effects reach this formatter; unknown, no-effect,
cancelled and invalidated outcomes retain their existing paths. Rendering failure
keeps the effect confirmed and preserves full raw evidence instead of retrying it.

Both teammates coordinate cards/playback: A supplies authoritative outcome and text;
B owns safe display, voice playback and any detail UI. No B source or tests changed.
See CONFIRMATION_TEXT_2026-09-23.md for bounds and verification limits.

Runtime provenance is additive too: trusted authorization adapters can declare
`effect_environment="mock"`; missing/other values render as `unspecified`, never
as verified real effects. Final payloads retain this marker and mock confirmations
explicitly say "mock action". Model/tool-result fields cannot select the marker.
Samsung's mock harness and the mock-only authorizer declare it. B can display this
metadata but must not infer action authority or real integrations from it.
