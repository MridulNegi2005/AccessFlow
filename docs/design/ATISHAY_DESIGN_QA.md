# Atishay frontend design QA — 24 September 2026

**Final result: blocked.** This is a partial visual and interaction check, not
acceptance of pixel parity or a native Stitch export. The owner-approved visual
sources are `references/approved-photo-conversation.png` and
`references/approved-meeting-correction.png`, each 1536×1024 pixels. The local
implementation is the FastAPI demo at `/`, `/?preview=photo` and
`/?preview=meeting`. No same-state 1536×1024 implementation capture was saved
as a local file in this pass, so source and implementation could not be placed
in one normalized comparison artifact. Browser screenshots were inspected in
the task but are not durable export evidence; implementation screenshot path,
pixel dimensions and density normalization remain unavailable.

## Findings

- **P1 — Native design acceptance remains open.** The selected Stitch anchors
  report 1280×1033 (`01-photo-answer`) and 1280×1025
  (`02-meeting-correction`), not the 1536×1024 reference frame. The approved
  PNGs were not attached and the full `DESIGN.md` was not imported byte-for-byte.
  Clicking the selected frame's Download produced no file verifiable in the
  checked download/design folders. Attach the exact sources, review at readable
  scale, correct the anchors and save verified PNG exports.
- **P1 — Live action-card parity requires shared evidence.** The Wednesday 5 PM
  card is a labeled deterministic preview, not a projection of authoritative
  meeting state. The normal demo keeps unsupported action details as text. A
  stable action identity and matching write outcome must be agreed with Mridul
  before a live in-place correction or scheduled state is shown.
- **P2 — Preview photo differs from the approved sample.** The local preview
  uses an original illustrative dog asset, not the exact approved image. It is
  labeled as sample imagery and must not be mistaken for uploaded evidence.
  Revisit crop, subject and image quality after accepted exports exist.

## Checked surfaces and limits

- **Typography:** the local answer uses editorial serif and sans controls;
  the preferred Instrument Serif/Geist names have fallbacks. Exact glyph shapes,
  weights, line breaks and antialiasing were not normalized against source.
- **Spacing/layout:** inspected the normal live answer at the browser default
  desktop size and at 390×844 CSS px. At 390px, the console and answer stack
  vertically; the document width was 375px inside a 390px viewport, with no
  horizontal overflow. This is not a same-state reference comparison.
- **Colors/tokens:** the inspected shell uses the intended charcoal, warm ivory,
  forest and lime family. Exact source-pixel sampling/contrast audit is open.
- **Imagery/icons:** the live page has no user-uploaded image in this check;
  the local photo preview and approved source imagery were not compared in a
  normalized composite. Icon and logo fidelity remain open.
- **Copy/content:** a local `demo/mock` text request visibly returned its
  mock-agent response and mock provenance. The source photo/meeting copy is
  illustrative, not evidence of actual perception or scheduling.
- **Interaction evidence:** the local WebSocket text request completed; the
  browser-side causal guard rejects stale/unattributed final answers in the
  owned regression. Physical microphone, screen reader, live model, real
  calendar action and all reduced-motion combinations remain unverified.

The image-to-code QA procedure requires a saved same-viewport, same-state
source/implementation comparison before passing. That gate remains blocked.
The report stays in Atishay-owned design documentation rather than adding a
root-level file outside his workstream.
