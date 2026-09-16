# AccessFlow: Atishay workstream audit

Date: 15 September 2026  
Reviewed shared checkout: `mridul/engine`, commit `30ed402`  
Audience: Atishay and his coding agent  
Related A-side report: [MRIDUL_REAUDIT_2026-09-15.md](MRIDUL_REAUDIT_2026-09-15.md)

## Purpose and limits

This is an independent review of the Workstream B code present in the shared checkout. It is **not an inspection of unmerged work on Atishay's machine**, and it does not attribute every current B-side issue to Claude's latest A-side commits. No B implementation or test was changed during this audit.

There is a useful foundation: perception has injectable ASR/vision providers, observations preserve source identifiers, native work runs off the event loop, the UI labels its mocks clearly, and audio helpers have deterministic tests. The remaining gap is between those isolated components and the promised experience of patient, correction-aware interaction.

The most concrete current defects are broken browser utterance revision semantics, dropped audio timestamps, missing interrupt routing, incomplete media validation and bit-depth-dependent energy behavior. The browser also needs safe rendering before it displays real model/tool content.

The whole repository passes **328 tests with one expected failure** when run as `uv run --offline --frozen --extra dev python -m pytest -q`; Ruff passes. The expected failure is A's clarification/image controller defect. The plain `pytest` command currently fails on A-side scoreboard imports. Neither is a reason for Atishay to rewrite the controller or root configuration.

No new ASR/model/vision inference, browser microphone session, clinical evaluation or participant feedback session was performed for this audit. Python probes used temporary files; a Node VM executed the actual inline browser script with minimal DOM/WebSocket fakes. That VM verifies message generation and HTML construction, not real browser execution of an attack or microphone behavior.

## Ownership boundary

Atishay owns:

- `src/accessflow/perception/`
- `src/accessflow/turn_policy/`
- `demo/`
- `tests/perception/`, `tests/demo/`
- `docs/feedback/`, `docs/presentation/`, `docs/handoffs/atishay.md`

Mridul owns the controller, contracts, adapters, evaluation harness, root configuration/lockfile, engine tests and release packaging under `AGENTS.md`.

**Do not take over the vision subprocess merely because a handoff says it is blocked on B.** The handoff calls `src/accessflow/adapters/perception_worker.py` B-owned, while `AGENTS.md` assigns adapters to A. The reports flag this contradiction for resolution. Your `LocalPerception` already exposes the needed `vision_provider` seam. Preserve that interface and provide examples; change worker ownership only through an explicit documented agreement.

The clarify-then-image deadlock is also A-owned. Do not work around it by marking all frames complete/authorized, injecting spoken intent into image observations, or duplicating action logic in the frontend.

## B1 — P1: browser partials are separate utterances instead of revisions

**Source:** `demo/index.html`, `transcript(final)` around lines 77–85.

The function increments `utterance` and resets `revision=0` every time it is called, whether the event is partial or final. Executing the actual script's function for partial, partial, final produces:

```text
browser-1, revision 0, final false
browser-2, revision 0, final false
browser-3, revision 0, final true
```

These are three different source identities. The shared contract expects revisions of one utterance to replace earlier hypotheses. The UI cannot currently exercise that guarantee correctly and may leave the engine treating partial hypotheses as different speech events.

**Required change:** allocate one active utterance ID when a new utterance begins; increment its revision for replacement hypotheses; send the final hypothesis with that same ID. Allocate a new ID only for the next utterance. Define reset/cancellation behavior explicitly.

**Acceptance:** a browser-script test observes one ID with increasing revisions for partial → corrected partial → final, then a new ID for the following utterance. The final observation must contain the replacement text, not concatenated fragments. Test two quick partial sends, final without partials, and a new session. Keep IDs unique without encoding user text.

## B2 — P1: interrupt input has no browser route

**Source:** `demo/app.py:event_from_message` around lines 138–176; `demo/index.html` controls.

The browser translator accepts transcript, audio and frame only. An input with `kind='interrupt'` raises `ValueError: Unsupported browser event: interrupt`. There is no explicit stop-speaking/stop-task UI control. This prevents the demo from demonstrating the central interruption contract even though the controller already accepts typed interruption events.

**Required change:** translate the existing interruption contract into typed events, preserving timestamp, scope and associated utterance when supplied. Add distinct, understandable controls for stopping output and canceling a task. Do not implement cancellation or tool rollback in the frontend; the controller owns that behavior.

`HeuristicTurnPolicy` also never returns `kind='stop'`; plain “stop” falls through to complete. This is an unfinished semantic route, not justification for mapping every occurrence of “stop” to task cancellation. “Stop talking,” “stop booking,” quoted instructions and a product name containing the word need different treatment. Start with explicit UI interruption, then add conservatively scoped speech behavior in coordination with A's contract.

**Acceptance:** deterministic WebSocket tests observe the correct interrupt event while a fake reasoner/tool is slow; stop-output and stop-task remain distinct. After cancellation, ordinary input still works. Any optional speech output actually stops playing when the relevant event is handled. Never claim cancellation rolled back a committed action.

## B3 — P2: uploaded audio loses its supplied speech timestamps

**Source:** `demo/app.py:event_from_message`, Audio construction around lines 158–166.

Transcript messages copy `speech_start` and `speech_end`; audio messages copy only path, utterance ID and revision. A probe supplied `speech_start=12.5` and `speech_end=14.5`; the resulting `AudioEvent` had **0 and 0**. `DemoPerception` and `LocalPerception` faithfully propagate those zeros, so the loss occurs at the browser adapter boundary.

This prevents meaningful end-of-speech latency measurement and obscures timing during interruptions. Upload completion time is not the user's actual end of speech.

**Required change:** preserve valid supplied speech timestamps; define their clock domain and how recorded-file replay maps onto it. For microphone capture, retain capture timestamps separately from encode/upload/ASR timing. If original speech timing is unavailable for a manually chosen file, identify it as unknown or a defined replay timeline, rather than present a fabricated measured latency. Propose any needed additive contract change to Mridul.

**Acceptance:** exact start/end values survive browser message → typed input → observation; invalid/reversed values follow a documented validation policy; metrics distinguish playback/replay time, upload time and real speech end. The test should use nonzero timestamps so silent defaulting is detectable.

## B4 — P2: media validators accept incomplete files

**Sources:** `src/accessflow/perception/local.py:validate_wav`, `_validate_png`; `demo/app.py:_materialize_upload`.

Two independent temporary-file probes succeeded unexpectedly:

1. A **24-byte PNG prefix**, containing only signature, claimed IHDR length/type and width/height, passes both `_validate_png` and the browser upload validator. It has no complete IHDR payload, CRC, image data or IEND.
2. A normal PCM WAV created with 320 samples, then truncated to its **44-byte header**, passes `validate_wav` and reports 320 frames although the sample data is absent.

These are header checks, not complete media validation. Downstream decoders may still reject them, but the user-facing claim that uploaded files were validated is too strong and failures occur later in a less controllable component.

**Required change:** validate decodability and data completeness, with bounded byte/duration/pixel limits. Prefer a maintained image decoder if available through an agreed dependency rather than building a full PNG parser. For WAV, verify sufficient frame bytes and enforce the formats the consuming backend actually supports. Share validation helpers between upload and perception code to avoid divergent checks.

**Acceptance:** header-only PNG, truncated image data, bad image structure, header-only WAV, partial final PCM frame and excessive declared dimensions/duration are rejected before inference. Ordinary mono/stereo PCM and valid PNG fixtures still pass. Validation must not allocate memory proportional to untrusted dimensions before checking limits. Declare any dependency in Atishay's handoff; Mridul owns the lockfile update.

## B5 — P2: the 8 MiB limit is applied after full decoding, and input errors terminate the session

**Source:** `demo/app.py:_materialize_upload`, WebSocket receive loop; `demo/index.html:fileToBase64`, `sendFile`.

The server base64-decodes the full incoming value before checking decoded size. The client similarly reads and encodes the whole selected file first. A per-file decoded-byte limit therefore does not bound transient allocation, aggregate session disk use or queued work. The queues are unbounded and decoding/file I/O occur directly in the receive coroutine.

Malformed message types are also inconsistent: `payload=None` causes `AttributeError`; a non-string base64 value can raise `TypeError`. A bad image or unsupported event raises through the receive task and closes the entire session, with no structured recoverable validation response. Cleanup exists, but the user loses the interaction instead of getting a useful retry path.

**Required change:**

- Validate message/payload/base64 types before use.
- Bound encoded message length before decoding, in addition to decoded-byte limits and the server's WebSocket message limit.
- Add a bounded per-session media/queue policy and avoid blocking the event loop with large decode/validation/disk operations.
- Reject oversized files client-side early for usability, while retaining server authority.
- Return a structured demo validation error for an invalid input where the session can safely continue; reserve connection closure for protocol/transport conditions that require it.
- When connecting real perception, remove the browser's arbitrary local `path` fallback or restrict it to explicit server-owned fixture IDs. **Current mocks do not read arbitrary paths**, so this audit does not claim an existing file-exfiltration exploit.

**Acceptance:** malformed JSON shapes, wrong base64 types and one bad upload do not crash the handler; a subsequent valid transcript succeeds. Repeated uploads hit an explicit total limit. Interrupt processing remains responsive during upload/validation. Temporary files are removed after rejection/session shutdown.

## B6 — P2: event rendering puts untrusted text into `innerHTML`

**Source:** `demo/index.html:show(event)` around lines 63–69.

The function concatenates `JSON.stringify(event)` into an HTML string. JSON serialization does not escape text for an HTML context. Executing the actual function with an event payload containing `<img src=x onerror=alert(1)>` places that raw tag into the assigned `innerHTML`.

The current canned server responses limit the presently reachable content path. The probe verifies an unsafe rendering sink, **not execution of a remote exploit in the current browser**. It becomes directly relevant when the demo shows real model responses, tools, user content or detailed errors.

**Required change:** build the strong/pre elements through DOM APIs and assign text with `textContent`. Keep output as plain text unless there is a deliberately designed sanitized-rich-text feature; the demo does not need one.

**Acceptance:** markup-like user/model/tool strings display literally, create no nested image/script elements and trigger no event handlers. Ordinary Unicode and pretty-printed JSON remain readable. Use a DOM-capable test or a small browser check for the final security assertion, not only a string comparison.

## B7 — P2: energy activity depends on sample width rather than relative signal level

**Source:** `src/accessflow/perception/audio.py:load_pcm`, `energy_activity` around lines 104–147.

The loader accepts one- through four-byte PCM and preserves the sample width. `energy_activity` compares raw integer RMS against a fixed default threshold of 500.

For the same approximately half-scale alternating signal:

| Input | Observed RMS | Active at default threshold |
|---|---:|---|
| 8-bit PCM | 64 | false |
| 16-bit PCM | 16,384 | true |

An 8-bit centered sample cannot reach an RMS of 500, so the default energy baseline never classifies any valid 8-bit signal as active. Wider sample formats use an entirely different effective threshold. `webrtc_activity` correctly requires 16-bit PCM, but `load_pcm` does not convert valid 8-bit input into that expected format.

**Required change:** choose a documented canonical PCM format or use a normalized energy scale with explicit threshold units. Preserve compatibility deliberately if current experiments depend on integer RMS. Normalize/convert to the VAD's required format at a clearly named boundary; do not silently claim that every accepted WAV is VAD-ready.

**Acceptance:** equivalent relative-amplitude 8/16/24/32-bit signals have comparable activity outcomes after normalization; silence remains inactive; clipping and stereo downmix behave predictably; supported audio reaches VAD without a surprising format error. Record threshold units with experiments.

**Additional experiment:** the linear downsampler has no explicit anti-alias filtering. Before claiming robust resampling, test a signal above the target Nyquist frequency and ordinary speech across supported rates. Consider a maintained resampling implementation if aliasing harms the task. This is a suggested signal-quality test, not a measured ASR regression from this audit.

## B8 — P1 product milestone: acoustic patience is not connected to actual turn completion yet

**Sources:** `src/accessflow/perception/local.py:111–125`, `src/accessflow/turn_policy/heuristic.py`, audio/VAD/timing helpers.

Each WAV input is transcribed as a whole and yields `final=True`. The heuristic policy uses text, revision and final status. Energy activity, WebRTC activity and timing summaries exist as helpers but are not used in that live observation/turn-policy path to decide whether a pause is an unfinished utterance.

This is a legitimate completed-file ASR interface. It does not demonstrate that a live assistant waits through a pause, detects the actual end of a turn, or balances patience against unnecessary delay. Do not relabel helper-unit tests or a prerecorded final transcript as evidence of that research claim.

**Next independent slice:**

1. Define the input unit and timing semantics: completed WAV upload versus incremental recording/activity observations. Preserve the existing route and propose additive fields/events to A if needed.
2. Build replayable labeled speech/activity fixtures and a B-owned policy experiment using an injectable clock. The experiment should work with a fake agent while A's controller changes continue separately.
3. Compare a short fixed-silence threshold, a longer threshold and the proposed combined policy on the same recordings. Keep a semantic-only baseline separate if it calls a model.
4. Include fluent speech so unlimited waiting cannot win; include continuation after a long pause, repetitions, explicit corrections, backchannels, noise and an actually completed utterance.
5. Measure premature completion, missed completion, extra wait after labeled speech end, clarification count and task-relevant ASR errors. Report individual cases and denominators before broad averages.

**Acceptance:** a deterministic replay can show a long pause followed by continued speech without prematurely emitting completion, while fluent completed speech gets a bounded response. Integrate the approved observation/decision contract with A afterward; do not directly mutate controller readiness or action permissions.

The existing heuristic is a baseline. Its `uncertainty=0.0` on every unrecognized final utterance is not calibrated semantic certainty. Label it accordingly; test ambiguous/incomplete final transcripts instead of presenting the number as a measured confidence probability.

## B9 — remaining demo and evidence work

These are openly unfinished features, rather than accusations that the current mock labels are misleading:

- **Microphone:** the microphone button sends a synthetic filename; it does not call `getUserMedia`, record, encode or upload microphone audio. Implement actual capture with an explicit format conversion path. Many browser capture formats are not WAV; do not rename encoded browser audio to `.wav`.
- **Demo integration:** the server hardcodes `DemoPerception`, `DemoReasoner`, `FinalFlagPolicy`, empty tool manifests and `FakeTools`. Add an explicit injection/configuration seam for the real agent supplied by A while retaining a visibly labeled offline demo. The UI should display backend identity and actual tool/state events, not invent results.
- **Connection lifecycle:** there is no `onclose` handler or ready-state guard. Controls can remain usable after the agent/session ends. Disable inappropriate actions while connecting/closed, show the state and provide an explicit new-session path. Test cleanup during recording/upload/disconnect.
- **Vision evidence:** retain frame IDs through ambiguous, failed and superseded observations. Distinguish generic `local/injected-vision` from the actual provider/model in recorded configuration. Coordinate provenance with A's adapter telemetry rather than changing engine behavior.
- **Accessibility checks:** add programmatic input labels, keyboard checks and a concise accessible status region. Dumping every JSON snapshot into one live region can overwhelm a screen-reader user. Keep technical traces available separately from the conversational status.
- **Feedback:** the existing handoff admits no participant feedback or held-out speech-quality evidence. Keep that honest. Use voluntary written feedback by default; do not record/upload participant voices without specific agreement, and do not infer clinical efficacy from a small demo.
- **Environment:** the B handoff records a historical Python 3.11 link issue and Python 3.12 commands. Recheck Atishay's current machine before treating that as still broken. Agree the supported runtime with Mridul; do not edit the shared lockfile independently.

## Independent work packages for Atishay

| Order | Owned change | Can be tested without A's running engine? | Completion evidence |
|---|---|---|---|
| 1 | Browser utterance/revision lifecycle and audio timestamps | Yes, script and adapter tests | Exact emitted events and replacement semantics |
| 2 | Interrupt route and controls; connection/error handling | Yes, fake agent and scripted outputs | Correct scope/timing, usable session after errors |
| 3 | Safe rendering and bounded, complete media validation | Yes, temporary fixtures | Invalid files rejected, literal output rendering, bounded limits |
| 4 | Normalize audio/activity inputs and thresholds | Yes, generated PCM fixtures | Comparable activity across formats and explicit VAD compatibility |
| 5 | Timing-policy replay and matched baselines | Yes, injected clock/fake agent | Premature completion plus added-wait measurements |
| 6 | Real microphone and configurable demo backend | Mostly; use an agreed fake factory first | Actual WAV route, cleanup, visible backend identity |
| 7 | Held-out media cases, optional feedback, presentation evidence | Yes for authoring; integrate before final claims | Provenance, labeled outcomes, honest limitations |

Fix the demonstrated defects before expanding the UI. Send additive interface/dependency proposals to Mridul; do not wait for a hosted service or his personal API quota to write B-owned tests.

## Suggested acceptance commands

From the repository root, using the existing development environment:

```powershell
uv run --offline --frozen --extra dev python -m pytest tests/perception tests/demo -q
uv run --offline --frozen --extra dev ruff check src/accessflow/perception src/accessflow/turn_policy demo tests/perception tests/demo
```

After integration, ask Mridul to run the complete contract/engine suite as well. These commands do not prove real ASR, image quality or browser microphone operation; report those separately when actually exercised. If dependencies are not installed locally, agree the installation step instead of silently dropping the offline flag and downloading models.

## Copy-paste instructions for Atishay's AI

> Audit baseline: `30ed402`. Read `docs/reviews/ATISHAY_AUDIT_2026-09-15.md`, root ownership rules and your current handoff. First check whether your branch already fixes each finding; do not overwrite newer work from another clone.
>
> Work only in perception, turn policy, demo, their owned tests and B-owned feedback/presentation/handoff files. Do not modify the controller, contracts, adapters, evaluation harness or root dependency lockfile. The subprocess ownership instructions conflict; coordinate that explicitly with Mridul. Your existing vision-provider constructor seam already exists, so do not duplicate his provider/planning logic.
>
> Start with browser utterance/revision correctness, timestamp preservation, interrupt routing, safe rendering and complete bounded upload validation. Then normalize audio/activity inputs and build a replayable timing-policy comparison. Use deterministic fixtures and the fake agent so you do not wait for Mridul's engine or API availability. Implement actual microphone/demo integration only through the agreed event/agent interfaces.
>
> For each slice report the reproduced defect, exact owned files changed, test commands/results, contract version, dependency proposals, live versus fake evidence and remaining limitations. Preserve fixture provenance. Do not claim whole-file ASR tests validate live endpointing, remove repetitions indiscriminately, authorize writes from images, hard-code service tool behavior in the frontend, or silently replace a failed model call with canned output. Keep experimental speech/feedback claims limited to the evidence actually collected.

## Work intentionally excluded from this report's implementation list

Mridul must handle the clarification/image authorization deadlock, actual subprocess provider wiring once ownership is resolved, independent effect oracles, scoreboard eligibility/chronology, corpus integration, profiles, root test imports and release packaging. Atishay can supply observations and fixture examples for those tests; he should not repair the A-owned implementation himself.
