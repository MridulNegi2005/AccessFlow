# AccessFlow design system

Approved direction: 23 September 2026. Status: design specification, not implemented functionality.

This file is the canonical visual and interaction specification for the frontend handoff.
It applies to direct implementation and Google Stitch exploration. Atishay owns implementation.
Read [the handoff](docs/design/FRONTEND_HANDOFF.md) for inspected code, ownership and integration gates.

## 1. Product and design intent

AccessFlow is a general-purpose, voice-first, interruptible conversational assistant.
People can also type and attach supported images. Device repair and meeting scheduling
are examples, not the product's permanent navigation or information architecture.

Reading this as a calm everyday product interface with an editorial visual language:
an ivory voice console beside a charcoal answer workspace, with lime/forest-green accents.
Design variance 4/10; motion 3/10 overall, concentrated in the voice visualization;
visual density 4/10. Keep rest states quiet.

The two approved mockups are the visual anchors:

- [Photo conversation](docs/design/references/approved-photo-conversation.png)
- [Meeting correction](docs/design/references/approved-meeting-correction.png)

Preserve their identity, composition and proportions. They are generated reference
images, not working screenshots or reusable frontend assets. This specification
resolves behavioral omissions in the static mockups. Do not reproduce the UI as one image.
The approved serif and warm ivory explicitly take precedence over generic skill bans
on serif software interfaces or warm neutrals. There is no marketing hero or landing page.

## 2. Fixed shell, changing answers

The same page accommodates every scenario. Do not build a separate application or
navigation item for dogs, meetings, comparisons, weather or support.

**Header:** AccessFlow mark and wordmark; the tagline “At your pace.”; New conversation;
settings if implemented. The mockup avatar is decorative and does not require accounts,
login, profile storage or an online-status feature. Omit it if there is no useful action.

**Left: persistent conversation console.** In order:

1. Small “Voice conversation” label.
2. The dominant waveform with generous clear space.
3. One truthful voice status and a short, state-specific helper.
4. Stable-position session and microphone controls.
5. A compact live caption or latest user utterance, with a visible text label.
6. Secondary “Or type a message” composer with a labeled send control.
7. Supported attachment action and removable attachment thumbnails when present.

The user should not need to hold a microphone button or press “Run task” after speaking.
Start conversation is an explicit user gesture for microphone permission and playback.
Do not show an empty attachment tray or permanently expanded large text form.

**Right: adaptive answer workspace.** A small context label, a restrained answer heading,
then the useful content. Use prose, an image, a comparison, a list or one action card
according to the request. Suggested follow-ups are optional and contextual. No second
large composer. Keep earlier useful answers available through a modest conversation
history control; do not replace the entire interface with chat bubbles or a debug feed.

Technical traces belong in a collapsed developer view. Keep a small, readable mode
indicator (“Design preview”, “Mock tools”, or the configured live backend) available;
do not hide provenance to make a demonstration look live.

## 3. Palette and typography

These are implementation tokens chosen to match the references, not measured pixel samples.

| Token | Value | Role |
|---|---|---|
| canvas | `#191D1F` | Main charcoal background |
| surface-dark | `#22272A` | Occasional action card |
| surface-ivory | `#F7F5EE` | Voice console |
| text-on-dark | `#F5F4EE` | Main answer text |
| muted-on-dark | `#BDC3C7` | Supporting copy on dark |
| text-on-light | `#18221B` | Console body and labels |
| muted-on-light | `#59615C` | Console secondary text |
| lime | `#ABE865` | Active waveform, small accents and focus |
| forest | `#173E20` | Console primary controls, darker waveform bars |
| lime-wash | `#EAF5CE` | Waveform field and brief changed-value highlight |
| border-dark | `#4F585C` | Functional borders against charcoal |
| border-light | `#C9CEC5` | Dividers and decorative borders on ivory |

Use a stronger border/focus indicator where a faint divider would not identify a control.
Error meaning must be conveyed in words and an icon; do not rely on color alone.
No pure-black panels, rainbow gradients, neon outer glows or purple substitutions.
Forest, lime and lime-wash form one green accent family.

- Functional copy: **Geist**, with `system-ui, sans-serif` fallback; 16px body, 1.5 line height.
- Answer headings: **Instrument Serif**, 38–52px desktop, 30–38px narrow; regular weight.
- Keep controls, metadata, times and small labels sans-serif. Serif emphasis may appear
  on the meeting's day value, matching the reference, but never on dense field labels.
- Wordmark approximately 28–32px semibold; section headings 20–24px; labels 12–13px
  with modest letter spacing; secondary copy 14–16px. Essential content stays readable.
- Bound ordinary prose to about 60–68 characters per line. Long headings wrap naturally.
- Use existing licensed font assets if available; otherwise begin with fallbacks.
  Self-host chosen fonts with their license when integrated; no runtime font dependency
  required for offline demos. Do not pretend a specific font is already installed.

## 4. Layout and responsive behavior

- Reference canvas: 1536 × 1024. Also verify 1440 × 900, 1280 × 720, 768 × 1024 and 390 × 844.
- Desktop outer spacing 24–32px, header 64–84px, console approximately 30% of usable width
  (usually 340–450px), gap 32–48px. Main workspace consumes the remaining width.
- Use CSS Grid, with a bounded console column and `minmax(0, 1fr)` answer column.
- Console radius 24px; action/image radius 16–20px; input radius 12–16px; pill controls.
- Space scale: 4, 8, 12, 16, 24, 32, 48px. Most separation comes from space, not nested cards.
- At ordinary desktop sizes, keep header stable and let answer and console content
  scroll within their regions as necessary. Give scroll regions keyboard access.
- At short heights or high zoom, let content reflow/scroll instead of clipping controls.
  Do not impose screenshot-height absolute positioning.
- Below roughly 900px, use a single column. Compress the waveform area to about 120–160px,
  followed by status/controls, optional collapsed typing/attachments, then the answer.
  Keep the user in control of expansion; no giant decorative voice panel above every answer.
- Mobile uses normal vertical scrolling; no horizontal overflow or nested scrolling trap.
  Account for virtual keyboard and safe areas. Avoid a fixed overlay covering content.
- Keep the microphone discoverable on mobile with a compact voice strip if needed;
  it must not obscure the answer or keyboard focus.

## 5. Voice states and controls

Keep microphone capture, assistant playback, connection state and task state separate
internally. Present one primary human-readable status. A microphone may remain enabled
while the assistant speaks; this is not a contradiction if the labels describe both accurately.

| Situation | Primary label | Visual treatment / available action |
|---|---|---|
| Not started | Ready when you are | Quiet waveform; Start conversation |
| Permission pending | Allow microphone access | Stable indicator; typing remains usable |
| User speaking | Listening to you | Microphone-driven waveform; Mute mic |
| Pause within speech | Take your time | Waveform settles; do not infer completion from the animation |
| Accepted turn, waiting | Thinking | Small slow activity cue, never fabricated speech amplitude |
| Actual audio playback | AccessFlow is speaking | Playback-driven motion when measurable; Stop speaking |
| User barges in | Listening to you | Stop obsolete playback; restore user waveform |
| Muted | Microphone muted | Static muted mic, Unmute mic; text still works |
| Disconnected | Connection lost | Static state and reconnect action; do not pretend to listen |
| Session ended | Conversation ended | Microphone released, playback stopped; Start new conversation |

Start/End conversation occupies a stable location; Mute/Unmute mic occupies another.
During playback, provide “Stop speaking” as a separate clearly labeled control.
Do not silently turn a focused Stop speaking button into an End conversation button.
The differing controls in the two mockups illustrate states, not permission to shuffle focus.

**Stop speaking** stops playback and sends the existing speech interruption when needed.
**Mute mic** disables capture/admission; it does not cancel a task or restart the session.
**Cancel request** is contextual to a pending action; it is not a synonym for muting.
**End conversation** closes the active session and cleans up capture/playback. If a write
is unresolved, explain that ending a session cannot undo a committed external effect.

Only show “Speak anytime to interrupt” when that path works in the selected mode.
For capture-and-upload mode, use honest recording/upload labels instead. Do not advertise
continuous conversation just because the waveform moves.

## 6. Motion specification

The waveform uses rounded forest/lime bars over a pale lime circular field. It is the
main animated element. Drive user bars from microphone energy while permitted; smooth
the signal and clamp peaks. Never draw random energetic bars during user silence.

When assistant PCM is unavailable (for example browser speech synthesis), use a gentle
playback activity animation tied to real start/end/cancel callbacks, not a claim of
sample-accurate audio visualization. Do not route the assistant's audio into a user turn.

Suggested timings, to tune after implementation:

- State transition: 120–180ms opacity change.
- Changed slot: 180–240ms crossfade/small vertical movement inside a stable-size field.
- Changed-field lime-wash emphasis: settle back within 700–1000ms.
- Answer appearance: 160–220ms fade; no slow typewriter effect on an entire answer.
- Interruption: stop playback immediately on the appropriate signal; do not wait for
  an exit animation before handling the interruption.

Prefer transform and opacity. Pause animation when inactive or the page is hidden.
Respect reduced motion: static waveform/status and immediate value substitution, with
no pulse, sliding text or animated highlight. Never flash, shake, or loop every component.

## 7. Meeting correction: exact interaction

This is an example of a reusable action card, not a hard-coded planner workflow.

1. “Schedule a meeting on Tuesday…” produces a **draft** when the authoritative state
   supports it. Day: Tuesday. Time: Not set. Unknown people/duration stay visibly unknown.
2. During an unresolved correction, retain the card; do not dispatch a write because
   a timer expired or the interface looks complete.
3. “…actually, Wednesday at five PM.” updates the same draft's day and time when accepted
   state arrives. Keep card identity, focus, unrelated fields and surrounding content stable.
4. Briefly highlight Wednesday. Remove Tuesday from the card instead of retaining a
   before/after audit trail. The natural spoken caption may contain both words.
5. The card says “Draft only. No invitation sent.” until evidence supports another status.
6. Ask a concise clarification only for required missing/ambiguous details. Do not invent
   participants, duration, calendar date, timezone or conferencing link. “Five” alone is
   not inherently 5 PM; this approved example explicitly says five PM.
7. A supported tool invocation can show “Scheduling…”. A successful, matching result
   may show “Scheduled” (with **Mock tools** provenance for this project's mocks).
   Timeout may mean “Couldn’t confirm whether it was scheduled”, not “Failed, retry now”.
8. If correction arrives after an actual committed effect, do not visually rewrite history
   as though that effect never happened. Explain the existing result and supported next action.

Actual date/time fields must eventually identify an unambiguous date and timezone when
the tool requires them. The reference's weekday-only card is deliberately a draft.
Do not add a compulsory “Confirm” step to every task; respect already-given authorization
and the controller's requirements. No real meeting/calendar service is requested here.

## 8. Answer families and screen coverage

These are content states within one shell, not separate product pages.

| ID | State / sample request | Right workspace | Priority |
|---|---|---|---|
| S01 | Start a conversation | Calm invitation and two useful example prompts | Core |
| S02 | “Why do leaves change color?” | Short explanation with two meaningful sections; no forced card | Core |
| S03 | “What kind of dog is this?” + photo | Uploaded image and grounded descriptive answer, matching reference | Core |
| S04 | “Schedule a meeting on Tuesday…” | Tuesday draft, time unknown | Core |
| S05 | “…actually Wednesday at five PM.” | Same draft, Wednesday / 5 PM highlight, still listening | Core |
| S06 | Meeting missing required details | Existing draft plus one contextual clarification | Core |
| S07 | Assistant speaking, then user interruption | Preserve useful answer, switch voice state, await latest request | Core |
| S08 | Read or write still pending | Existing content plus honest progress, contextual cancel if supported | Core |
| S09 | Confirmed mock action / unknown write outcome | Distinct truthful result states; no automatic write retry | Core |
| S10 | Mic denied, unavailable or disconnected | Recoverable inline message and usable text input | Core |
| S11 | “Compare these two backpacks” + two images | Comparison with visible source references and unknown facts omitted | Extension |
| S12 | “Show pictures of…” | Image gallery only from available image results; otherwise explain limit | Extension |
| S13 | Long answer and conversation history | Scrollable content with stable voice console; no forced scroll on user | Extension |
| S14 | “Use this photo instead” while reasoning | New preview, pending analysis; reject obsolete image result | Integration |
| S15 | No useful evidence / tool error | Plain explanation and one relevant next action | Core |
| S16 | Mobile versions of S01, S03 and S05 | Same identity, compact voice area, one-column answer | Core |

Build S01–S10/S15/S16 using a small set of reusable components, not sixteen page files.
Extension states are design coverage, not authorization to add web image search, image
generation, a new planner, document ingestion or new external integrations.

## 9. Images, captions and input boundaries

- Distinguish “Your uploaded photo”, “Tool-provided image”, and a clearly labeled design
  fixture. Do not present the generated reference dog photograph as real submitted evidence.
- Render media from validated supported sources. Text cannot magically become an image
  result, and arbitrary tool HTML must not be injected into the page.
- Reference PNGs are design guides; choose a licensed/team-owned independent dog image
  for the actual demo. Preserve aspect ratio, use meaningful alt text and sensible crops.
- Current code validates PNG and WAV. Do not advertise JPG, HEIC, PDFs or “any file”
  until supported conversion/validation has actually been implemented and tested.
- Use “Add image or audio” in the working UI if those remain its supported formats.
  The reference's “Add image or file” is general concept copy, not a capability promise.
- Preserve limits, source identity, revisions, ordering and session isolation when redesigning.
  Removing a visual preview must not silently erase already-accepted backend evidence.
  If attachment withdrawal is unsupported, coordinate that behavior explicitly.

## 10. Accessibility, honesty and acceptance

- Keyboard-operable controls, explicit labels, visible focus, at least 44px touch targets.
- Verify contrast in implementation; target readable text and distinguishable controls.
  A bitmap is not proof of accessibility compliance.
- Captions available independently of optional speech output. Avoid announcing every
  transcript chunk to assistive technology; announce meaningful completed/status changes.
- Optional audio playback must be stoppable and never required to understand the answer.
- No microphone activation before the user's gesture. Clear mute/permission/recording state.
- Content-safe text rendering; validate media/link schemes; prevent untrusted outputs from
  creating executable scripts, controls or instructions to the application.
- Placeholder UI must be marked preview and separated from the live event adapter.
- Raw state, tool IDs and backend logs stay out of the normal conversation view.
- No client-side semantic parsing of “Tuesday” into a real action; frontend state represents
  evidence from the agent, not an independent source of permission or task truth.

Acceptance requires visual checks against both references plus behavioral checks for
interruption, stale response correlation, live-caption replacement, session reset,
permission denial, disconnected state, narrow screens, zoom and reduced motion.
Detailed implementation sequence and ownership are in the handoff.
