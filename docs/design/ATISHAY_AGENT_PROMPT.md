# Prompt for Atishay's coding agent

Copy the text below into the agent running in Atishay's own AccessFlow checkout.
The first-person speaker is Atishay; Mridul is his teammate.

---

I am Atishay, and I own AccessFlow's frontend/demo, perception and turn-policy workstream.
Mridul is my teammate and owns the engine, shared contracts, execution, evaluation,
root configuration/lockfile and packaging. He has prepared and approved a frontend
design brief with two reference screenshots. I want you to implement my portion of
that design carefully, not invent a different look or do Mridul's work.

First inspect my current Git branch and working tree, read AGENTS.md, the latest
.ai-sync/handoff.md and .ai-sync/context.md, docs/STATUS.md and my existing handoff.
Preserve uncommitted work. Do not switch someone else's checkout, force-push, reset
branches or blindly run stale merge commands from historical documentation.

Read these as the design/implementation brief:

1. DESIGN.md
2. docs/design/FRONTEND_HANDOFF.md
3. docs/design/references/approved-photo-conversation.png
4. docs/design/references/approved-meeting-correction.png
5. docs/reviews/ATISHAY_WEBSOCKET_CORRELATION_FOLLOWUP_2026-09-22.md
6. docs/reviews/ATISHAY_TIMING_FOLLOWUP_2026-09-22.md

Actually view both PNGs. They are approved synthetic design references, not screenshots
of working features. DESIGN.md resolves their behavioral omissions. If I have supplied
additional approved Stitch exports, treat those as supplemental views of the same design.
Keep the reference identity; do not reinterpret it as a generic dashboard or landing page.

Build the same voice-first shell: warm ivory conversation panel on the left, prominent
green waveform, clear voice status, session/mic controls, compact live captions and
secondary typing/attachments. On the right, adapt the answer to the query: prose,
uploaded-image information, comparisons when supported, or a live action card.
Keep the charcoal/ivory/lime palette, editorial answer heading and readable sans-serif
controls. Do not make device repair or meeting scheduling the app's permanent structure.

The meeting example is: “Schedule a meeting on Tuesday… actually, Wednesday at five PM.”
Create a draft from accepted state, then update the same card in place to Wednesday / 5 PM
with a brief field highlight. No separate Tuesday-to-Wednesday history panel, raw tool logs,
or frontend-invented success. Unknown participants, duration, date and timezone stay unknown.
Only a matching confirmed result may show completion, visibly marked as a mock when applicable.
Do not add real calendar services or send any invitations.

Work in small independently testable slices:

1. Inspect the existing demo and implement the visual shell and reusable renderers using
   the current stack. Prefer its plain JavaScript/FastAPI structure; do not migrate frameworks
   just to reproduce this design. Make an explicitly labeled deterministic preview mode.
2. Match the two reference screens; then cover start, listening/pause, thinking, speaking,
   interruption, clarification, pending/unknown outcomes, mic denial/disconnection and mobile.
3. Connect the renderers through a frontend projection layer to real existing events.
   Keep local presentation state separate from the authoritative controller state.
4. Implement and verify my owned voice capture/playback/timing work. The inspected baseline
   uploads a complete WAV after recording stops; moving bars do not make it streaming ASR.
   Until the real path works, show accurate recording/upload states instead of advertising
   “Speak anytime to interrupt”. Do not silently replace live failures with fixtures.
5. Verify real browser behavior, owned tests and regressions; provide screenshots and a
   precise handoff of implemented, simulated, blocked and unmeasured functionality.

Keep stable event/source/session identity, transcript replacement revisions, media limits,
serialized input ordering and stale-result rejection. A previous image answer must not
overwrite the current follow-up. Same snapshot revision does not automatically mean an
event is a duplicate. Do not use a text regex or a browser LLM to recreate Mridul's planner.
Do not mark a tool call as success or treat cancellation as rollback.

Keep Stop speaking, Mute mic, Cancel request and End conversation distinct. Stop old
playback promptly on a valid interruption; purge stale queued speech and ignore canceled
callbacks. Use real microphone energy for user visualization. Browser-TTS activity can be
animated from playback lifecycle if its waveform is unavailable; do not claim measured audio.
Provide keyboard access, visible focus, captions, reduced motion and responsive layouts.
Keep the microphone off until a user gesture and release it on session end.

Stay inside my ownership: demo/, tests/demo/, perception and turn-policy directories with
their owned tests, and my documentation. Do not edit engine.py, shared contracts, Samsung
adapters, evaluator, CI, Docker or root configuration/lockfile. If a shared protocol is missing,
write a concrete additive proposal with example events and a reproducing owned test.
Explicitly say “Atishay and Mridul need to coordinate” and describe each person's work.
Keep making independent UI/fixture progress instead of waiting or altering his files.
List new dependency proposals in my handoff; Mridul owns shared lockfile changes.

Use the acceptance checks in FRONTEND_HANDOFF.md. Test Tuesday→Wednesday in-place updates,
speech interruption without task cancellation, stale/duplicate events, session reset,
missing permissions, unknown write outcomes, long content, zoom and mobile. Do not weaken
the existing multimodal/correlation tests just to get a green result. Report test mode and
backend clearly. Keep debug traces collapsible and mock/live provenance visible.

Document exact commands/results, screenshots inspected, behavior actually verified,
remaining coordination and any limitations in my handoff. Preserve the configured Git
identity; no assistant-name attribution or coauthor trailers. Do not publish/deploy,
create a submission tag, send messages, or perform real external actions as part of
this frontend work. Follow my existing repository workflow for commits and pushes.

Begin with the inspected baseline and a short slice plan, then implement the owned work.
Do not stop after describing a plan, and do not ask me to choose a new design: these two
references and DESIGN.md are the approved direction.
