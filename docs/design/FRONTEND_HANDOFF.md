# Atishay frontend implementation handoff

Date: 23 September 2026. Inspected baseline: `3a91ad8` on `mridul/engine`.
This is a read-only implementation assessment and future work brief. Recheck the
actual merged checkout before implementing; it may contain subsequent changes.

## 1. Owner and scope

Atishay implements the approved frontend in `demo/`, with tests in `tests/demo/`.
His perception/turn-policy changes stay in his existing owned directories and tests.
Mridul retains engine, shared contracts, execution, evaluation, packaging and root
configuration/lockfile ownership. This handoff does not resume his paused goal.

The design preparation here does not transfer frontend implementation to Mridul.
Do not modify either teammate's implementation merely to make screenshots look live.
Contract proposals go in `docs/CONTRACT_PROPOSALS.md` with concrete examples; both
teammates coordinate before a shared wire-contract change is implemented.

Do not add real booking/calendar services, authentication, persistent profiles,
databases, external search or a new AI framework to deliver this design.

## 2. What is actually present

| Inspected file / behavior | Consequence |
|---|---|
| `demo/index.html`: inline HTML/CSS/JS; `WebSocket('/ws')` | Evolve the existing app. No framework migration is necessary. |
| `demo/app.py`: FastAPI, per-session Agent, bounded queues, validation and cleanup | Preserve this transport and its safeguards. |
| `demo/recorder-worklet.js` and microphone functions | Browser captures PCM, encodes WAV and sends it after stop. |
| `startMicrophone` / `stopMicrophone` | Current microphone path is not continuous streaming ASR. |
| `show(event)` | Current display prepends raw JSON event cards; this is a debug view, not the approved UI. |
| `sendInterrupt(scope)` | Speech and task interruptions already have distinct meanings. |
| `demo_status` and `demo_error` envelopes | They are demo events, not all instances of shared OutputEvent. |
| `OutputEvent.state` in `contracts.py` | Snapshot includes revision, intent, slots, pending calls, status, correction_pending. |
| `Slot` | Value, confirmed flag, evidence and revision exist; confirmed slot does not prove a write succeeded. |
| `demo/app.py` currently constructs FinalFlagPolicy, FakeTools and MockOnlyAuthorization | A redesigned page does not automatically enable live timing or real tools. |
| Validated PNG/WAV, 8 MiB per file and 16 MiB cumulative session upload admission | Do not expand accept labels or remove bounds as a cosmetic change. |

No playback implementation using browser speech synthesis was found in the inspected
page. Acknowledgment/final events are not proof that audible playback started.
No existing rich answer-block contract or successful real calendar path is assumed.
Consult actual payloads before deciding how to render them.

## 3. Recommended implementation path

### Slice 1: shell and independent previews

- Keep the existing FastAPI/plain-JavaScript approach unless Atishay has a concrete
  reason to change it. Separate CSS/JS into owned files if useful; preserve routes.
- Build shared renderers for voice console, captions, composer, attachments, prose,
  image answer, comparison and action draft/result. Do not create one page per query.
- Use one token source matching root DESIGN.md. No broad restyling or new palette.
- Create deterministic presentation fixtures under `demo/` or `tests/demo/` using an
  explicitly selected preview mode. A preview badge must remain visible. Never inject
  fixture responses when a live request fails or use a production fallback to fake success.
- Match photo and meeting references before polishing secondary states. An uploaded
  photo fixture and generated screenshot are different assets with different provenance.
- Add S01/S02/S03/S04/S05/S10 fixtures first. Next cover interruptions, pending/unknown
  results and narrow layouts. Comparison/gallery are optional extensions.

This slice can run entirely independently from unfinished backend features.

### Slice 2: event projection

- Build a small frontend projection layer between received events and renderers.
  The layer translates accepted evidence; it does not plan tasks, authorize writes
  or duplicate the engine's slot-correction logic.
- Keep local presentation state (focus, panels, microphone/playback state, pending
  upload preview) separate from authoritative task state.
- Handle demo_status/demo_error separately from OutputEvent. Dispatch by validated kind.
- Scope projection by connection/session and source identity. Replace partial transcript
  revisions for the same utterance; do not append each revision as another utterance.
- Preserve legitimate earlier answers as history while preventing a late answer to an
  old request from replacing the current card. Inspect causal IDs and frame provenance.
- Do not globally discard all same-revision events: snapshot revision alone does not
  order every meaningful playback/error/final update. Define deduplication and correlation
  from actual envelopes and cover it with tests. If identity is missing, propose a seam.
- Update one stable card node/key on accepted slot changes; preserve focus and unchanged fields.
- `tool_call` means requested work, not completed work. `cancel_call` means cancellation
  requested, not confirmed rollback. Only supported result evidence can mark completion.
- Do not parse model prose or use regex on user words to synthesize a supposedly authoritative
  meeting card. Use available structured state, or display plain text until a mapping exists.
- Unknown intent/tool shapes should still produce a readable generic answer; the frontend
  must not break because a tool is not called “schedule_meeting”.

### Slice 3: honest voice behavior

- Add microphone energy visualization to the real capture stream. Keep admission and
  upload bounds; stop/release tracks and audio nodes correctly when ended or disconnected.
- For the existing upload-on-stop path, show Recording/Uploading/Processing truthfully.
  That is an interim mode, not the final “Speak anytime to interrupt” experience.
- Atishay owns investigating incremental capture, transcription revisions, turn timing
  and speaker interruption in his areas. Integrate his timing policy deliberately;
  changing CSS while retaining FinalFlagPolicy does not establish pause-aware behavior.
- If using existing browser TTS, drive speaking status from actual start/end/error/cancel
  callbacks. Manage utterance identity and purge obsolete queued speech on interruption.
  Treat callbacks from canceled/previous sessions as stale.
- Local Stop speaking can stop actual playback immediately. Send the appropriate existing
  speech interrupt without treating it as task cancellation. Network latency must not
  hold local audio hostage to a decorative animation.
- Automatic barge-in needs a real user-speech signal and testing against echo, assistant
  playback, ambient noise and backchannels. Energy animation alone is not this signal.
- Do not use a hard-coded silence timer as a disguised replacement for the agreed turn policy.
- Muting must actually stop input admission, not merely change the icon or hide the waveform.
  Determine resume semantics and handle browser errors without losing typed input.

### Slice 4: safe rich rendering and accessibility

- Show uploaded previews as local evidence, with provenance and supported format labels.
  Decode/convert additional formats only in owned code with explicit validation/tests.
- Use plain text or a safe supported formatter for model output. Avoid arbitrary HTML.
- Media returned by tools needs a supported source and safe URL handling. No image search
  or image generation is supplied by this design; explain unavailability gracefully.
- Provide keyboard controls, labels, focus retention, reduced motion, readable contrast,
  bounded captions and non-spamming status announcements.
- Move trace JSON into an optional diagnostics view; keep mock/live provenance readable.
- Stop old microphone, playback, frame previews/object URLs and pending UI handlers on
  session replacement. A fresh conversation must not inherit an earlier user's state.

## 4. Work requiring both Mridul and Atishay

These are coordination gates, not instructions for Atishay to edit Mridul's code.

| Seam | Atishay's work | Mridul's work | Until agreed |
|---|---|---|---|
| Live transcript and draft snapshots | Specify UI/perception observations and test fixtures | Confirm shared envelope/controller emission semantics if existing output is insufficient | Labeled preview; honest upload mode |
| Causal answer/frame correlation | Reproduce ordering and implement demo-side projection/tests | Inspect missing engine provenance or shared-contract gaps | Do not let an unrelated final replace the active answer |
| Stable action-card identity and write outcome | Define presentation requirements and generic fallback | Expose/confirm authoritative operation/result semantics where missing | Draft/pending/unknown; never fabricated success |
| Speech timing and interruption signal | Capture, timing, playback and barge-in tests | Confirm A adapter/controller handling and ordering | Explicit Stop speaking; no unsupported hands-free claim |
| Additional dependencies | Propose exact packages, versions and rationale in B handoff | Review/update shared project config and lockfile | Prefer existing stack; experiment only in isolated env |
| Attachment removal/replacement | Define preview behavior and frame source IDs | Confirm evidence invalidation if shared semantics need changing | Separate preview removal from task evidence changes |

Relevant existing reports, still findings until verified closed:

- `docs/reviews/ATISHAY_WEBSOCKET_CORRELATION_FOLLOWUP_2026-09-22.md`
- `docs/reviews/ATISHAY_TIMING_FOLLOWUP_2026-09-22.md`
- `docs/CONTRACT_PROPOSALS.md`

Atishay can continue the independent shell, fixtures, renderers and owned tests while
these are discussed. No person waits for the other to finish an entire workstream.

## 5. Acceptance and evidence

### Visual checks

- Capture both approved scenarios at 1536×1024 and compact desktop 1280×720.
- Check mobile 390×844 and tablet; no off-screen controls, horizontal overflow or overlapping text.
- Verify long transcript, long heading, missing photo, narrow window and 200% zoom.
- Compare console dominance, margins, typography, palette and card shape against references.
- No raw revision history, device-repair sidebar, forced booking card for informational answers,
  oversized typing area or quietly altered logo. Inspect rendered screenshots, not just CSS.

### Meaningful behavior checks

1. Same utterance partials replace each other; final wording preserves intentional repetition.
2. Tuesday draft becomes Wednesday/5 PM in place; unrelated fields/focus remain intact.
3. No success state from a transcript, confirmed slot, tool_call or frontend timer alone.
4. Late/duplicate outputs and stale frames cannot replace the current request's content.
5. Stop speaking stops playback but preserves the task; Cancel request stays distinct.
6. A canceled playback callback cannot restore “speaking” or play obsolete queued words.
7. Mic denied, muted, unavailable, overloaded and disconnected states offer honest recovery.
8. New conversation releases resources and isolates all prior state/media/playback callbacks.
9. Keyboard-only and reduced-motion operation remain usable; relevant status is announced once.
10. Malformed events and untrusted strings/media cannot inject markup or bypass existing bounds.

Use deterministic event gates for races, not arbitrary long sleeps or screenshot-only tests.
Browser behavior should be tested in a real browser where possible; Python test success
alone does not prove microphone permissions, playback, layout or automatic barge-in.

Existing local commands from repository root (adapt to current environment):

```powershell
uv sync --frozen --extra dev
uv run uvicorn demo.app:app --host 127.0.0.1 --port 8000
uv run pytest tests/demo -q
uv run ruff check demo tests/demo
```

If perception/timing changes, run the applicable owned suites as well. Before integrating,
run the agreed full regression suite. Preserve every failure and label backend/mode.
Do not claim a visual fixture, fake-ASR run or mocked calendar proves live model behavior.

## 6. Deliverables and limits

Deliver implemented owned changes, screenshots of the two anchors and failure/mobile
states, exact test commands/results, dependencies proposed, shared seams still open,
and a short operation guide. Update Atishay's handoff with honest capability labels.

Do not expand this into a new product or sacrifice interruption/correlation correctness
for animation. If time is tight, finish the common shell, text/photo rendering and action
draft states before optional comparison/gallery polish. Keep an honest manual audio mode
until the live path is verified. No calendar invitation or external message should be sent.
