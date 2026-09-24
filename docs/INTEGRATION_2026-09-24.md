# Branch integration — 24 September 2026

User-requested order, using fetched remote heads and a clean working tree:

1. Original main438b91b; Mridul c9136eb merged in a40cffd.
2. Atishay ed9d581 merged into that main in8c609d9.

Both input commits are ancestors of the combined main. No rebases, force-pushes
or dropped commits. The only content conflict was .ai-sync/handoff.md; both
histories were retained, and this integration checkpoint supersedes their status.
Backend source blobs match Mridul's checkpoint; frontend/perception/test blobs
match Atishay's. No application repair, fixture deletion or assertion weakening
was performed to make the integration pass. The workflow is unchanged/manual-only.

## Validation

- Ruff clean; all4 offline development scenarios passed (fake mode).
- The one inline browser JavaScript block passed node --check. The initial check
  wrapper hit Windows cp1252 encoding; sending UTF-8 bytes fixed the wrapper only.
- First full run:1 failed,1187 passed,2 skipped,1 expected failure in65.46s.
- Failure: tests/demo/test_app.py::test_websocket_vision_failure_recovers_to_multimodal_session.
  It received `Mock agent received audio input: Please inspect the attached screen`
  without the expected image context `screen shows the approval prompt`.
- Four isolated repetitions passed on unchanged source. These do not erase the
  failed full run or establish that the race is resolved.
- Final full run:1188 passed,2 skipped,1 expected failure in55.42s.
  The earlier race remains unresolved; both full reports are retained.

## Unresolved multimodal ordering follow-up

The test sends a recovered image, waits only for its upload receipt, then sends
audio. Upload acknowledgment is not proof of image observation completion.
`_receive_media_status` discards non-status events and `_receive_controller_outputs`
returns on the first final/error. Both perception and planning execute asynchronously.
This supports a timing/correlation hypothesis, but the captured failure alone does
not prove whether the exact race is in the controller, demo, or test. It is not
established as pre-existing or newly caused by this merge.

Atishay should provide a deterministic gated example recording source/event IDs,
image observation completion, audio observation and the final's causal ID. Assert
the combined answer associated with the intended request; do not drop the image
assertion, replace model evidence with canned text, or add sleeps as a fix.
Mridul owns any controller correction shown necessary by that example; Atishay
owns the demo/test correlation repair. Existing WebSocket correlation follow-up
remains relevant, but this is a distinct recorded failure. No B source was edited.

## Scope and next work

No live model, new browser visual QA, microphone, Docker or full official evaluation
was run for this merge. Earlier text-model/package evidence describes its original
source, not a rerun on this integrated tree. General development goal remains active.
MP3 bridge ownership still awaits the user's answer. Continue A-owned runtime/profile
configuration; coordinate B media/voice and retain the known race as an open issue.

[All merge test evidence](evidence/merge-main-2026-09-24/README.md)
