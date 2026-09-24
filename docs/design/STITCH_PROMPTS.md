# Google Stitch prompt pack — 23 September 2026

Selected workflow: Atishay follows this pack in order, reviews and retains the Stitch
results, then implements them in his owned frontend. The user's follow-up makes this
the first stage, superseding the earlier optional-Stitch recommendation.
Status updated 24 September 2026: prompts 1–5 were run in the same AccessFlow Stitch
project, which is accessible in the Codex in-app browser, and the canvas contains the
requested frame names. Selected `01-photo-answer` visibly contains a dog photo and answer
at 1280×1033; selected `02-meeting-correction` visibly contains a single Wednesday 5 PM
draft at 1280×1025. Neither matches the requested 1536×1024 size. The approved reference
PNGs were not attached, and the complete local DESIGN.md was not imported byte-for-byte;
the project has a summarized canvas named DESIGN.md. ZIP Export was clicked twice, but no
archive was visible in `C:\Users\adish\Downloads` or `docs/design/stitch/`. Therefore the
generated canvases remain exploratory previews—not accepted production references or proof
of behavior. Review the anchors against the approved sources, then save and verify their
exports before claiming this stage is complete. See [the Stitch export log](stitch/README.md)
for the verified details and remaining manual steps.
Screen generation and click prototypes do not verify the real model, microphone timing,
engine integration or tool cancellation.

## Preparation

Open [Google Stitch](https://stitch.withgoogle.com/). Start one project and provide:

- `DESIGN.md` from the repository root (import as design context when available, or paste it).
- `docs/design/references/approved-photo-conversation.png`.
- `docs/design/references/approved-meeting-correction.png`.

Use the same project for all batches. Preserve one common shell and design system.
Generate a separate readable screen per state, not a collage of tiny app mockups.
Suggested canvas names below are labels for organization, not guaranteed API commands.
Exact controls depend on the current Stitch interface.

## Prompt 1: establish the two approved anchors

```text
I am designing AccessFlow, a voice-first interruptible conversational assistant.
Use my attached DESIGN.md and two approved screenshots as the source of truth.
This is an existing product interface, not a marketing site. Reproduce the visual
direction faithfully; do not explore new branding, colors or navigation.

Create TWO separate 1536×1024 desktop screens of the SAME app shell:

A. 01-photo-answer. Match the approved photo screen: charcoal canvas, warm ivory left
voice console, prominent forest-green/lime waveform, clear speaking status and
“Speak anytime to interrupt” in this design preview. Secondary typing and attachments
stay on the left. Right side shows an uploaded golden retriever photo and a restrained
editorial answer heading, descriptive prose and two useful follow-up suggestions.
Use a clearly identified sample image. Do not imply the preview is a real model result.

B. 02-meeting-correction. Match the approved meeting screen. The left live caption is
“Schedule a meeting on Tuesday… actually, Wednesday at five PM.” The microphone state
is “Listening to you”. The right side has one draft meeting card: Wednesday, 5:00 PM,
People: Not added yet, Duration: Not set, and “Draft only. No invitation sent.” Highlight
only the Wednesday value subtly to suggest an in-place update. No Tuesday strike-through,
before/after timeline, backend logs or fake completion. No specific calendar date or
timezone is invented. This is a draft, and required ambiguity is resolved before execution.

Keep identical header, logo, panel proportions, spacing, type system, buttons and green
palette between screens. Use roughly 30% left console and 70% answer workspace. Voice is
visually primary. Preserve the editorial serif despite generic dashboard styling defaults.
Use stable End conversation and Mute mic positions; Stop speaking is a distinct playback
control when needed, not an unrelated action swapped under keyboard focus.

These are presentation previews, not real calendar or microphone integrations. Include a
small “Design preview” indicator. Do not create login, account pages or external actions.
Generate only these two anchors first so I can review visual fidelity before more states.
```

If the shell drifts, apply this correction before proceeding:

```text
Preserve the approved screenshot composition more closely. Do not restyle the product.
Restore the warm ivory left voice console, the large waveform, the charcoal answer area,
lime/forest-green accents and restrained editorial heading. Put typing and attachments
below voice controls on the left, not in a large bottom composer. Remove unnecessary
cards, debug labels, permanent repair fields, gradients and a correction timeline.
Change only the mismatched areas. Keep the same shell geometry in both screens.
```

## Prompt 2: essential voice and correction states

```text
Using the accepted AccessFlow anchor screens and the SAME DESIGN.md, create the following
additional screens. These are states of one conversation interface, not separate products
or navigation pages. Reuse all shell/component styles. Give each screen its exact name.

03-ready: no microphone access yet, quiet waveform, “Ready when you are”, Start conversation,
secondary typing/upload, and a calm right panel with two example queries. No fake history.

04-listening-pause: a live caption stops mid-sentence, waveform settles, helper “Take your
time”. Keep the current answer/draft visible without prematurely replying or marking success.

05-meeting-tuesday: early draft for “Schedule a meeting on Tuesday…”. Day Tuesday, Time Not set,
People Not added yet, Duration Not set. Same exact card as the corrected Wednesday anchor.

06-meeting-clarify: Wednesday at 5 PM draft preserved, plus one compact clarification asking
who to invite. No auto-invented contacts, date, timezone or length. Do not ask all questions
in one long form. This does not imply remaining date/time ambiguities are already resolved.

07-interrupted: assistant was speaking; user says “Wait, make it Thursday.” Show Listening
to you, current caption, and pending correction without claiming a committed meeting was
undone. Keep the useful answer/card visible. No modal interruption dialog.

08-pending: draft request is being processed in a MOCK tool scenario. Clearly indicate
“Mock tools” and “Scheduling…”, with a contextual Cancel request action. Voice remains usable.
No progress percentage or success before a result.

09-result: a matching mock result confirms a fully specified meeting. Use a clearly marked
sample fixture with explicit date, time, timezone, attendee and duration supplied in that
fixture; do not retroactively invent these fields for the earlier incomplete draft. Show
“Scheduled” and Mock tools. Display only the supplied result details.

10-unknown-outcome: same shell, “I couldn’t confirm whether it was scheduled.” Keep the last
known request visible. Do not claim failure or offer an automatic retry that might duplicate
the meeting. A verification option can be shown only as a supported preview action.

Do not add separate side navigation for these scenarios. Keep live captions compact and
avoid internal slot revisions or tool IDs. These remain clearly labeled design previews.
```

## Prompt 3: general information, images and recovery

```text
Extend the SAME approved AccessFlow project with these separate states. Do not change
palette, typography, shell, console controls or voice priority.

11-information: user asks “Why do leaves change color?” Show a concise useful text answer
with two readable sections, no calendar card and no mandatory stock illustration.

12-comparison: two sample backpack uploads and a request to compare them. Use two source
thumbnails and a clear compact comparison. Label uncertain or invisible specifications
as unknown; do not invent capacity, price or brand from a photo.

13-image-results: user asks for pictures of a requested subject. Show an image-result layout
with sample tool-provided images and source labels, clearly preview-only. This designs a
renderer, not a claim that AccessFlow has image search/generation. Also show a separate
13b-images-unavailable state that explains when no supported image source is available.

14-replaced-image: user says “Use this photo instead” while an earlier photo is being analyzed.
New attachment preview appears, old analysis no longer becomes the current answer. Show
honest waiting rather than a fabricated recognition result; preserve the overall layout.

15-mic-denied: inline microphone permission explanation, actionable retry/help and fully
usable typing. Do not animate a listening waveform or block the entire application.

16-disconnected: freeze voice activity, preserve visible content, show Connection lost and
Reconnect. Do not imply speech is being processed. Do not replay pending writes on reconnect.

17-long-answer: demonstrate readable scrolling and a modest previous-answer/history control,
keeping the voice console usable. No giant chat-bubble feed or forced jump to newest content.

Avoid placing all of these into one dense dashboard. One understandable state per screen.
```

## Prompt 4: responsive views and purposeful variants

```text
Keep the accepted desktop design fixed. Create 390×844 mobile versions of the ready,
photo-answer and corrected-meeting screens. Use a compact voice area, one clear status,
accessible controls, secondary expandable typing/attachments and a single-column answer.
No horizontal scrolling, obscured controls or giant waveform occupying the whole screen.
Account for the onscreen keyboard. Also create a compact 1280×720 meeting view.

Only if useful, provide TWO waveform treatments within the SAME layout: rounded reactive
bars matching the reference, and a slightly softer bar-envelope variant. Keep branding,
colors, typography, controls and panel proportions identical. Do not redesign the whole app.
The reference bars remain the default unless I explicitly choose the alternative.

Show a reduced-motion version with a static voice indicator and immediate field updates.
Do not claim static designs prove contrast, screen-reader support or working motion.
```

## Prompt 5: linked preview and implementation export

```text
Connect the accepted screens into a clearly labeled presentation prototype:
Ready → Listening → Tuesday draft → Wednesday/5 PM draft → Clarification.
Also link Photo answer speaking → User interruption → Listening.
Add deliberate preview controls for traversing these states; do not present fixed delays,
clicks or prerecorded strings as real ASR, model reasoning, cancellation or calendar actions.

Keep the meeting card frame stable while only the changed field transitions. Use subtle
180–240ms value changes and a brief lime-wash highlight; provide a reduced-motion path.
No typewriter answer reveals, permanent pulsing across all controls or flashy transitions.

Export the approved screen images, available frontend assets/code and design rules for
Atishay's coding agent. Include a state/screen index and mark all simulated interactions.
Use the existing project's plain HTML/CSS/JavaScript/FastAPI architecture as the target
when possible. Do not deploy or publish. If an export format is unavailable, keep the
PNG references and DESIGN.md; do not invent missing files or claim production integration.
```

## What to pass back to the coding agent

Retain accepted files under a clearly named `docs/design/stitch/` folder in Atishay's
checkout, with a README listing source project/export date, accepted screen names and
which assets are generated. No API keys, private user audio or unrelated source documents.
Unzip into an isolated directory first; inspect before moving anything into `demo/`.

Give the agent ATISHAY_AGENT_PROMPT.md plus the accepted exports. It should reuse visual
assets/tokens where useful while retaining existing transport, validation, ownership and
tests. It must not replace working protocol code with an unreviewed generated app.

Follow Prompts 1–5 in order, checking the anchors before expanding the screen set.
Only the alternative waveform treatments explicitly marked optional may be skipped
without changing the selected workflow. Missing Stitch access/export must be reported
with the exact manual step Atishay needs to perform; do not silently bypass this stage.
Independent repository inspection, event mapping and test preparation can proceed
while waiting. After the accepted exports are available, continue into implementation
and verification using ATISHAY_AGENT_PROMPT.md and FRONTEND_HANDOFF.md.
