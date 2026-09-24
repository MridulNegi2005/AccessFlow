# AccessFlow frontend redesign — implementation report

**Date:** 24 September 2026
**Branch:** `atishay/perception`
**Surface:** Existing FastAPI demo at `/`
**Design source:** [`DESIGN.md`](../../DESIGN.md) and the approved images in [`references/`](references/)

This report records what changed in the live demo, what was intentionally removed, and
what remains blocked or unverified. The implementation follows the approved voice-first
direction in the written source brief; it is not a pixel-for-pixel reproduction of a
native Stitch export. No Stitch PNG/code export is present in this checkout.

## Before → after

| Area | Before this change | Now | Why |
|---|---|---|---|
| Product frame | A task-entry dock titled “New task” beside a generic task answer stage | Persistent “Voice conversation” console beside an adaptive answer workspace | The voice-first shell now serves every request type instead of making task forms the product identity |
| Main visual hierarchy | Large, vertically stacked text box and separate voice/screenshot upload zones | Quiet ivory console, prominent green waveform, honest voice status and stable controls | The approved reference makes the conversation—not a form—the first action |
| Colors and type | Earlier charcoal/ivory palette with coral recording state and weaker green contrast | `#191D1F` charcoal, `#F7F5EE` ivory, `#173E20` forest, `#ABE865` lime and `#EAF5CE` waveform field; editorial serif answer heading | Matches the approved family without gradients or neon effects |
| Voice capture | Record WAV, then press the always-present “Run task” button | Start recording explicitly; the same control becomes “Finish & send”; a completed recording is submitted automatically | Removes the extra action after speaking while accurately preserving upload-on-stop behavior |
| Typed input | Large textarea presented as the primary task surface | Compact “Or type a message” composer with an explicit Send action | Typing remains fully supported but visually secondary to voice |
| Attachments | Large permanent drop zones and separate upload sections | Small Add image and Upload WAV actions; local removable attachment rows appear only when used | Keeps PNG/WAV capability discoverable without an empty upload tray |
| Request/answer | Task-oriented labels | “Your words” caption, small conversation context, calm prompt examples, editorial answer and contextual follow-ups | Lets the right side change with the request instead of hard-coding dogs or meetings |
| Mode disclosure | Backend details were visually prominent but not concise | Small dynamic `Mock tools` / `Live backend` context plus response provenance | Shows the actual configured demo mode without raw event logs |
| Design-only preview | No separate deterministic preview route | `/?preview=photo` (also `1`) shows a labeled illustrative dog-photo answer; `/?preview=meeting` shows one corrected Wednesday 5 PM draft; both disable recording/upload/send and open no WebSocket | Lets reviewers inspect the two anchor compositions without fabricating live behavior |

### Removed from the normal main view

- The oversized task textarea and its always-visible character count.
- Permanently expanded voice and screenshot upload panels.
- The always-visible large “Run task” CTA. A compact **Send with attachment** CTA now appears
  only when a supported attachment and request are staged; finishing a microphone recording
  submits automatically.
- A fixed device-repair or meeting-specific structure. Meeting details remain plain response
  text unless the engine supplies authoritative structured action state.
- Any suggestion that a recording is streamed to speech recognition while the microphone is
  open. The UI says the WAV uploads after capture ends.

Raw engine events and tool traces remain outside the user-facing answer. No planner, dates,
calendar calls, success states, semantic text parsing or new external integration were added.

## Implemented UI details

- Header: existing lime AccessFlow mark and wordmark, the brief tagline “At your pace.”,
  optional read-aloud switch and New conversation. The switch collapses to a speaker icon on
  narrow screens; its accessible name remains explicit.
- Console: “Voice conversation” title; decorative pale-lime circle; rounded forest/lime bars;
  one large status and helper; stable Start/Finish voice and Upload WAV buttons; labeled latest
  words; compact text composer; Add image; and a conditional attachment list with remove
  actions. The browser does not request microphone permission until Start voice is pressed.
- Waveform: quiet fixed bars when inactive; during capture, bars are scaled from smoothed RMS
  energy in the actual AudioWorklet samples and clamped. No random “listening” pulse is used.
  This is capture visualization, not evidence of live ASR or automatic barge-in.
- Answer: calm initial invitation and two example prompts; content-safe text heading/body;
  uploaded PNG preview when the current response includes one; metadata/provenance; optional
  follow-up prompt chips; and an accessible full-size image dialog.
- Speech output: remains optional and off by default. Stop speaking is only shown during actual
  browser speech and sends the existing `speech` interruption; it is not labeled as task cancel.
- Statuses: Ready, Recording, Sending, Thinking, Speaking, connection lost and microphone
  denial/unavailability are presented in the console. Typed input remains available on capture
  failure. Status updates use a polite live region; reduced-motion preference suppresses motion.
- Boundaries: PNG and WAV only, maximum 8 MiB each in the browser; the existing server-side
  session budget and all identity/order/correlation rules remain in place. Arbitrary HTML is
  still not rendered.
- Layout: desktop uses a roughly 30% console with bounded width and a flexible answer column;
  below 900px it becomes a single scrollable column with a smaller waveform; 390px keeps the
  complete input panel within the viewport width and lets the answer continue below it.

No new dependency was added. Fonts use the declared Geist/Inter and Instrument Serif preference
names with platform sans-serif/Georgia fallbacks; no font is claimed to be self-hosted.

## Owned changes and retained user work

- `demo/index.html`: visual shell, accessible responsive states, dynamic provenance,
  deterministic preview mode, mic-energy rendering and auto-submit after recording stops.
- `demo/app.py` and `demo/design-preview-dog.png`: a dedicated static route and an original
  generated illustrative sample image for the read-only photo preview. This is not the
  approved reference PNG or a user-uploaded photo.
- `tests/demo/test_app.py`: updated the page contract assertions for the compact composer,
  truthful upload-on-stop message, preview-only state and attachment submission affordance.
- `docs/design/STITCH_PROMPTS.md` and `docs/design/stitch/README.md`: actual Stitch workflow
  state and missing native-export procedure.
- `docs/design/IMPLEMENTATION_REPORT_2026-09-24.md`: this current change inventory.
- `docs/handoffs/atishay.md`, `.ai-sync/handoff.md`, `.ai-sync/context.md`,
  `docs/AI_USE_LOG.md`: updated handoff/sync records.
- Browser captures used for review are under `artifacts/accessflow-*`. They are captures of
  this demo, not Stitch exports, approved photo assets or model evidence. The mic-denial and
  disconnected captures are simulated UI states, not screenshots of physical-device failures.

The pre-existing `DESIGN.md` and approved reference PNG bytes were preserved and committed;
the two unrelated untracked websocket/timing follow-up reviews were left intact.
`docs/STATUS.md`, engine files, shared contracts, root configuration/lockfile and
Mridul-owned adapters were not edited. Implementation commit `f0ca543` was pushed to
`origin/atishay/perception` and verified at the remote ref. No deployment,
Stitch publication, booking, payment or outbound communication was performed.

## Verification evidence

The local Edge browser was driven through the actual FastAPI page using the configured
`demo/mock` backends. At the following CSS viewports, `documentElement.scrollWidth` equaled
`clientWidth` (no horizontal overflow):

| Viewport | Console width | Answer top | Notes |
|---|---:|---:|---|
| 1536 × 1024 | 442 px | 82 px | Desktop shell |
| 1440 × 900 | 408 px | 82 px | Mock text request submitted through the composer and rendered |
| 1280 × 720 | 360 px | 82 px | Compact desktop; page scroll height is 933 px, no fixed clipping |
| 768 × 1024 | 709 px | 636 px | Single-column tablet layout |
| 390 × 844 | 362 px | 758 px | One-column mobile; answer follows the complete console |

Additional browser checks: `/?preview=1` reports `socket === null`, shows deterministic sample
copy, disables send/capture/upload and has no horizontal overflow at 390px. The later in-app
browser check also displayed both new anchor previews at 1536×1024 and 390×844; the mobile
meeting card was corrected from a colliding two-column day/time layout to one column, and
the photo asset loaded. The normal local mock WebSocket still returned a text answer with
no console errors. A local in-memory
PNG fixture was staged and removed; the request CTA appeared only after typed context was added
and disappeared after removal. A normal text request traversed the real local WebSocket and
returned the expected mock-agent response with `Mock tools` provenance. A rejected
`getUserMedia` promise exercised the microphone-denial recovery copy while leaving Start voice
enabled; a disconnected-status event exercised the Reconnect state. These are UI-path tests,
not a physical permission prompt/device test. A 768×512 CSS viewport (roughly the content width
of a 1536px desktop at 200% zoom) also remained horizontally bounded and vertically scrollable;
actual browser zoom was not automated.

Exact command results are recorded in the latest Atishay handoff and `.ai-sync/context.md`.
The 24 September final full-suite regression completed: **811 passed, 1 existing xfailed,
2 dependency warnings**. Focused demo tests: **126 passed, 1 xfailed**. Ruff, inline
JavaScript parse and `git diff --check` passed.

### Follow-up browser defect loop (24 September)

**Status: IN PROGRESS.** The visual and interaction work is improved, but native Stitch
exports, physical voice behavior and the full acceptance matrix remain open. This pass used
the local FastAPI demo in the Codex in-app browser; screenshots were inspected in the task,
not saved as native Stitch files or new repository artifacts.

| Route / state | Viewport checked | Defect and outcome | Evidence |
|---|---|---|---|
| `/?preview=photo`, enlarge sample | 1280×720 browser viewport | P2: button previously did nothing; dialog now opens the displayed image and fits without inner scrolling | Before: loaded image with closed dialog after click. After: open dialog, loaded full-size image, `scrollHeight == clientHeight`, inspected screenshot and Escape returned focus to the image button |
| `/?preview=photo`, enlarge sample | 390×844 CSS viewport | Same interaction works without horizontal overflow | Open dialog, `documentElement.scrollWidth` 375px within 390px viewport; inspected screenshot |
| `/`, long mock response | 1280×720 browser viewport | P1: entire long response became a giant serif heading; now a short generic heading precedes the complete unmodified answer body | Submitted through the local `demo/mock` WebSocket; inspected rendered answer and verified full body text |
| Browser read-aloud lifecycle | Controlled Node.js speech-synthesis stub | Stale callbacks after replacement/cancel can no longer set speaking state | `tests/demo/speech_lifecycle_check.cjs` runs under the owned pytest suite; audible output remains unverified |

A new typed/attachment request also cancels obsolete local playback and sends only the
existing speech interruption before entering Thinking; it does not cancel the task.

The page's browser error/warning logs were empty in the checked photo and live-answer tabs.
The follow-up full suite passed: **812 passed, 1 existing xfailed, 2 dependency warnings**;
owned demo tests: **127 passed, 1 xfailed**. Ruff, inline JavaScript parse and
`git diff --check` passed. The Node.js lifecycle regression is optional and explicitly
skips when Node.js is not installed; no root dependency or lockfile changed.

### Not verified / not claimed

- Actual physical microphone permission, recording quality, device removal, live ASR, streaming
  transcription, pause-aware endpointing or automatic speech barge-in.
- Speech-synthesis audio, screen-reader announcements across browser/OS combinations, automated
  contrast compliance, or real-model response quality.
- Native Stitch export assets. The implementation should be compared against the source images
  and written design, but those images were not attached to Stitch during this workflow.
- Exact screenshot-state parity remains unverified: the two local anchor previews now show
  a dog-photo answer and one corrected meeting draft, but they are deterministic sample
  compositions, not native Stitch exports or real engine-driven events.
- Structured live meeting-card updates or completion: current events do not provide the stable,
  authoritative action-card identity/outcome needed to render the Wednesday correction safely.

**Atishay and Mridul need to coordinate** on additive shared evidence for live transcript
revisions, causal answer/frame correlation, structured action identity/write outcome and
speech interruption timing/scope. Atishay owns the console, capture waveform, honest upload
state and demo projection/tests. Mridul owns any shared event/controller/engine semantics and
contract-owned tests. Until they agree, this UI keeps unsupported actions as plain text and
never invents a successful meeting state.

## Stitch export: exact remaining manual action

The Stitch project link and state-frame list are recorded in [`stitch/README.md`](stitch/README.md).
Prompts 1–5 were run, and the project is accessible in the Codex in-app browser. Selected
`01-photo-answer` visibly contains a dog photo and answer at 1280×1033; selected
`02-meeting-correction` visibly contains one Wednesday 5 PM draft at 1280×1025. The two
approved PNGs were not attached (the browser file chooser event timed out and no files
appeared), and the complete local `DESIGN.md` was not imported byte-for-byte, though a
summarized project canvas named DESIGN.md exists. ZIP Export was clicked twice, but no
archive was visible in `C:\Users\adish\Downloads` or `docs/design/stitch/`; no native
export is verified. Review and correct the anchors against the approved sources, then use
**Shift+D** or **right-click → Copy As → PNG** if available, save the reviewed PNGs under
`docs/design/stitch/`, and add their actual filenames/date/dimensions there. Treat any
Stitch code as untrusted generated output and inspect it before reuse.
