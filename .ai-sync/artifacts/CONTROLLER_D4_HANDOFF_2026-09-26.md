# Controller D4 handoff — 26 September 2026

## A-owned implementation

The controller now keeps up to eight accepted images per session with immutable
admission ordinals, server receipt order/time, optional capture time and provenance,
processing status, and observations bound to their original frame/event/revision.
A later image does not erase or relabel an earlier one. A late valid result can fill
its own earlier record without settling the current frame or reopening a finished
request. Duplicate IDs and a ninth attachment are rejected without reindexing.

The reasoner receives a path-free `image_history`. `PlanProposal.image_bindings`
selects the image source of each image-derived slot; the controller checks the
accepted frame, event, revision and literal caption quote before state mutation.
The selected source survives in `Snapshot.slot_image_sources`, and a changed source
invalidates dependent work even if the value stays the same. An unqualified
"the/this/attached image" selection defaults to the newest accepted image;
"old image" with more than one earlier candidate asks for clarification. A
write may use an image-derived field only while its verified source remains valid.
Image evidence alone never supplies user authorization for a write. Existing
single-image planners retain an automatic source binding only while exactly one
image is observed and it is the active image.

Image receipt acknowledgments now contain the nonempty text required by the
Samsung protocol adapter. The hosted repository default context budget is
32,768 characters, matching the packaged profile; the local Ollama budget stays
14,000. This fixes a live public development run that otherwise failed before
making its second provider request. No model training or B-owned source changed.

## Verified here

- Focused controller/contract/integration set: 109 passed before final default
  context adjustment; subsequent changed-area run: 59 passed.
- Broad Python 3.11 regression: 1,429 passed, 6 skipped, 7 B-owned cases
  deselected, 2 dependency warnings in 106.74 seconds. The B stop tests pass
  separately with `--runxfail`: 3 passed. Ruff and `git diff --check` pass.
- A native development package assembled from clean commit `7cf33d9` contains
  98 files. Its hashes, 37 pinned dependencies and organizer import validated
  in the existing isolated Windows Python 3.11 environment. An installed local
  Ollama 0.34.0 / Gemma 3 4B service, CPU INT8 Faster Whisper and hosted Qwen
  warmed successfully from that exact package: service startup took 9.22 s,
  setup took 56.39 s, and the owned service was stopped afterward.
- The first package verification attempt timed out before service readiness;
  the second reached service readiness but setup raised `RuntimeError` after
  6.11 s. These are retained as failed attempts, not discarded. The third
  candidate and final clean-commit package attempts passed. This is variable
  setup behaviour on this Windows host, not proof of reliable target-platform
  startup. Sanitized reports are in
  `docs/evidence/d4-controller-2026-09-26/`.
- A normal-speed public `pub_03_text_chained_booking` run used the organizer
  harness with actual hosted reasoning. With the old repository 14K default,
  it scored 38.5: no task calls, and later requests failed before network I/O
  with `ValueError` from the context bound. A 65K diagnostic run scored 56.9:
  the search completed, but a provider HTTP 429 prevented the booking and
  final. The hosted default is now 32K, matching the package. These runs
  establish a functioning evaluator path and expose remaining accuracy/quota
  limits; they do not establish a passing task-completion score.

All external writes in these checks were mock harness effects. The package is
a local ignored development candidate, not a submission or release.

## Atishay-owned integration needed next

After this branch is incorporated into the shared base, consume
`SessionView.image_history`, `Snapshot.slot_image_sources`, and the
`acknowledge.image_received` ordinal receipt. Update only B-owned demo and
perception tests. Five B demo tests currently assert single-image replacement
or silence on an older image failure; D4 instead retains both images and
reports a failure under its own ID. In particular:

1. `test_websocket_combined_media_context_is_visible` needs deliberate response
   focus when audio and image history coexist; it currently receives an audio-led
   mock final after a frame.
2. `test_websocket_stale_vision_failure_does_not_break_recovered_multimodal_session`
   must distinguish an honest older-image error from a current-session failure.
3. `test_websocket_new_frame_replaces_previous_frame` and
   `test_new_frame_replaces_previous_frame_in_reasoner_context` encode the
   superseded replacement rule.
4. `test_conflicting_frames_require_resolution_before_write` is now a strict
   XPASS; remove the obsolete marker only after checking its assertion still
   proves the intended write guard. The two strict stop xfail markers are also
   obsolete and their tests pass unmasked.

Then run the twelve predeclared real-reasoning/vision attempts and four physical
microphone checks using the combined runtime. Record successful and failed
attempts separately. A caption quote proves source identity, not that a model
correctly interpreted a date, address or other field. The real-image cases
must check that semantic grounding and the spoken cross-image selection.

## Gates that still require an environment or joint work

Docker is absent on this machine. The generated Docker recipe and Linux target
have not been executed. The local installed-vision setup varied across three
attempts, and the normal-speed public run still lacks a confirmed write/final.
Run repeated organizer scenarios, including audio and visual cases, after B's
runtime integration and on the declared submission platform. Do not report
the deterministic tests or setup warm-up as official multimodal completion.

This is an A-side code handoff, not a claim that the combined project is ready
to submit.
