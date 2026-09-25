# Atishay delivery results — 25 September 2026

Status: **PARTIAL**. This is a development checkpoint, not voice/perception or
submission acceptance. Branch: `atishay/perception`; based on merged main
`5dd2a56ce7f063335fb2fcb0fbfe4f127640e9a6`. The latest owned changes
are in `demo/`, `tests/demo/`, `tests/perception/` and `docs/feedback/`; no Mridul-owned
implementation or configuration was edited.

## Slices and gates

| Item | Result | Evidence / command | Works | Missing / owner and next action |
| --- | --- | --- | --- | --- |
| A — error correlation | PASS, deterministic | `pytest tests/demo/test_app.py -q`; `node tests/demo/answer_correlation_check.cjs` | Admission receipt maps source/revision to server event before ASR or vision can fail; current errors show safe text and controls recover. | Physical browser/model failure smoke remains part of Gate 2/3, Atishay. |
| B — stop | FAIL, partial | `pytest tests/perception/test_confirmed_stop_semantics.py -q --runxfail` exposes two intended failures; Node output-stop regression passes. | Current authoritative output-stop cancels browser TTS; old session/cause ignored. Device/booking classification remains distinct. | Mridul must add output-only and hold/clarify controller decisions; Atishay will map the classifier and verify task/playback behavior. See proposal below. |
| C — configured agent | PASS for adapter seam; NOT RUN end-to-end real inference | `test_websocket_configured_mode_uses_factory_agent_and_declared_mock_tools`, `test_websocket_configured_factory_requires_explicit_backend`, opt-in browser ASR test | Explicit `ACCESSFLOW_DEMO_AGENT_MODE=configured` uses `build_configured_agent`, its reasoner/policy/perception, declared in-memory calendar mock manifest/executor, source-preserving observation projection, backend labels and worker cleanup. Setup fails visibly with no fake fallback. | No configured reasoning backend was available in this environment. Actual common-agent answer and mock calendar outcome require a configured installed provider, Atishay; shared action semantics remain Mridul's. |
| D — hands-free voice/images | PARTIAL | Deterministic live-voice harness, installed-ASR preview/final and reconnect tests, per-image perception regressions, `image_staging_check.cjs`, `answer_correlation_check.cjs` and `attachment_history_check.cjs` | The browser has opt-in provisional ASR and automatic final capture, with a longer bounded quiet window for action-like previews that have not yet expressed a correction. A fourth preview can capture later speech after the former three-preview cap; bounded, configurable quiet/preview/turn limits yield explicit no-final failure when exceeded. Separately receipted PNGs retain source-bound thumbnails and processing/failure status, including a same-session receipt arriving after a task timeout; late observation updates only its image row. An observed image is not mislabeled unavailable by a later task/tool error. The browser refuses a ninth image explicitly. | Physical-mic timing, general semantic endpoint quality, committed-effect closure, authoritative Image 1/2/3 ordinals, shared multi-image registry/field selection and actual vision remain open. The browser list is not agent reasoning evidence. D2/D3 controller hooks and D4 registry/source guards require Mridul. |
| Gate 1 — 26 cases | FAIL | Checklist below | Error, selected stop/playback/capture, deterministic corrected and repeated-quantity mock actions pass. | D1/D2/D3/D4 and actual live action cases remain. |
| Gate 2 — 12 actual-inference attempts | NOT RUN | `GATE2_PREDECLARED_2026-09-25.json` fixes four cases and 12 attempt IDs; `test_gate2_predeclaration.py` verifies the WAV/PNG bytes and SHA-256 hashes without loading a model. No `ACCESSFLOW_SAMSUNG_BACKEND`/vision model configuration was available in the last bounded check; loopback 11434 did not confirm a listener. | Generated correction/repetition and arithmetic WAVs plus three actual PNGs are locked as development inputs. The two-image labels were visually inspected in their pixels. | No actual reasoning/vision attempt or result is claimed. Atishay needs a configured provider and vision service; Mridul must land D4 source-bound multi-image selection before G2-04. The installed-ASR memory failure remains assigned to Mridul per user direction. |
| Gate 3 — four human microphone cases | NOT RUN | No new human audio captured | None claimed. | Run M01–M04 only after hands-free implementation and the user's capture agreement, Atishay. |
| Gate 4 — regression | PASS on current standard-suite rerun; opt-in ASR currently FAILS under low memory; acceptance still partial | Python 3.11.15: `.venv\Scripts\python.exe -m pytest -q` **1388 passed, 6 skipped, 3 xfailed, 2 dependency warnings** (123.56 s); `.venv\Scripts\ruff.exe check .` and seven Node checks passed. The fixture preflight passed without loading a model. The separately enabled installed-ASR tests failed on the earlier low-memory rerun and were not retried, per user direction. | Owned perception preserves separate image IDs/failures and rejects queue overflow; configured browser/controller checks cover repeated-quantity mock effects and disconnect during a gated mock write; browser receipt-bound image history, late-receipt isolation, downstream-error status and longer action-pause behavior pass deterministic checks. Previous installed Faster Whisper runs decoded generated WAV preview/final and reconnect cases. | An earlier full run failed one Mridul-owned offline CLI scenario with `missing_dependency`/timeout; isolated and later full runs passed, root cause unproven. The opt-in ASR failure was `mkl_malloc: failed to allocate memory`; Mridul will handle that resource issue. Two D1 xfails and the D4 conflicting-frame xfail remain deliverable failures; physical-mic timing and configured reasoning remain unverified. |

### Gate 2 predeclaration, not inference evidence

The immutable input list is [GATE2_PREDECLARED_2026-09-25.json](GATE2_PREDECLARED_2026-09-25.json).
`tests/perception/generate_gate2_fixtures.ps1` uses Windows System.Speech and
Microsoft Zira Desktop to generate the two WAVs. G2-01 includes a spoken
Tuesday repetition, a 1.4-second break, and the explicit Wednesday correction;
G2-02 asks 17 × 19 (= 323). These are synthetic recordings, not human speech.
G2-03 uses actual `device_panel.png` pixels (`ERR-42`). G2-04 uses two actual
PNG payloads already in `SCENARIO_MATRIX.json`: Image 1 visibly says `WED 5`
and Image 2 visibly says `DEVICE B`. Those reference labels are grading data,
not content to inject into the agent. Each attempt must use a fresh session,
the same declared configuration, and its fixed input bytes.

All of `G2-01-A/B/C`, `G2-02-A/B/C`, `G2-03-A/B/C` and `G2-04-A/B/C` are
**NOT RUN**. The preflight command
`.venv\Scripts\python.exe -m pytest tests/perception/test_gate2_predeclaration.py -q`
checks fixture identity only; it cannot pass Gate 2. When inference is
available, append an attempt record for *each* ID with the exact commit,
backend/configuration names, input SHA-256, session/source/event/revision IDs,
model output, mock effects, elapsed time, outcome and failure reason. Retain
failures and do not replace these fixtures after seeing results. In particular,
G2-04 must wait for Mridul's D4 registry; a newest-image-only answer cannot
count as completing it. The low-memory installed-ASR path is not retried here.

### Regression notes

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

The browser regression also reproduced an owned D4 display error: after a
final image observation, a later `backend_failure` with the same causal event
changed that PNG's status from `observed` to `failed`; a `tool_failed` could
similarly mark a merely received PNG as unreadable. The new check failed on
the old behavior, then passed after restricting image-failure status to a
pre-observation `backend_failure`. This is UI evidence-state correction, not
the missing shared image registry. A second failing timing check showed that
an action-like Tuesday preview finalized at 2.2 seconds of silence before a
2.5-second-pause correction. The owned capture now waits up to 4.2 seconds
for such prefixes (subject to the configured failure bound); the corrected
preview finishes hands-free. Long pauses and ASR lexical errors remain risks.

Another owned D4 browser reproducer showed that `finishRun()` cleared a PNG
waiting for its server receipt, and the later same-session receipt was
discarded because the old request was no longer active. The new check failed
before the repair. The browser now retains bounded pending PNGs across task
timeout; a matching receipt may populate history, but cannot update the new
request's event map, processing text or answer. A late vision observation
updates only that accepted row. An image that was never sent, including a
throwing send path, releases its pending capacity; End session/fresh session
still clears pending images. This is browser evidence retention, not proof
that the shared controller can reason across those images.

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
| V02 | PARTIAL | `live_voice_check.cjs` covers a simulated 2.5-second pause after an actionable "Schedule ... Tuesday at three" prefix, then a Wednesday correction, with only one final WAV after the correction. Action-like previews without correction wait up to a configurable 4.2-second quiet window by default; a completed correction can still finish after the normal 2.2 seconds. An explicit unfinished preview such as "Book Tuesday, actually" stays pending and eventually fails honestly if abandoned. This is a lexical timing guard, not semantic certainty: longer pauses, ASR misrecognition and physical-mic endpoint quality remain unverified. |
| V03 | PASS, deterministic only | `test_websocket_repeated_quantity_commits_one_unchanged_mock_effect`: one partial "two tickets" request followed by a final with the phrase repeated keeps the complete text in the reasoner view, commits exactly one mock write with quantity 2 and none from partial speech. Quantity interpretation is a scripted reasoner, not an actual model result. |
| V04 | PARTIAL | `live_voice_check.cjs` now holds an ASR preview callback across a pause and resumed speech: the old revision is rejected before a newer preview arrives, the newer correction is displayed, a still-later old callback is ignored, and the final WAV gets a higher revision. Server preview-only routing and final admission are covered separately. No physical audio timing, actual delayed model result, or controller-authority race has been exercised. |
| L01 | PASS | `microphone_pending_check.cjs`: pending/denied/late-grant capture cleanup. Not physical permission evidence. |
| L02 | PASS | `microphone_disconnect_check.cjs` and opt-in browser ASR disconnect test cover owned track/context and worker release in separate deterministic seams. |
| L03 | PASS, generated-audio/process-ASR regression only | `test_websocket_reconnect_with_installed_asr_starts_fresh_session`: first session receives a real Faster Whisper preview, its child closes on disconnect, and the next WebSocket has a new session ID, new process worker, only the new audio source in its reasoner view, and a correctly correlated final. Both children close. Browser old-session output filtering is separately covered by `answer_correlation_check.cjs`. This is not a physical-mic or actual-reasoner result. |
| L04 | BLOCKED at controller | `test_distinct_image_ids_keep_both_results_after_later_admission` proves a valid old-image result survives a newer ID in owned perception. `answer_correlation_check.cjs` retains a late same-session receipt after the old task times out and attaches its subsequent observation to that image without reviving an old answer. The shared single-active-frame controller still lacks D4 registry/source-bound selection, Mridul; authoritative ordinal/provenance display remains open. |
| V05 | PARTIAL | `live_voice_check.cjs` sends provisional previews before automatic final, now including later speech after three previews. Defaults are 2.2 s ordinary fluent quiet completion, 4.2 s action-like quiet completion (bounded below the failure timer), 5.5 s unfinished/no-decode failure, 1 s preview spacing, 12 previews and a 60 s turn cap; these are validated constructor options, not measured ideal values. A capped/oversize turn fails without final audio and cannot restart as a suffix-only turn until speech goes quiet. The earlier installed-ASR WebSocket test observed a generated-WAV preview before final admission and zero mock planner calls until final, but the later low-memory opt-in rerun failed. No physical-mic or real-reasoner action proof. |
| L05 | PARTIAL | `live_voice_check.cjs` discards unfinished speech and closes owned capture resources; `answer_correlation_check.cjs` invokes End session, clears queued input/closes the socket, and rejects a late final. `test_websocket_disconnect_cancels_inflight_preview_without_final` closes a pending preview, while `test_websocket_disconnect_during_mock_tool_wait_emits_no_late_final` closes during a gated mock write with no late effect/final. Physical End-session timing, in-flight native/remote work and already-committed-effect reporting remain unverified. |
| I01 | BLOCKED at controller | Owned perception and demo-wrapper tests retain separately identified images. `attachment_history_check.cjs` and `answer_correlation_check.cjs` retain browser thumbnails by accepted source/event, including late same-session receipt/observation, while rejecting duplicate/old-session receipts. The old receipt does not enter a newer request's event map or answer. No Image 1/2/3 label is assigned without a server ordinal; D4 registry and shuffled-completion conformance remain absent in Mridul's controller. |
| I02 | BLOCKED | D4 per-field source selection/provenance and write guard absent, Mridul; browser display/test owned by Atishay. |
| I03 | BLOCKED | D4 ambiguous-reference/field clarification needs shared selected-source view, Mridul. |
| I04 | BLOCKED at controller | Owned perception surfaces distinct-image failure and rejects a ninth pending image. The browser retains a failed accepted image as unavailable, refuses a ninth local session attachment before upload, and clears object URLs on a fresh session. Pending image identity now survives a task timeout until its matching receipt or session end; a send that throws releases its slot. A later tool/task error does not mark an observed image as failed. D4 bounded authoritative registry, stable ordinals and shared failure lifecycle remain absent in Mridul's controller. |

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
