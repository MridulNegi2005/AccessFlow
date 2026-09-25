# Atishay delivery results — 25 September 2026

Status: **PARTIAL**. This is a development checkpoint, not voice/perception or
submission acceptance. Branch: `atishay/perception`; based on merged main
`5dd2a56ce7f063335fb2fcb0fbfe4f127640e9a6`. The latest owned changes
are in `demo/`, `tests/demo/`, and `tests/perception/`; no Mridul-owned
implementation or configuration was edited.

## Slices and gates

| Item | Result | Evidence / command | Works | Missing / owner and next action |
| --- | --- | --- | --- | --- |
| A — error correlation | PASS, deterministic | `pytest tests/demo/test_app.py -q`; `node tests/demo/answer_correlation_check.cjs` | Admission receipt maps source/revision to server event before ASR or vision can fail; current errors show safe text and controls recover. | Physical browser/model failure smoke remains part of Gate 2/3, Atishay. |
| B — stop | FAIL, partial | `pytest tests/perception/test_confirmed_stop_semantics.py -q --runxfail` exposes two intended failures; Node output-stop regression passes. | Current authoritative output-stop cancels browser TTS; old session/cause ignored. Device/booking classification remains distinct. | Mridul must add output-only and hold/clarify controller decisions; Atishay will map the classifier and verify task/playback behavior. See proposal below. |
| C — configured agent | PASS for adapter seam; NOT RUN end-to-end real inference | `test_websocket_configured_mode_uses_factory_agent_and_declared_mock_tools`, `test_websocket_configured_factory_requires_explicit_backend`, opt-in browser ASR test | Explicit `ACCESSFLOW_DEMO_AGENT_MODE=configured` uses `build_configured_agent`, its reasoner/policy/perception, declared in-memory calendar mock manifest/executor, source-preserving observation projection, backend labels and worker cleanup. Setup fails visibly with no fake fallback. | No configured reasoning backend was available in this environment. Actual common-agent answer and mock calendar outcome require a configured installed provider, Atishay; shared action semantics remain Mridul's. |
| D — hands-free voice/images | PARTIAL | Deterministic live-voice harness, installed-ASR preview/final and reconnect tests, per-image perception regressions, and `image_staging_check.cjs` | The browser has opt-in provisional ASR and automatic final capture. A resumed-speech revision invalidates an in-flight old preview. A preview ending in an explicit continuation cue now holds rather than becoming final on the quiet timer; it either accepts a later correction or fails without final audio after a bounded wait. A dropped PNG uploads the thumbnailed file. Distinct image IDs remain separate in owned perception. | Physical-mic timing, general semantic endpoint quality, committed-effect closure, ordered multi-image registry/field selection and actual vision remain open. The trailing-cue hold is a conservative lexical guard, not general semantic endpointing. D2/D3 controller hooks and D4 registry/source guards require Mridul; receipt-based browser attachment history remains Atishay-owned. |
| Gate 1 — 26 cases | FAIL | Checklist below | Error, selected stop/playback/capture, deterministic corrected and repeated-quantity mock actions pass. | D1/D2/D3/D4 and actual live action cases remain. |
| Gate 2 — 12 actual-inference attempts | NOT RUN | Fresh bounded environment check: no `ACCESSFLOW_SAMSUNG_BACKEND`/vision model configuration in this shell, and loopback 11434 did not confirm a listening service; no run ledger created. | Installed ASR can decode a generated fixture through the browser adapter. | Predeclare four development cases and run 3 attempts each with actual ASR/reasoning/vision where applicable, Atishay. A valid configured provider and applicable vision service are needed; never count fake reasoner or fixture response. |
| Gate 3 — four human microphone cases | NOT RUN | No new human audio captured | None claimed. | Run M01–M04 only after hands-free implementation and the user's capture agreement, Atishay. |
| Gate 4 — regression | PASS on final standard-suite rerun; opt-in ASR currently FAILS under low memory; acceptance still partial | Python 3.11.15: `python -m pytest -q` **1385 passed, 6 skipped, 3 xfailed, 2 dependency warnings** (127.63 s); `ruff check .`, six Node checks and live-voice script syntax passed. The separately enabled installed-ASR tests failed on rerun with native allocation failure. | Owned perception preserves separate image IDs/failures and rejects queue overflow; configured browser/controller checks cover repeated-quantity mock effects and disconnect during a gated mock write; previous installed Faster Whisper runs decoded generated WAV preview/final and reconnect cases; picker/drop staging matches the actual uploaded file. | The first full run in this slice failed one Mridul-owned offline CLI scenario with `missing_dependency`/timeout; the isolated test and next full run passed, root cause unproven. The current opt-in ASR failure is `mkl_malloc: failed to allocate memory` (about 1 GB physical RAM free at inspection); rerun when resources permit. Two D1 xfails and the D4 conflicting-frame xfail remain deliverable failures; physical-mic timing and configured reasoning remain unverified. |

The two warnings are Starlette TestClient/httpx deprecations. The six skips
were: `test_websocket_configured_adapter_with_installed_asr_and_mock_reasoner`,
`test_websocket_reconnect_with_installed_asr_starts_fresh_session` and both
tests in `test_live_worker_agent.py` because the opt-in model variable was not
set for the default suite; `test_corpus_boundary.py` and
`test_tool_metadata.py` because native symlinks were unavailable. The three
xfails were `test_conflicting_frames_require_resolution_before_write` (D4
controller gap) and the two strict D1 cases named in Slice B. The symlink
skips are environment/packaging checks, not proof of media acceptance; the
other four were run separately with the installed model. The opt-in
command was run separately with `ACCESSFLOW_TEST_WHISPER_MODEL_PATH` explicitly
set to the installed `Systran/faster-whisper-base.en` snapshot. That run used
actual Faster Whisper CPU INT8 on a **generated** WAV, but a **mock reasoner**;
it proved event/source identity and bounded native child teardown, not a real
answer, booking, human microphone result or Samsung score.

The new L05 browser check invokes the actual End-session handler, confirms it
clears queued transport input, closes the socket, stops playback/capture, and
rejects a late final event. The gated mock-write WebSocket test initially
failed because its scripted proposal omitted required tool dependencies; the
controller correctly rejected that write. With the manifest-matching
dependencies in the test, it reached the pending tool and passed. These are
test-harness findings, not evidence that an actual remote effect can be undone.

A read-only image UI review found that drag-and-drop previewed a `File` while
the upload path read only `#image.files[0]`. The owned browser now stores the
staged `File` and uses it for both preview and upload, checked with picker and
drop cases. The page still stages only one image at a time and does not assign
server-backed Image 1/2/3 ordinals or show per-image status. The current demo
receipt echoes source/event/revision but has no authoritative image ordinal or
receipt timestamp; the shared controller also lacks the requested D4 history.
Do not interpret the staging repair as I01-I04 acceptance. Three bounded kit
paths checked locally did not contain `WALKTHROUGH.md`; this does not establish
whether the organizer or teammate has a copy elsewhere.

After the delayed-preview change, the first full-suite rerun had **1 failure**
(`test_slow_image_provider_does_not_block_event_loop`): its provider did not
start within the test's one-second wait, and the task logged `MemoryError`.
The same test passed in isolation (0.99 s); no AccessFlow worker process was
left running in a read-only process check, and the next full run passed. This
is a transient/environmental hypothesis, not a proven root cause or a
silently discarded failure.

The first full run after the trailing-continuation guard had one different
failure: Mridul-owned
`tests/engine/test_corpus.py::test_cli_corpus_root_flows_to_replay_trace_evidence`
reported a 3/4 offline-fake scenario suite. The retained local report showed
`device_correction_during_write.json` timing out with `missing_dependency`,
`no_dispatchable_call` and `no_progress_exhausted`; it made zero mock effects.
That test passed in isolation and the entire suite passed on a no-parallel
rerun. We did not edit the engine, evaluation harness or failing test. This is
an intermittent shared-path finding with no established root cause, not a
passing first run or a proven effect of the browser change.

The opt-in installed-ASR run is also **not green in this slice**. The first
combined run returned 1 failed/3 passed for the generated-WAV browser and
perception cases; the configured browser preview lacked a backend because it
was an error preview. Its isolated retry failed again. A test-only diagnostic
identified `RuntimeError('perception worker backend failure')`; a subsequent
direct `LocalPerception` test exposed the underlying native error:
`mkl_malloc: failed to allocate memory`. At inspection the host reported
approximately 1,049 MB free physical memory and 1,541 MB free virtual memory.
A second isolated browser run briefly passed before failing again, and the
two direct model tests later failed. The temporary diagnostic hook was removed.
This is a current environment/resource failure, not proof that the new browser
guard causes model failure or proof of reliable real-ASR behavior. No other
applications or shared worker code were altered to manufacture a passing run.

Browser QA status: **IN PROGRESS**. The local mock page was opened in the Codex
in-app browser at 1280 CSS-pixel width. I inspected pixels in the initial and
post-answer states, confirmed the unavailable live-voice control stays disabled
after a text request, checked `document.body.scrollWidth` (1265 versus 1280
viewport width) and saw no browser error logs. The mock text request returned a
mock echo, not a substantive agent answer. The first local server run could not
upgrade `/ws` because the local `.venv` lacked WebSocket support; installing
`websockets==17.1` into that local environment allowed the smoke check without
changing the root dependency files. The temporary server was stopped. No
configured live-voice state, physical microphone, or responsive viewport was
visually verified, so this is not a full visual or device pass.

### Gate 1 stable case checklist

`PASS` below is deterministic evidence only. It does not upgrade the aggregate
gate or the real-inference/human-device gates.

| ID | Result | Test/evidence and remaining boundary |
| --- | --- | --- |
| E01 | PASS | `test_websocket_audio_backend_failure_keeps_multimodal_session_usable` plus `answer_correlation_check.cjs`: pre-observation ASR error maps to current receipt, browser error displays and task recovers. |
| E02 | PASS | `test_websocket_empty_asr_has_accepted_identity_and_recovers`: no observation/final for empty decode, then a valid transcript succeeds. |
| E03 | PASS | `test_websocket_configured_vision_failure_is_recoverable` plus browser correlation regression. |
| E04 | PASS | `answer_correlation_check.cjs`: old source, revision and session failures cannot end a new run. |
| E05 | PASS | `answer_correlation_check.cjs`: duplicate error after finish ignored; a new valid final renders. |
| E06 | PASS | `answer_correlation_check.cjs`: successful frame final waits for failed audio and cannot masquerade as full success. |
| S01 | PASS | `answer_correlation_check.cjs`: matched authoritative `stop_output` cancels playback. |
| S02 | PASS | `speech_lifecycle_check.cjs`: cancelled generation rejects late TTS callbacks. |
| S03 | FAIL | `test_stop_speaking_emits_output_stop_without_stopping_task` strict xfail; shared decision/controller missing. |
| S04 | PASS | `test_explicit_task_cancel_prevents_pending_mock_effect`: final spoken task cancel invalidates a gated mock write, emits cancel/output-stop, and leaves the session running. |
| S05 | PASS | `test_stop_words_have_distinct_scopes`: booking cancellation and washing-machine stop remain ordinary complete requests. This is classification, not a real cancellation effect. |
| S06 | FAIL | `test_vague_stop_holds_and_clarifies_without_a_final` strict xfail; partial cancel classifier is covered separately but shared hold is absent. |
| V01 | PASS, deterministic only | `test_websocket_configured_correction_commits_only_wednesday_mock_effect`: browser → actual controller, scripted planner double, partial Tuesday produces no effect; final correction creates one 2026-09-30 17:00 Asia/Kolkata mock effect and no Tuesday write. Real configured reasoning/mic remains Gate 2/3. |
| V02 | PARTIAL | `live_voice_check.cjs` covers a simulated pause and resumed speech. An explicit unfinished preview such as "Book Tuesday, actually" now stays pending past the normal quiet threshold; continuation is accepted and completes automatically, while abandonment produces a recoverable failed status and no final WAV. This does not protect every long pause before a correction cue or establish physical-mic endpoint quality. |
| V03 | PASS, deterministic only | `test_websocket_repeated_quantity_commits_one_unchanged_mock_effect`: one partial "two tickets" request followed by a final with the phrase repeated keeps the complete text in the reasoner view, commits exactly one mock write with quantity 2 and none from partial speech. Quantity interpretation is a scripted reasoner, not an actual model result. |
| V04 | PARTIAL | `live_voice_check.cjs` now holds an ASR preview callback across a pause and resumed speech: the old revision is rejected before a newer preview arrives, the newer correction is displayed, a still-later old callback is ignored, and the final WAV gets a higher revision. Server preview-only routing and final admission are covered separately. No physical audio timing, actual delayed model result, or controller-authority race has been exercised. |
| L01 | PASS | `microphone_pending_check.cjs`: pending/denied/late-grant capture cleanup. Not physical permission evidence. |
| L02 | PASS | `microphone_disconnect_check.cjs` and opt-in browser ASR disconnect test cover owned track/context and worker release in separate deterministic seams. |
| L03 | PASS, generated-audio/process-ASR regression only | `test_websocket_reconnect_with_installed_asr_starts_fresh_session`: first session receives a real Faster Whisper preview, its child closes on disconnect, and the next WebSocket has a new session ID, new process worker, only the new audio source in its reasoner view, and a correctly correlated final. Both children close. Browser old-session output filtering is separately covered by `answer_correlation_check.cjs`. This is not a physical-mic or actual-reasoner result. |
| L04 | BLOCKED at controller | `test_distinct_image_ids_keep_both_results_after_later_admission` proves a valid old-image result survives a newer ID in owned perception; shared single-active-frame controller still lacks D4 registry/source-bound selection, Mridul. Atishay still needs UI/source display. |
| V05 | PARTIAL | `live_voice_check.cjs` sends a bounded provisional preview before an automatic final and now refuses to finalize an explicit trailing correction cue on silence alone; the installed-ASR WebSocket test returns a Faster Whisper preview before final admission and sees zero mock planner calls until final. No physical-mic or real-reasoner action proof. |
| L05 | PARTIAL | `live_voice_check.cjs` discards unfinished speech and closes owned capture resources; `answer_correlation_check.cjs` invokes End session, clears queued input/closes the socket, and rejects a late final. `test_websocket_disconnect_cancels_inflight_preview_without_final` closes a pending preview, while `test_websocket_disconnect_during_mock_tool_wait_emits_no_late_final` closes during a gated mock write with no late effect/final. Physical End-session timing, in-flight native/remote work and already-committed-effect reporting remain unverified. |
| I01 | BLOCKED at controller | Owned perception and demo-wrapper tests now retain separately identified images; D4 server admission-ordinal registry and shuffled-completion behavior remain absent in shared controller, Mridul. UI/test owned by Atishay. |
| I02 | BLOCKED | D4 per-field source selection/provenance and write guard absent, Mridul; browser display/test owned by Atishay. |
| I03 | BLOCKED | D4 ambiguous-reference/field clarification needs shared selected-source view, Mridul. |
| I04 | BLOCKED at controller | Owned perception now surfaces distinct-image failure and rejects a ninth pending image without evicting eight accepted pending images. D4 bounded registry, stable ordinals and failure lifecycle remain absent in shared controller, Mridul; UI error/fresh-session test owned by Atishay. |

## Narrow joint interface requests

### D1 — stop/hold contract

Reproducer: run `python -m pytest tests/perception/test_confirmed_stop_semantics.py -q --runxfail`.
`Stop` currently reaches a final without `stop_output`; `Stop speaking` produces no
output-stop. Mridul: add backward-compatible `TurnDecision` cases for
`output_only_stop` and `hold_and_clarify` (existing kinds/defaults unchanged),
then have the controller emit a causal `acknowledge(stop_output=true)` while
preserving task authority for output-only stop; vague stop must hold new tool
dispatch and issue `clarify` without cancelling the voice session. Explicit
`Cancel this task` must invalidate pending work but keep the session open.
Atishay: map final classified phrases to those kinds, never authorize from
partial speech, and test current-session playback and late callbacks. The
already-wired browser accepts an authoritative `stop_output` event only for a
current session and accepted event ID. No official wire change is requested.

### D2/D3 — live timebase and closure

The existing `SpeechStatusEvent` admits `pending/failed` but cannot express
provisional WAV revision, acoustic clock mapping, or an explicit browser
endpoint decision that is distinct from write authority. Mridul should define
an additive controller-facing pending/finality mapping and make `session_end`
cancel owned inference/tools and ignore late work. Keep legacy complete WAV
and Samsung `end_of_turn` semantics unchanged. Atishay can implement capture,
activity windows, coalesced ASR snapshots, automatic completion and immediate
browser transport teardown against that seam, then write V02/V05/L05 tests.
An unfinished WAV must never be flushed on End session.

### D4 — multi-image registry

Current `Agent` has one pending/active frame token, so admitting Image 2 can
invalidate Image 1 before both can be addressed. Mridul should add a bounded
session registry keyed by accepted frame ID with server admission ordinal,
receipt timestamp, optional untrusted capture timestamp, revision/status,
per-image evidence and explicit source-bound field selection in the reasoner
view/write dependencies. Existing single-image clients retain their default.
Atishay can display ordinal/receipt/error states and prove shuffled results,
but cannot make a safe Image 1+Image 2 write by frontend text alone. Preserve
the official wire and reject capacity excess without renumbering.

## Reproducible launch boundary

`ACCESSFLOW_DEMO_AGENT_MODE=mock` is the default and explicitly remains a fake
demo. Set it to `configured` to use the shared builder; then set an explicit
`ACCESSFLOW_SAMSUNG_BACKEND` and that provider's existing model/credential
settings. For native audio use `ACCESSFLOW_SAMSUNG_PERCEPTION=process`, an
installed `ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH`, and a recognizable
`ACCESSFLOW_SAMSUNG_WARMUP_AUDIO`. For images also configure
`ACCESSFLOW_SAMSUNG_VISION_PROVIDER=ollama`, its model/loopback URL and an
installed PNG warm-up image. Optional `ACCESSFLOW_DEMO_ASSETS_ROOT` resolves
relative installed paths; the default is the repository root. Launch with
`python -m uvicorn demo.app:app --host 127.0.0.1 --port 8000` using the locked
Python 3.11 environment. The status should show the configured reasoner name,
configured perception backends and `mock` tool environment. Browser disconnect
must close the session-owned native worker; the opt-in test verified this in
five seconds with its client still running. These real-mode launch settings
were **not** run here: no backend env key was set and loopback port 11434 did
not accept a connection. No credential value was read or recorded.

The organizer kit files (`WALKTHROUGH.md`, `PROTOCOL.md`, `SCORING.md`,
`SUBMISSION.md`) were not in this checkout or the bounded `Samsung Stuff`/
`Samsung GenAI` locations checked on this machine. This is a local availability
finding, not a claim about what the organizer supplied. Official 300/120-second
setup/scenario limits remain unchanged and official scoring was not run.
