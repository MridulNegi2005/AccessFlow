# Samsung adapter work — 22 September 2026

## Current A-side checkpoint — 22 September 2026

**996 passed, 1 skipped, 1 xfailed**, two dependency deprecation warnings, in
82.99 seconds. Ruff passed; offline-fake development scenarios 4/4. Commands:
`uv run --offline --frozen --extra dev pytest -q`,
`uv run --offline --frozen --extra dev ruff check .`,
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.
The skip is native Windows symlink creation without the required privilege;
mocked resolved-escape tests pass. The existing conflicting-frame xfail remains
unresolved. Neither is counted as a passing safety test.

Implemented explicit spoken result bindings, fixed argument mappings and source
revision checks. A scoped review reproduced and closed an image-induced contract
removal bypass and acceptance of success-labelled evidence carrying an error.
Malformed Pydantic/JSON/schema outputs now get one bounded same-input retry with
sanitized shape feedback; non-fresh retries cannot gain spoken write authority.
Optional tool documentation is explicitly loaded below kit/docs, hashed and kept
separate from observations/results/permissions. Verbatim return examples are
selected with line/hash provenance to reduce repeated input tokens.

One live Qwen Samsung chained-booking attempt completed: **100.0/100**, one search,
one booking, confirmed final at 6250 ms, normal tail unchanged. Earlier new attempts
failed validation (38.5) and hit input quota (15.4); all reports are retained in
`docs/evidence/samsung-binding-2026-09-22/README.md`. These are individual exposed
public development runs, not medians, an ablation or release certification.
The successful explicit profile uses a 32768-character hosted cap, output cap950,
1.0-second speculative partial debounce and docs/TOOLS.md. Defaults/local limits
were not silently changed. The provider reported a 7000 input-token/minute quota;
the successful run used 3013+3615 planning input tokens, so headroom remains tight.

Next A-side work: bounded transient-read retry to save a model roundtrip and final
answer time; then additional public interruption/unseen/no-tool cases and repeated
measurements under declared quota conditions. MP3/vision/timing/frame coordination
still requires Atishay; no B-owned implementation or handoff changed. Docker,
unrelated file-boundary security review and submission materials remain outstanding.
Current work stays local on mridul/engine. No push, workflow dispatch, release tag
or submission. User's latest steering: no more Astra subagents; Luna only if needed.
This checkpoint supersedes current-state wording in historical sections below.

## Current validation checkpoint — 22 September 2026

Fresh rerun: **863 passed, 1 xfailed**, two dependency deprecation warnings
(63.64 seconds); Ruff passed; offline-fake development suite **4/4**.
Commands: `uv run --offline --frozen --extra dev pytest -q`,
`uv run --offline --frozen --extra dev ruff check .`, and
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.
The merged-main baseline previously measured 842 passed / 1 xfailed; the current
local Mridul branch additionally includes adapter, recovery and runner tests.
The conflicting-frame expected failure remains unresolved, not a passing safety test.

Three recorded live Qwen public text attempts: simple search **100.0**, chained
booking **56.9**, failed-read recovery **81.5**. These are individual development
scores, not task completion percentages or final benchmark results. Booking was
blocked by tool-derived argument authority; recovery succeeded but final inference
missed the normal tail window. Full evidence and provenance:
`docs/evidence/samsung-text-2026-09-22/README.md`.

Next A-side work: implement and test the proposed delegated-result binding in
`docs/DELEGATED_RESULT_BINDING.md`, then optimize bounded read recovery timing.
That spec is not implemented or certified. Coordinate MP3/vision/timing with
Atishay; no B-owned implementation changed. No new dependencies. Current work
remains local on `mridul/engine`; no release, submission or workflow dispatch.
This checkpoint supersedes current-state claims in historical sections below.

Owner: Mridul. This is incremental implementation, not submission readiness.

## Entry point and execution boundary

`accessflow.adapters.samsung:ParticipantAgent` provides the organizer's Python
constructor, async `setup()` and async `run()`. The controller uses `executor=None`:
tool calls and cancellations are sent to organizer queues and results come back
through that same boundary. It does not execute demonstration tools locally.
HarnessAuthorization is only suitable for the organizer's mock environment;
the controller's spoken-intent and argument checks still apply.

Set `ACCESSFLOW_SAMSUNG_MEDIA_ROOT` to the extracted kit root and
`ACCESSFLOW_SAMSUNG_BACKEND` explicitly to the existing chosen backend. Existing
provider-specific configuration remains unchanged; see `PROFILES.md`. Backend
warm-up occurs in setup. No fake or alternate-provider fallback is configured.
Tests inject components explicitly and are offline software evidence.

The initial default perception construction supports text only. MP3 and live
vision configuration are not completed by this slice. Do not run all public
scenarios and label unsupported media as successful model inference.

Use the official time scale of **1**. The clock starts at run(), not setup();
event timestamps convert milliseconds to seconds. Accelerated harness replay
is not supported by the initial runtime clock. A `scenario_end` event leaves
the result channel open until the harness cancels run after its tail window.

Setup failure is retained and does not trigger another model warm-up on the
scenario clock. Parser and background failures propagate instead of leaving a
silent dead input pump. Internal diagnostics remain bounded; they are not a
sixth official action kind. Tests must also verify any actionable error-to-speech
policy; retained internal diagnostics alone are not scored by Samsung.

## Remaining A-side work

- Review and test every translator mapping against the kit validator. Exercise
  interruption, late results, failed tools, source replacement, and session isolation.
- Reconcile the authority guard with legitimate tool-derived booking identifiers.
  Preserve the prohibition on rewriting a user-fixed value. Do not simply remove
  the guard to make chained tool scenarios pass.
- Wire real backend/perception configuration and collect reproducible official
  traces. Current mock tests cannot establish task quality or response latency.
- Package an importable submission with pinned dependencies and environment
  declarations. Do not copy organizer ground truth into the agent/package.
- Resolve meaningful error reporting, filler budgets, bounded tool waits, and
  frame-as-context behavior before claiming protocol/quality completeness.

## Coordination proposal: official media seam (not yet agreed)

Mridul and Atishay must agree on a media adapter boundary. The proposed split is:

| Component | Owner | Required behavior |
|---|---|---|
| Official event translation and path admission | Mridul | Preserve frame IDs, ordered audio chunks, milliseconds and end-of-turn; constrain paths to configured media root |
| MP3 decoding and audio observation assembly | To agree before implementation | Accumulate a turn's clips, preserve revisions/timestamps, bound native work and decoded bytes; no handwritten transcripts |
| Perception and assigned process worker | Atishay | Use agreed audio input interface and replaceable real vision; preserve cancellation/source identity |
| Runtime factory and official trace evaluation | Mridul | Same configuration/provenance through official entry point; no demo executor or scripted planner fallback |

This does not authorize editing Atishay's files. Existing C1–C4 decisions remain
open, including frame replacement/conflict semantics and stop-speaking versus
cancel-task semantics. Whole-file audio arrival is not a calibrated speech endpoint.

## Validation of initial slice

Full suite: **855 passed, 1 xfailed** (95.19 seconds), with two dependency
deprecation warnings. New adapter tests: **13 passed**. Ruff passed. Samsung
`harness/protocol.py` accepted all five translated action types with synthetic
data. This is protocol-shape evidence, not a public-scenario or live-model score.
The existing conflicting-frame expected failure is still unresolved.

## Focused boundary review

A Luna high read-only review of `samsung.py`, `samsung_protocol.py` and their
13 tests reported no concrete findings in the inspected cancellation, timeout,
path, shutdown and documented-schema boundaries. The reviewer reran the focused
suite: 13 passed. This is a limited code review, not a full security audit or
live/official evaluation. Source checkpoint: `865a266`.

The current shell has no Samsung backend/media-root or Groq credential/model
configuration loaded. A local `.env` exists but was not loaded during this slice.
Configuration and warm-up remain to be exercised; no secrets were printed.

## Read-failure recovery follow-up

The controller now replans on a current failed read using separate sanitized
`tool_failures` rather than admitting failure payloads into usable results.
The existing two-attempt limit is preserved and errors cannot establish write
permission. Final suite:859 passed/1 xfailed; Ruff clean; offline dev4/4.
Official transport/live-model retry behavior still needs scored-scenario evidence.


## Samsung transient-read retry — 22 September follow-up

`ACCESSFLOW_SAMSUNG_FAST_READ_RETRY` accepts only `1` (default Samsung factory)
or `0` (model-directed control). It enables one exact current transient-read
retry without inference. Generic Agent defaults remain unchanged (opt-in).
The runner records the actual agent flag and execution ledger with operation IDs
and `retry_of_call_id`. No additional official action fields are required.

Measured pub_08 with the documented hosted profile: 100.0 with retry enabled,
81.5 in the matched configuration control. The control's final request hit rate
limit; do not characterize the difference as solely a tail/latency improvement.
See `docs/evidence/samsung-retry-2026-09-22/README.md` for all evidence and limits.
