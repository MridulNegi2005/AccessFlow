# Integration note for Atishay, 16 September 2026

Branch `mridul/engine` and branch `atishay/perception` are merged into `main`. Neither branch
was broken on its own. Your branch passed 255 tests and 4 expected failures. My branch passed
411 tests. The merged tree failed 27 tests, and every failure was an image path.

This note states the cause, the change I made, and the 21 tests that need your decision.

## Cause

You added this to `src/accessflow/turn_policy/heuristic.py`:

```python
if observation.modality == "image":
    return TurnDecision(kind="continue", uncertainty=1.0)
```

Before that, an image observation with `final=True` fell through to `kind="complete"`.

The controller gated image readiness on that verdict:

```python
self.latest_complete = (self.speech_ready or self.active_speech is None) and (
    obs.final and decision.kind == "complete")
```

With the new branch, every image returns `continue`, so `latest_complete` can never become
true for a frame. The frame arrives, perception produces a correct observation, the engine
stores it and sets `active_frame`, and then nothing plans on it. Every image path stalls
until the scenario deadline.

## Your change is correct. Keep it.

A photo caption must not drive speech turn cues. A caption that reads "okay" must not count
as a backchannel, and a caption containing "actually" must not count as a correction. That
was a real defect and you fixed it.

The fault was mine: the controller asked a speech turn policy a question about a frame. A
turn policy answers one thing, whether the speaker finished the utterance. A frame is not an
utterance, so it has no turn to end.

## What I changed, in `src/accessflow/engine.py` only

1. Image readiness now comes from the observation, not from the turn policy:
   `self.latest_complete = (self.speech_ready or self.active_speech is None) and obs.final`.
2. The spoken acknowledgement "I'll check that." is no longer emitted for a frame. It answers
   a speaker who waits to hear that the turn landed. A frame has no speaker waiting.

I changed no Workstream B file. All 5 engine failures cleared. Engine, perception and
contract tests pass together: 499 tests.

## Safety check, verified directly

An image alone still cannot authorize a write. I ran the case from
`tests/demo/test_app.py::test_image_evidence_never_authorizes_a_write_without_spoken_request`
against the merged engine:

```
write_intent_retained = False
speech_ready          = False
executor.calls        = []
executor.effects      = {}
```

The write gate holds. Only `state.correction_pending` changed, from True to False, because a
complete image is now resolved evidence. That is the assertion your test reads, not the
safety property. The safety property is intact.

## The 21 tests that need you

These fail because they record the stalled behaviour as expected. The behaviour they expect
is the behaviour of a controller that ignores images.

- `tests/demo/test_app.py::test_websocket_local_perception_timeout_is_recoverable`
- `tests/demo/test_app.py::test_websocket_png_upload_reaches_mock_controller`
- `tests/demo/test_app.py::test_websocket_concurrent_sessions_do_not_share_multimodal_context`
- `tests/demo/test_app.py::test_websocket_image_before_audio_context_is_visible`
- `tests/demo/test_app.py::test_websocket_environment_vision_provider_reaches_multimodal_context`
- `tests/demo/test_app.py::test_websocket_real_local_perception_and_vision_share_context`
- `tests/demo/test_app.py::test_websocket_audio_backend_failure_keeps_multimodal_session_usable`
- `tests/demo/test_app.py::test_websocket_audio_revision_recovers_after_failure_with_image`
- `tests/demo/test_app.py::test_websocket_configured_vision_failure_is_recoverable`
- `tests/demo/test_app.py::test_websocket_vision_failure_recovers_to_multimodal_session`
- `tests/demo/test_app.py::test_websocket_malformed_vision_json_is_recoverable[[]]`
- `tests/demo/test_app.py::test_websocket_malformed_vision_json_is_recoverable[{not-json]`
- `tests/demo/test_app.py::test_websocket_vision_quota_exhaustion_is_recoverable`
- `tests/demo/test_app.py::test_websocket_http_vision_quota_exhaustion_is_recoverable`
- `tests/demo/test_app.py::test_websocket_vision_timeout_is_recoverable`
- `tests/demo/test_app.py::test_inflight_old_frame_cannot_enter_multimodal_context`
- `tests/demo/test_app.py::test_image_evidence_never_authorizes_a_write_without_spoken_request`
- `tests/demo/test_app.py::test_new_frame_replaces_previous_frame_in_reasoner_context`
- `tests/demo/test_app.py::test_image_only_informational_response_needs_additive_controller_support`
- `tests/demo/test_reasoner.py::test_websocket_environment_reasoner_receives_multimodal_context`
- `tests/demo/test_reasoner.py::test_websocket_reasoner_failure_is_recoverable`

Three shapes:

1. **Strict dictionary equality on an output event.** The event now carries
   `caused_by_event_id`. Compare the fields you care about, or add the key.
2. **An extra `final` for the image.** A frame now produces its own informational answer, so
   `next(item for item in received if item["kind"] == "final")` returns the image's answer
   and not the later transcript's. Select the final you mean.
3. **`correction_pending` after a frame.** It is False now, because a complete image is
   resolved evidence. Assert the absence of calls and effects instead; that is the property
   those tests are named for.

## One decision is yours and mine together

Should a lone image produce an informational answer with no spoken request?

- The engine contract says yes. `tests/engine/test_component_integration.py::
  test_image_only_input_can_produce_informational_response` predates both our branches.
- Your demo tests say no, and `docs/CONTRACT_PROPOSALS.md` carries your two related
  proposals, "Additive image-only informational response" and "Conflicting visual evidence
  requires resolution".

I kept the engine contract, because reverting it means images never complete at all. If you
want a lone image to stay silent until the person speaks, that is a contract change, not a
test fix, and I will make it on the engine side. Tell me which you want.

Do not change `heuristic.py` back.
