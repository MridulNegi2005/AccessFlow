# Samsung adapter work — 22 September 2026

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
