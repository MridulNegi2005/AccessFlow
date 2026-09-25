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
| D — hands-free voice/images | NOT RUN | Existing file-upload route and offline timing tests only | WAV and PNG upload route remains; no synthetic recording is called live microphone evidence. | Automatic completion, processing while speech continues, End session, and ordered multi-image history remain to implement. D2/D3 controller hooks and D4 registry/source guards require Mridul; browser capture/display belongs to Atishay. |
| Gate 1 — 26 cases | FAIL | Checklist below | Error and some playback/capture cases pass. | D1/D2/D3/D4 and action cases remain. |
| Gate 2 — 12 actual-inference attempts | NOT RUN | No declared reasoning provider or listening Ollama service; no run ledger created | Installed ASR can decode a generated fixture through the browser adapter. | Predeclare four development cases and run 3 attempts each with actual ASR/reasoning/vision where applicable, Atishay. Never count fake reasoner or fixture response. |
| Gate 3 — four human microphone cases | NOT RUN | No new human audio captured | None claimed. | Run M01–M04 only after hands-free implementation and the user's capture agreement, Atishay. |
| Gate 4 — regression | PASS for current code; acceptance still partial | Python 3.11.15: `python -m pytest -q` **1372 passed, 5 skipped, 3 xfailed, 2 dependency warnings** (112.06 s); `ruff check .` and four Node checks passed. Explicit installed-model opt-in: **3 passed**, 135 deselected (20.49 s). | Current checked code is regression-clean; real ASR worker and browser adapter tests pass on generated WAV. | Skips include opt-in model tests when env is absent; two D1 xfails are open deliverable failures, not successes. Re-run after final implementation, Atishay. |

The two warnings are Starlette TestClient/httpx deprecations. The three retained
xfails are one earlier demo case and two strict D1 conformance cases. The opt-in
command was run separately with `ACCESSFLOW_TEST_WHISPER_MODEL_PATH` explicitly
set to the installed `Systran/faster-whisper-base.en` snapshot. That run used
actual Faster Whisper CPU INT8 on a **generated** WAV, but a **mock reasoner**;
it proved event/source identity and bounded native child teardown, not a real
answer, booking, human microphone result or Samsung score.

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
| S04 | NOT RUN | New D1 task-cancel-vs-pending-write conformance needs shared controller semantics and an owned browser reproducer. |
| S05 | PASS | `test_stop_words_have_distinct_scopes`: booking cancellation and washing-machine stop remain ordinary complete requests. This is classification, not a real cancellation effect. |
| S06 | FAIL | `test_vague_stop_holds_and_clarifies_without_a_final` strict xfail; partial cancel classifier is covered separately but shared hold is absent. |
| V01 | NOT RUN | No actual configured-agent Tuesday-to-Wednesday mock calendar effect. |
| V02 | NOT RUN | Offline pause replay exists; live automatic endpointing is absent. |
| V03 | NOT RUN | No integrated repetition/effect check. |
| V04 | NOT RUN | Source/revision tests exist, but no hands-free delayed-ASR correction conformance. |
| L01 | PASS | `microphone_pending_check.cjs`: pending/denied/late-grant capture cleanup. Not physical permission evidence. |
| L02 | PASS | `microphone_disconnect_check.cjs` and opt-in browser ASR disconnect test cover owned track/context and worker release in separate deterministic seams. |
| L03 | NOT RUN | No fresh-session reconnect regression through a configured process worker. |
| L04 | BLOCKED | Shared single-active-frame controller lacks the D4 image registry and source-bound selection, Mridul; Atishay still needs UI/per-image test. |
| V05 | NOT RUN | No processing-during-speech or automatic hands-free completion path. |
| L05 | NOT RUN | No End session control closing active voice/inference/tool wait without a final upload. |
| I01 | BLOCKED | D4 admission-ordinal registry absent in shared controller, Mridul; UI/test owned by Atishay. |
| I02 | BLOCKED | D4 per-field source selection/provenance and write guard absent, Mridul; browser display/test owned by Atishay. |
| I03 | BLOCKED | D4 ambiguous-reference/field clarification needs shared selected-source view, Mridul. |
| I04 | BLOCKED | D4 bounded registry/capacity/failure lifecycle absent, Mridul; UI error and fresh-session test owned by Atishay. |

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
