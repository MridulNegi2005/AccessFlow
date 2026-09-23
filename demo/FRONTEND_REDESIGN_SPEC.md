# AccessFlow frontend redesign specification

**Status:** Implementation complete; target-size browser-pixel review completed in an isolated local Edge session.
**Prepared:** 23 September 2026
**Current surface:** The single FastAPI/WebSocket demo at `/`.
**Visual reference:** [Input Dock + Answer Stage](../artifacts/design-explorations/02-input-dock-answer-stage.png).

![Selected Input Dock and Answer Stage concept](../artifacts/design-explorations/02-input-dock-answer-stage.png)

## Goal and decisions

Rebuild the demo as a polished, responsive task workspace that closely follows the reference's composition: a warm, bright input panel on the left and a spacious dark answer area on the right. Use AccessFlow service or accessibility tasks and actual session output in place of the concept image's dog example.

Decisions already made with AJ:

- Add **optional browser text-to-speech** for responses. It is off by default and has a working stop control.
- Remove developer controls from the main UI: the explicit partial-send button, raw event stream, full backend banner, and standalone Stop task button.
- Send **debounced partial text automatically** while the user types; Run task sends the final revision.
- Keep the current one-session demo model. Do not imply accounts, saved history, real transactions, or verified model quality.

This work is a frontend redesign and a small demo-adapter addition for displaying observed input. It does not require changing the shared controller, contracts, root dependencies, or tool authorization.

## Change inventory: current → planned

| Area | Current demo | Planned change |
| --- | --- | --- |
| Overall layout | A narrow, centered, vertically stacked page of similar dark sections. | Full-width dark workspace with a persistent ivory input dock on the left and a flexible answer stage on the right. |
| Header | Text-only AccessFlow title and a paragraph containing the complete backend label. | Original lime SVG mark, stronger wordmark, short tagline, and compact voice-output toggle. Show backend provenance beside a response. |
| Text input | Single-line `Transcript` field with `Send final transcript` and `Send partial` buttons. | Large multiline task field with a real label, character count, automatic draft revisions, and one prominent Run task button. Remove the visible partial button. |
| WAV input | Browser file input plus separate `Upload WAV` button. | A secondary Upload WAV action inside the voice zone. Stage a validated file and show its name/size before running. |
| Microphone | Separate Start microphone capture and Stop and upload microphone buttons. | One large record control in a pale-lime waveform tile. Tap to start and tap to finish; show recording duration and errors inline. |
| PNG input | Browser file input plus separate upload button. | Clickable, keyboard-usable PNG drop zone with drag feedback and a selected-file row with thumbnail/remove action. |
| Media limits | Browser precheck of 8 MiB per file; server also enforces a 16 MiB decoded session budget. | Preserve both limits. Correct the concept image's unsupported “PNG, JPG, HEIC up to 10MB” copy to **PNG, up to 8 MiB**. WAV also remains up to 8 MiB. |
| Interruptions | Always-visible Stop speaking and Stop task buttons. | Show Stop speaking only during speech playback; cancel browser speech and send the existing `speech` interrupt. Remove standalone Stop task; New task confirms before ending active work. |
| Results | Newest-first event cards with raw JSON. | Readable request summary, actual response text, image preview where relevant, clarification, errors, and a follow-up composer. Remove raw event cards from the product UI. |
| Backend disclosure | Large “Perception and reasoning backends” line above all controls. | Small, truthful “Demo response” or local-backend label near generated output. Never present a mock answer as a live-model answer. |
| Session reset | Restart session button next to the event stream. | New task control with a confirmation if work is active; reset capture, response, media previews, and speech cleanly. |
| Follow-ups | User reuses the main transcript field. | Add a visually secondary follow-up composer and three optional prompt-fill chips once an answer or clarification exists. |
| Speech output | No browser audio playback, despite a Stop speaking engine control. | Use browser `speechSynthesis` when explicitly enabled. Speaking pill appears only while playback is active. |
| Responsive behavior | Basic narrow-page wrapping. | Defined desktop, tablet, and mobile layouts, with no nested scroll trap or horizontal overflow. |

### Explicitly retained beneath the new presentation

- The existing WebSocket route, output kinds, session-scoped agent state, source IDs, event sequence, transcript revision rules, media validation, microphone WAV encoder, ordered media sending, and mock/local backend separation.
- The backend's `task` interrupt capability and automated protocol tests, even though the standalone Stop task control leaves the screen.
- The current security boundary: model text and filenames are inserted as text, never trusted as HTML or instructions.

## Detailed visual contract

### Page frame and grid

- Design against the reference's approximately **1487 × 1058** frame; verify implementation first at **1440 × 1024**.
- Page background: `#15171C`. Keep a quiet, low-contrast texture only if it does not reduce readability; a flat color is acceptable. The design relies on contrast and typography rather than decorative effects.
- Desktop header height: **88 px**. Horizontal padding: **40 px** in the header, **20 px** around the main panel. Brand mark is an original three-part lime symbol; do not crop the generated reference into the UI.
- Desktop main grid: left panel **448 px**, gap **56 px**, right side `minmax(0, 1fr)`. The right side keeps at least **32 px** breathing room at the viewport edge.
- The left panel starts just below the header, with **24 px corner radius**, roughly **22 px inner padding**, an ivory `#FBF8F2` fill, and minimal shadow. Let the document scroll when its content exceeds the viewport instead of creating a small internal scrollbar.
- Use an **8 px spacing unit**; important gaps are **16, 24, 32, and 56 px**. Lines and grouping do the work before shadows or extra cards.

### Color and typography

| Role | Target |
| --- | --- |
| Dark page | `#15171C` |
| Input panel | `#FBF8F2` |
| Dark ink on ivory/lime | `#17191B` |
| Primary text on dark | `#F7F4EE` |
| Muted text on dark | `#B3B6BA` |
| Dark dividers | `#393C40` |
| Primary action | `#A8EC59` |
| Voice tile | `#EAF2D5` |
| Stop/interruption | `#FF6548` |

- Bundle a licensed sans font for interface text and a licensed, restrained display serif for the large answer; include local font files and licenses so the page works offline. Use appropriate system/Georgia fallbacks while fonts load.
- Wordmark: about **28 px**, bold sans. Section headings and control labels: **15–18 px** sans. Main task text: **20 px**, approximately **1.45** line height. Answer headline: about **48 px**, **1.08** line height on desktop, no more than two or three lines before the body. Answer paragraphs: **18–20 px**, comfortable line length.
- Make the exact font choice and weight a screenshot comparison decision during implementation; prioritize the reference's strong serif/sans contrast and text metrics over a decorative font name.

### Left input dock

1. **Title row:** compact sparkle mark and “New task,” left aligned. No decorative metric or fake account information.
2. **Task textarea:** about **236 px high**, **16 px radius**, thin neutral border, **20 px padding**. Counter in the lower right uses the actual **16,384-character** browser text bound rather than the concept image's “2000.” Empty, focused, populated, error, and disabled states must be visually distinct.
3. **Voice tile:** about **120 px high**, pale lime, softly rounded. A centered dark circular control approximately **82 px** wide holds the mic icon; thin static waveform bars flank it. Below, show “Tap to record,” then “Recording · 00:12 / Tap to finish” while active. The waveform animates only during recording and only when motion is allowed. Keep Upload WAV as a subtle secondary action.
4. **Image drop zone:** about **172 px high**, thin dashed border, centered **44 px** image icon, “Drop a PNG image,” and the true file rule. On dragover, tint the zone and strengthen its border; on invalid file, show a specific inline message without clearing the task draft.
5. **Selected media:** compact roughly **74 px** row per staged file, with PNG thumbnail when available, filename, size, and remove button. Revoke thumbnail object URLs on replacement/reset. Avoid claiming an image description before the vision backend produces one.
6. **Run task:** full width, roughly **66 px high**, lime background and dark text/play icon. Disabled until text or audio exists. On submission, keep its position and show a short sending/processing state. Once a task has run and the user edits the left draft, change its copy to “Run updated task.”
7. **Footer copy:** one small truthful note about combining text, voice, and a PNG in the current session. Do not claim support for documents, arbitrary files, or persistent tasks.

### Right answer stage

1. **Request summary:** small “What I heard” label near the top and up to two lines of exact user text or actual ASR text. A WAV without a transcript reads “Audio received · processing” or “Audio received · demo/mock”; no guessed words.
2. **Voice status:** compact pill aligned to the upper right when speaking, with subtle waveform, “AccessFlow is speaking…,” and a coral stop button. When voice is off, reserve no fake speaking status.
3. **Answer:** large serif opening line drawn from the real final payload, followed by the full body. Preserve meaning and order. Format actual newline-separated content cleanly; do not infer new facts or build dog-style attribute lists from unstructured text.
4. **Image and details:** when an image was submitted, display it in the large media region, approximately **480 × 465 px** at the reference width. Use a thoughtful preview crop and offer full-image viewing with `object-fit: contain`. The adjacent answer/details column may include only data from the output or confirmed inputs: submitted modalities, visible clarification, and backend provenance. Without an image, the answer expands into the available width.
5. **Below the answer:** thin rule, “Explore further” copy, and three restrained chips: “Explain more simply,” “What evidence did you use?”, “What should I do next?” Clicking a chip fills the follow-up field; it does not submit it.
6. **Follow-up composer:** approximately **70 px high**, wide pill shape with a clear send action and a visible keyboard focus state. It appears after an answer or clarification, which avoids two competing text inputs on the empty screen.
7. **Initial right-side state:** spacious headline and brief instruction explaining how to start a task. Do not preload a fabricated final answer, stock dog photo, confidence score, or session history.

## Interaction states and source of truth

| State | Screen behavior | Source |
| --- | --- | --- |
| Connecting | Subtle connection indicator; Run waits or queues within the existing bound. | WebSocket ready state and `demo_status`. |
| Drafting | Local text remains editable; send one debounced partial revision after about **600 ms** of inactivity. | Browser draft plus existing transcript event format. |
| Recording | Live timer, active voice tile, stop action, and clear permission/unsupported-browser errors. | Browser microphone and AudioWorklet. |
| Media staged | Local thumbnail or WAV filename, remove/replace action. | Selected local file; no server success implied. |
| Uploading | Per-file progress/working label and disabled duplicate Run action. | Browser read/send and server `media_received` notice. |
| Processing | Quiet loading indicator; preserve request and media preview. | Sent final request until controller output. |
| Clarification | One prominent question with follow-up composer ready. | `clarify` output only. |
| Final | Render actual answer and provenance label; enable follow-up. | `final` output only. |
| Error | Inline, recoverable message next to affected input or answer area. | Browser validation, `demo_error`, or `error`. |
| Disconnected | Keep visible draft and local media; offer reconnect/new task without implying queued work succeeded. | WebSocket close/error. |
| Speaking | Speaking pill and working stop control. | Browser `speechSynthesis` playback state, never text generation alone. |

### Event and submission rules

- Text drafts use the existing utterance ID and strictly increasing revisions. Run task cancels the draft timer and sends the final revision in sequence. A later edit starts a new utterance ID. Do not send empty drafts.
- Limit pending browser messages to the current **16-item** queue and surface queue-full or closed-session errors in readable copy.
- Stage at most one active PNG and one active WAV/recording in the left panel. On Run task, serialize chosen media before the final text transcript so the answer can use the submitted context. If the user has only an image, prompt for a question or spoken request instead of promising a result from an uncertain image-only path.
- Add a demo-only `demo_observation` notice where needed for “What I heard,” with `modality`, `source_id`, `revision`, `text`, `backend`, and `final`. This is display evidence, not a new authoritative session state or a shared contract change. Ignore stale revisions in the browser.
- Render `acknowledge`, `clarify`, `final`, `error`, `demo_status`, and `demo_error` into the corresponding UI states. Keep all model and filename text escaped via DOM text APIs.
- Optional TTS is **off by default**. When enabled, speak only `final` and `clarify` text through browser `speechSynthesis`; use a system voice. Cancel playback on a new response, new task, recording start, page exit, or stop click. The stop click also sends the existing `speech` interrupt and leaves the task available.
- New task clears local state and starts a fresh WebSocket session. Confirm first if recording or processing is active. The standalone task-cancel control stays out of the main UI as AJ chose.

## Responsive and motion specification

| Width | Layout |
| --- | --- |
| **1280 px and wider** | Two columns, roughly **448 px** input dock and flexible answer stage. Image and answer details sit side by side. |
| **900–1279 px** | Two columns with a **360 px** input dock. Stack image above detailed answer text where the right side becomes too narrow. |
| **640–899 px** | Stack the ivory input panel above the answer stage with about **24 px** separation. Keep the answer visually spacious. |
| **Below 640 px** | **16 px** page gutters, full-width dock, answer headline near **36 px**, full-width image, vertically wrapping chips, and no horizontal scroll. The follow-up field stays in normal flow so the mobile keyboard cannot cover it. |

- Use **150–220 ms** hover/focus transitions for color, border, and small elevation changes. A new answer may fade in and rise at most **8 px** over roughly **240 ms**. Avoid large page shifts, continuous glow, or decorative parallax.
- `prefers-reduced-motion` removes movement and waveform pulsing while preserving clear state colors and text.
- Minimum interactive target **44 × 44 px**. Maintain visible keyboard focus, logical tab order, Escape behavior for the image viewer, readable error messages, and polite live announcements. Blocking failures use an assertive announcement. Verify body text at WCAG AA contrast.

## Original implementation plan (superseded by the implementation record below)

| Owned area | Planned work |
| --- | --- |
| `demo/index.html` | Semantic header, input dock, answer stage, live region, and accessible controls. Remove old section/event-card markup. |
| `demo/` CSS and JavaScript | Separate visual styles and page behavior from the current all-in-one HTML; keep vanilla browser APIs and local asset serving. |
| `demo/app.py` | Serve local CSS, JS, fonts, and SVG assets; emit the narrow demo observation notice if required for actual transcription display. Preserve existing WebSocket protocol and limits. |
| `demo/favicon.svg` | Replace the old blue placeholder mark with the new original lime mark. |
| `tests/demo/` | Replace brittle old-markup assertions with checks for current controls, event mapping, revision ordering, media ordering, upload errors, TTS stop behavior, and WebSocket recovery. |

Do not add a framework, account system, database, persistent sessions, unsupported file types, custom voice service, new controller state, real bookings, or payments. The selected concept image is a visual target, not a page asset to paste into the browser.

## Acceptance checklist

1. Inspect the rendered empty and populated pages at **1440 × 1024**, **834 × 1194**, and **390 × 844**. Compare geometry, hierarchy, colors, and typography against the selected reference; open and inspect the screenshots rather than relying on file creation alone.
2. Exercise text draft → final, a corrected draft, PNG drop/select/remove, WAV upload, microphone record/stop, clarification, follow-up, mock final, optional local-backend final, speech playback/stop, new task, invalid media, permission denial, and disconnection.
3. Confirm no horizontal overflow, clipped controls, stale media preview, relevant console exception, keyboard trap, or misleading mock/live label.
4. Run the focused demo tests, full repository tests, lint, and diff checks. Keep backend, failure, and expected-failure claims tied to actual results.
5. Keep the implementation record below current. Do not describe the first implementation as visually approved until the preview has been inspected at the target sizes.

## Implementation record

The first implementation replaces the stacked dark developer demo with the selected ivory input dock and charcoal answer stage. It adds a multiline request composer, automatic 600 ms partial revisions, staged WAV/PNG previews with removal, tap-to-record WAV capture, a readable answer/clarification panel with provenance, follow-up chips and composer, optional browser speech output, and an Escape-dismissible full-image dialog. The page uses system font stacks and does not download font assets.

Removed from the visible page: the manual partial-send button, raw event JSON cards, large backend banner, separate upload buttons, and standalone Stop task control. Retained in the transport: event sequence and source IDs, transcript revision semantics, the existing speech interrupt, microphone WAV encoding, per-file limits, bounded WebSocket queues, and one-session behavior.

Mixed-media submissions are sent sequentially through the existing session. The engine may produce an intermediate final after a final media observation; the UI holds those older finals while the submitted run is active and displays the result after the last submitted source's final observation. A final text request is last and receives cumulative session context. This is presentation coalescing, not an atomic backend transaction.

The demo emits a final-only, demo-only observation notice carrying modality, source ID, revision, text, backend, and final state. This does not change shared contracts or session authority. The existing favicon is retained; the header uses an inline lime mark.

Implemented responsive breakpoints: 448 px dock and answer stage at 1280 px and wider; 360 px dock from 900–1279 px; stacked dock and answer stage from 640–899 px; compact mobile treatment below 640 px. Image and answer details stack when the available answer width is narrow. Secondary buttons, prompt chips, TTS switch, connection action, and media-removal controls use 44 px minimum hit areas.

Follow-up hardening after independent source review: the image area and removal controls now truly lock during a run; screenshot preview is a keyboard-focusable button; the response article no longer duplicates its separate live announcement; narrow image layouts remain stacked; speech stops when microphone recording begins; choosing a microphone recording replaces a staged WAV only after capture setup succeeds; and the stage now provides visible connection/reconnect plus per-file preparing/sending status. Response headlines can wrap arbitrary backend text without widening the page.

Browser verification used the actual local FastAPI demo in an isolated Edge profile at 1440 × 1024, 834 × 1194, and 390 × 844. Empty state was visually inspected at all three sizes; a mock text response was inspected at all three; a generated 640 × 360 PNG was staged and submitted, its preview button focused and activated, and the full-size dialog loaded the expected image dimensions. The document stayed within each viewport in the text and PNG scenarios (desktop/tablet document width 1425/819 px due to the vertical scrollbar, mobile 390 px). The mobile header wrapping found in the first screenshot was corrected and recaptured. A desktop empty-state capture is available locally at [`FRONTEND_REDESIGN_PREVIEW.png`](FRONTEND_REDESIGN_PREVIEW.png); it is excluded from Git by the existing PNG ignore rule.

Verification scope is deliberately specific: this browser pass covered empty/text/image states, responsive width, connection display, and image preview. Microphone permission, live transcription, WAV upload, recovery after an actual server failure, and speech playback remain covered by source/tests or still require manual acceptance; pixel review does not certify those paths. The implementation continues to use system font stacks pending a screenshot-based font choice; no unlicensed font files were added.

Local verification: focused demo tests — 125 passed, 1 existing xfailed; full repository suite — 810 passed, 1 existing xfailed, 2 dependency warnings; repository-wide Ruff, inline JavaScript syntax, and `git diff --check` passed.
