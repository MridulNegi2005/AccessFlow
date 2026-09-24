# Stitch handoff record — 24 September 2026

Project: [AccessFlow Desktop Shell](https://stitch.withgoogle.com/projects/12923345623703202409?pli=1)

## What is in this folder

No native Stitch PNG, code or asset export has been saved here yet. Do not mistake the
browser screenshots in `artifacts/` for Stitch exports: they are local captures of the
implemented FastAPI demo, made for visual QA.

The project was used for prompts 1–5 in `../STITCH_PROMPTS.md`. Its visible frame set
includes the two anchors (`01-photo-answer`, `02-meeting-correction`), voice and meeting
states (`03-ready` through `10-unknown-outcome`), information/image/recovery states
(`11-information`, `12-comparison`, `13-image-results`, `13b-images-unavailable`,
`14-replaced-image`, `15-mic-denied`, `16-disconnected`, `17-long-answer`), mobile and
compact variants, a reduced-motion example, and a linked presentation prototype. Those
screens are mockups only. Some generated frames contain invented telemetry, unsupported
claims, or sample interaction text; they were not copied into the live frontend.

## Fidelity and limitations

- The approved source PNGs remain in [`../references/`](../references/). The browser file
  chooser event timed out, and no attached files appeared in Stitch.
- A summarized project canvas named DESIGN.md exists; the complete local
  [`DESIGN.md`](../../../DESIGN.md) was not imported byte-for-byte.
- The selected anchors are 1280 × 1033 (`01-photo-answer`) and 1280 × 1025
  (`02-meeting-correction`), rather than the requested 1536 × 1024. The implementation
  follows the written responsive breakpoints and was checked at real viewport sizes separately.
- One generated dog image differs from the approved photo reference. It is not a product
  asset and must not be presented as an uploaded user photo or copied into the demo.
- Prototype clicks, audio status, connection badges, tool telemetry and calendar outcomes
  are simulated. They do not prove microphone streaming, ASR, barge-in, calendar access,
  cancellation or successful external actions.

### Latest live inspection (24 September 2026)

The Stitch project is accessible in the Codex in-app browser. Selecting `01-photo-answer`
visibly showed a dog photo and answer, with a frame-size badge of **1280 × 1033**.
Selecting `02-meeting-correction` visibly showed a single Wednesday 5 PM draft, sized
**1280 × 1025**. Both differ from the requested 1536 × 1024. Visible content and frame
names alone do not establish fidelity to the approved references; these frames are not
being treated as accepted references.

Stitch's ZIP Export was clicked twice, but no archive was visible in the checked
`C:\Users\adish\Downloads` location or this folder. Therefore there is still **no verified
native export**; the clicks are not being reported as successful downloads. Review the
two anchors against the approved sources at readable scale, correct any mismatches, and
save only reviewed exports.

The selected meeting frame's context-menu **Download** was also tried with a browser
download-event watcher; no event fired. **Copy as → Copy as PNG** displayed “Copied as
PNG,” but this session's browser clipboard API returned no image bytes. If using that
option manually, paste into an image editor and save the PNG before counting it as an
export. No file has been saved from either action here.

## Manual review and export still needed

The project is accessible in the Codex in-app browser. To complete the source review and
native export without claiming an export that is not present:

1. Open the project link above and review `01-photo-answer` and `02-meeting-correction`
   at readable scale against the approved references. Check the observed dimensions and
   correct any mismatches rather than accepting either frame by name or visible content alone.
2. Attach `DESIGN.md` and the two PNGs from `docs/design/references/` using Stitch's
   **Choose Files** action, then correct the anchors against those exact source assets.
3. Use Stitch’s `Shift+D` export shortcut or right-click each accepted frame and choose
   **Copy as → Copy as PNG**, then paste into an image editor and save it. Save the
   accepted anchors and reviewed variants here as
   `01-photo-answer.png`, `02-meeting-correction.png`, etc.
4. If Stitch offers a project ZIP export, confirm the archive actually downloaded before
   recording it here. Inspect an archive in an isolated folder before moving assets into
   `demo/`.
5. If Stitch offers code/assets, export them here too. Inspect them before reuse; do not
   replace `demo/index.html` or its WebSocket adapter with generated code.
6. Record the actual export date, frame dimensions, filenames and simulated interactions
   in this README. Do not include credentials, recordings or private media.

The text-first implementation proceeded from the approved source references and
`DESIGN.md` despite the missing native export. That does not convert local QA captures into
Stitch deliverables.

The demo's `/?preview=photo` and `/?preview=meeting` are separately implemented local
sample states. The photo uses a newly generated, clearly labeled illustrative image;
neither preview is a saved Stitch export or evidence of live perception/calendar behavior.
