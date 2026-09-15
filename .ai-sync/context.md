# AccessFlow shared agent log

Shared project context for Claude Code, Codex and Antigravity. Personal knowledge is
not copied into this repository. Canonical plan and interface copies are in artifacts/.

## [2026-09-13 14:30] — Codex
**Task:** Implement AccessFlow; prioritize independent teammate bootstrap.
**Changes:** Added contracts/interfaces, deterministic fakes, clock, initial unverified engine,
Python configuration, workstream ownership, handoff instructions and plan copy. Initialized sync.
**Status:** in-progress
**Notes:** Atishay may begin B against contracts and fakes. Engine is not yet safety-tested.
Official kit, live model benchmarks and final submission remain outstanding. No hosted remote.

---

## [2026-09-13 14:32] — Codex
**Task:** Prepare GitHub collaboration at user request.
**Changes:** Added initial engine safety tests; normal clone/push instructions replace bundle workflow.
**Status:** in-progress
**Notes:** 16 offline tests passed; Ruff passed. Authenticated GitHub account verified; repository visibility selection pending. No live inference claim.

---

## [2026-09-13 15:00] — Codex
**Task:** Prepare the public-repository handoff for Atishay.
**Changes:** Verified the public clone and `atishay/perception` checkout; corrected
`ATISHAY_START_HERE.md` to explain direct collaborator pushes versus fork-based work.
**Status:** handoff-ready; no Workstream B implementation started.
**Notes:** `uv run --python 3.12 --extra dev pytest tests/test_contract.py` passed 4 tests.
The default 3.11 `uv` target is locally broken; no live ASR, vision or hosted-backend
evidence exists.

## [2026-09-13 15:30] - Codex
**Task:** Implement the first turn-policy checkpoint for Atishay's Workstream B.
**Changes:** Added the synchronous `HeuristicTurnPolicy` and focused tests for partial speech,
corrections, repetitions, backchannels and stale revisions; updated the README and handoff.
**Status:** checkpoint validated; no vision or UI implementation yet.
**Notes:** `uv run --python 3.12 --extra dev pytest -q` passed 29 tests and Ruff passed for owned
paths. The current contract still lacks timer/silence events, so no acoustic pause claim is made.

## [2026-09-13 16:00] - Codex
**Task:** Implement the replaceable PNG vision checkpoint for Atishay's Workstream B.
**Changes:** Added PNG validation and injected vision-provider support to `LocalPerception`,
with frame identity/timestamp tests and updated checkpoint documentation.
**Status:** checkpoint validated; minimal demo remains.
**Notes:** Focused perception tests passed 15; full suite verification follows. No live vision
backend or quality evidence is claimed.
## [2026-09-13 16:30] - Codex
**Task:** Implement the minimal fake-agent browser demo for Atishay's Workstream B.
**Changes:** Added FastAPI WebSocket routing, typed browser-event translation, labeled mock
perception/reasoning, plain HTML controls and an end-to-end smoke test.
**Status:** checkpoint validated; real WAV provenance and timing/VAD remain.
**Notes:** `uv run --python 3.12 --extra dev pytest -q` passed 37 tests. Ruff passed for owned
paths. FastAPI test-client dependency deprecation warnings remain; no live multimodal evidence.
## [2026-09-13 17:00] - Codex
**Task:** Add deterministic audio fixture provenance for Atishay's Workstream B.
**Changes:** Generated a synthetic 16 kHz PCM tone with standard libraries, recorded its hash and
provenance, and added a checked-in fixture validation test.
**Status:** checkpoint validated; local ASR model and timing/VAD remain.
**Notes:** Focused perception tests passed 16; the fixture is not speech and supplies no ASR quality
evidence. No participant recording was used.
## [2026-09-13 17:30] - Codex
**Task:** Add PCM loading and an energy-activity timing baseline for Atishay's Workstream B.
**Changes:** Added isolated mono/stereo loading, rate conversion, RMS activity frames and tests
against the checked-in fixture; documented the `audioop` deprecation limitation.
**Status:** checkpoint validated; local ASR and maintained VAD backend remain.
**Notes:** `uv run --python 3.12 --extra dev pytest -q` passed 43 tests. No live ASR or VAD
quality evidence is claimed.
## [2026-09-13 18:00] - Codex
**Task:** Harden the local Faster Whisper ASR seam for Atishay's Workstream B.
**Changes:** Added local model-path validation, injectable factory configuration and focused
CPU/int8 segment aggregation tests without downloading weights.
**Status:** checkpoint validated; live model measurement remains.
**Notes:** Perception tests passed 23; no live ASR quality or latency evidence is claimed.
## [2026-09-13 18:30] - Codex
**Task:** Replace deprecated audioop calls in Atishay's owned PCM path.
**Changes:** Added standard-library PCM decoding, stereo downmixing, linear resampling and RMS
helpers with coverage for 1-, 2-, 3- and 4-byte samples.
**Status:** checkpoint validated; live ASR measurement and acoustic VAD remain.
**Notes:** uv run --python 3.12 --extra dev pytest tests/perception/test_audio.py -q passed 9
tests. Ruff passed for owned paths. No dependency or contract changes; no live backend claim.

## [2026-09-13 19:00] - Codex
**Task:** Measure the installed local Faster Whisper backend on declared hardware.
**Changes:** Installed the optional runtime in the ignored environment, downloaded the base.en
model into ignored models storage and recorded a real CPU INT8 fixture run.
**Status:** checkpoint validated; speech-quality, acoustic VAD and live vision evidence remain.
**Notes:** Intel Core Ultra 5 125H, Python 3.12.10, faster-whisper 1.2.1. Model load 0.464 s;
0.500 s tone inference 0.677 s; realtime factor 1.354; transcript empty as expected. No tracked
dependency or contract changes.

## [2026-09-13 19:30] - Codex
**Task:** Add a non-participant speech fixture and measure local ASR through LocalPerception.
**Changes:** Added a Windows speech-synthesized WAV with provenance and recorded an adapter-level
Faster Whisper base.en CPU INT8 run.
**Status:** checkpoint validated; held-out speech accuracy, acoustic VAD and live vision evidence remain.
**Notes:** 5.304 s fixture, 5.874 s adapter elapsed, realtime factor 1.108. Transcript matched the
known script apart from the final number wording. No tracked dependency or contract changes.
## [2026-09-13 20:00] - Codex
**Task:** Add a timing-only activity summary and an additive proposal for future timing metadata.
**Changes:** Added activity windows, silence durations and pause signals over existing energy frames;
kept the v0.1 engine contract unchanged and recorded the proposal for review.
**Status:** checkpoint validated; held-out speech cases, acoustic VAD and live vision evidence remain.
**Notes:** Focused audio/timing suite expected 12 tests; no pause is treated as semantic completion.
## [2026-09-13 20:30] - Codex
**Task:** Add and evaluate an optional WebRTC activity backend.
**Changes:** Added lazy WebRTC VAD loading, format checks, deterministic injection tests and
comparative measurements against the energy baseline.
**Status:** checkpoint validated; held-out VAD quality, acoustic pause evaluation and live vision evidence remain.
**Notes:** webrtcvad-wheels 2.0.14, aggressiveness 2, 20 ms frames. Tone 25/25 active; generated
speech 189/265 active with 0.640 s trailing silence. No tracked dependency or contract change.

## [2026-09-13 21:00] - Codex
**Task:** Add and measure a generated pause-and-correction speech fixture.
**Changes:** Added provenance-tracked audio with a 1.5 second break, then measured WebRTC VAD
and Faster Whisper through LocalPerception.
**Status:** checkpoint validated; held-out endpoint quality, acoustic VAD evaluation and live vision evidence remain.
**Notes:** 6.024 s fixture, WebRTC 139/301 active frames in three windows with 0.640 s trailing
silence; ASR elapsed 1.334 s, realtime factor 0.221. No participant audio used.

## [2026-09-13 21:30] - Codex
**Task:** Add session-scoped WAV/PNG upload to the browser demo.
**Changes:** Added base64 transport, 8 MiB limit, WAV/PNG validation, temporary file cleanup and
browser encoding; kept the demo perception backend explicitly mock.
**Status:** checkpoint validated; microphone capture, held-out endpoint quality, live vision and feedback remain.
**Notes:** Demo suite 9 passed; no shared contract or dependency change.

## [2026-09-13 22:00] - Codex
**Task:** Replace the mock microphone control with browser-side WAV capture.
**Changes:** Added getUserMedia capture, 16-bit PCM WAV encoding, upload through the existing
session route and static UI checks; kept downstream perception demo/mock.
**Status:** checkpoint validated at code level; manual browser device smoke, held-out endpoint quality,
feedback and live vision remain.
**Notes:** Demo suite 9 passed; no shared contract or dependency change.

## [2026-09-13 22:30] - Codex
**Task:** Add internal and trailing endpoint candidates over activity windows.
**Changes:** Added timestamped PauseCandidate values with short-gap and all-silence guards.
**Status:** checkpoint validated; held-out endpoint quality, manual browser smoke, feedback and live vision remain.
**Notes:** WebRTC on pause-correction produced a 2.260 s internal and 0.640 s trailing candidate.
No shared contract or dependency change.

## 2026-09-13 - Codex Atishay feedback and recording safeguards

**Task:** Prepare the voluntary feedback worksheet and the <=5-minute demo recording script.

**Changes:** Added docs/feedback/SESSION_TEMPLATE.md with separate consent gates for
recording/upload, anonymized-note defaults, task prompts and retention fields. Added
docs/presentation/DEMO_RECORDING_SCRIPT.md with a 4m40s sequence that labels mock/local
backend boundaries and avoids presenting placeholders as live evidence. Updated status,
handoff and README records.

**Status:** Local documentation checkpoint prepared; no participant data or demo recording
collected.

**Notes:** Manual browser/device smoke, held-out endpoint quality, engine integration and
final presentation assembly remain. No shared contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay local demo smoke

**Task:** Verify the local demo after the documentation checkpoint.

**Changes:** Started the FastAPI demo temporarily and checked the served page for the
microphone capture path, WAV encoder and explicit demo/mock label.

**Status:** HTTP smoke returned 200 and the full suite passed 61 tests with 2 known
dependency deprecation warnings. The desktop browser-control surface failed to initialize,
so browser permission and physical-device microphone capture remain unverified.

**Notes:** Temporary server stopped after the check. No source, contract, dependency or
lockfile change.
## 2026-09-13 - Codex Atishay held-out generated speech evaluation

**Task:** Measure newly generated speech cases after the earlier development fixtures and
compare fixed-window endpoint candidates with labeled boundaries.

**Changes:** Added three 22.05 kHz mono PCM WAV cases under
tests/fixtures/audio/held_out, machine-readable labels/results under docs/feedback and a
fixture metadata test. Faster Whisper base.en CPU INT8 preserved the repeated phrase,
correction and two-part request. WebRTC produced no internal candidate for fluent or
repetition; the labeled 1.2 second break had a 1.880-3.860 second candidate with 0.606 IoU.

**Status:** Local held-out generated-case checkpoint measured. Human speech quality,
precise endpoint quality, browser/device smoke and integration remain unverified.

**Notes:** Fixture check passed 1 test; no shared contract, dependency or lockfile change.
Generated voice was used; no participant or third-party recording.
## 2026-09-13 - Codex Atishay opt-in local audio demo path

**Task:** Route real uploaded WAV input through the cached local Faster Whisper backend when
explicitly configured, while preserving the demo/mock default.

**Changes:** Added an environment-gated LocalPerception audio delegate, a visible backend
status label, configuration guidance and tests. A checked-in held-out WAV completed the
actual WebSocket demo route with the cached base.en CPU INT8 model; the acknowledgment
reported faster-whisper/cpu-int8 and the controller emitted its informational final.

**Status:** Local audio route verified through TestClient. Browser permission and physical
microphone capture, live vision and non-mock reasoning remain unverified.

**Notes:** Demo suite 11 passed; full suite verification follows. No shared contract,
dependency or lockfile change.
## 2026-09-13 - Codex Atishay visible local transcript output

**Task:** Make the local audio result reviewable in the browser demo.

**Changes:** The mock reasoner now includes the latest observation text in its informational
final response. This keeps the reasoner explicitly mock while exposing the LocalPerception
transcript for local audio review.

**Status:** Demo and full suites pass after the change; no shared contract, dependency or
lockfile change.

**Notes:** The output remains informational and cannot authorize a real action.
## 2026-09-13 - Codex Atishay presentation content outline

**Task:** Prepare a template-neutral presentation draft while the official template remains
unavailable.

**Changes:** Added docs/presentation/SLIDE_OUTLINE.md with eight evidence-labeled slides,
speaker-note requirements and explicit remaining gates.

**Status:** Content draft prepared; official template, final deck, video and integration
evidence remain.

**Notes:** No source, contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay session path isolation

**Task:** Prevent browser clients from supplying arbitrary filesystem paths to the demo
perception boundary.

**Changes:** No-byte fallbacks are rooted in the per-session temporary directory whenever
the WebSocket route supplies a media root. Added a regression test for a private path
payload.

**Status:** Demo suite 12 passed; full suite 65 passed; Ruff clean.

**Notes:** Base64 media validation remains unchanged. No shared contract, dependency or
lockfile change.
## 2026-09-13 - Codex Atishay local model configuration guard

**Task:** Make invalid opt-in local model configuration fail before the demo advertises a
local backend.

**Changes:** DemoPerception validates ACCESSFLOW_DEMO_WHISPER_MODEL as an existing directory.
The WebSocket sends a labeled demo/config error and closes before creating the Agent when
the path is invalid. Added direct and WebSocket regression tests.

**Status:** Demo suite 14 passed; full suite 67 passed; Ruff clean.

**Notes:** Default demo/mock behavior and valid local mode remain unchanged. No shared
contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay opt-in local Ollama vision path

**Task:** Add an optional local PNG provider behind the existing replaceable vision seam.

**Changes:** Added a standard-library Ollama generate provider with base64 PNG encoding,
loopback endpoint validation, response/error handling and backend labeling. The demo can
enable it with ACCESSFLOW_DEMO_OLLAMA_VISION_MODEL and an optional loopback endpoint.
LocalPerception preserves frame identity and reports ollama/<model>.

**Status:** Provider and demo delegate verified with mocked responses. No live Ollama service
or vision-quality result is claimed.

**Notes:** Perception and demo tests pass; no shared contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay local vision availability check

**Task:** Check whether the optional local Ollama service is available for live evidence.

**Result:** No ollama executable was found and the expected loopback port 11434 was not
open. No service was installed or downloaded.

**Status:** The provider remains mocked and the live vision-quality checkpoint remains open.

**Notes:** No source, contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay WebSocket media protocol smoke

**Task:** Verify that browser WAV and PNG payloads survive the session-scoped media boundary
and reach the demo controller path.

**Changes:** Added transport-only demo_status events containing the received media kind and
source ID. Added WebSocket tests for base64 WAV and PNG uploads. WAV reaches the mock
controller final; PNG is validated and retained for the session, while the current v0.1 agent
requires a paired transcript before emitting a controller final.

**Status:** Demo suite 18 passed; full suite 77 passed; Ruff and git diff --check clean.

**Notes:** No shared contract, dependency or lockfile change. Image-only controller planning
remains an engine integration item; no live ASR or vision-quality claim is made.

## 2026-09-13 - Codex Atishay functional Chrome browser smoke

**Task:** Exercise the local demo in Chrome through its real text, WAV and PNG controls.

**Changes:** No product source change in this checkpoint. Captured functional browser evidence for
the connected WebSocket, text final, WAV media status/final and PNG media status plus paired
transcript final. Added docs/feedback/BROWSER_SMOKE.md.

**Status:** Functional Chrome matrix passed; rendered width had no horizontal overflow. Physical
microphone/device capture, pixel inspection and separate console capture remain unverified.

**Notes:** Uvicorn required a local-only websockets 17.1 install to serve the WebSocket route.
The committed dependency files were not changed; shared dependency ownership should review this
proposal before fresh-machine browser use.
## 2026-09-13 - Codex Atishay synthetic microphone browser smoke

**Task:** Exercise microphone start, stop, WAV encoding and upload in real Chrome without
capturing a person.

**Changes:** No product source change. Chrome's fake audio device entered recording state,
stopped cleanly, uploaded a WAV and received media_received=audio plus the mock final.

**Status:** Synthetic microphone browser path passed. Physical device permission and capture,
pixel inspection and separate console capture remain unverified.

**Notes:** No participant or physical recording was used. No shared contract, dependency or
lockfile change beyond the previously documented local-only websockets runtime.

## 2026-09-14 - Codex Atishay multimodal end-to-end evidence

**Task:** Prioritize multimodal end-to-end coverage for Workstream B.

**Changes:** Added a demo-owned AudioWorklet recorder module and route, a recoverable input-error
path, and a demo test that carries a validated WAV followed by a PNG through injected local ASR and
vision, DemoPerception and one Agent context. Fresh Chrome CDP smoke covered text, WAV, PNG plus
paired transcript, synthetic microphone capture and clean console output.

**Status:** Focused demo suite 22 passed; perception suite 43 passed; final full suite 81 passed;
Ruff and git diff --check clean. Browser status remains IN PROGRESS because physical microphone,
pixel inspection, live ASR/vision quality and non-mock reasoning are unverified.

**Notes:** Branch remains atishay/perception. origin/mridul/engine was fetched at ad04bca for review;
no engine-owned files, shared contracts, lockfiles or dependency manifests were changed. The local
only websockets 17.1 runtime requirement remains a shared dependency proposal.

## 2026-09-14 - Codex Atishay image-only controller gap

**Task:** Extend the multimodal evidence to the image-only informational case without editing
engine-owned files.

**Changes:** Added a strict expected-failure demo example showing that a frame reaches the current
Agent and an opted-in reasoner response, but the controller does not emit an informational final
until completed speech exists. Added an additive proposal for an informational evidence basis that
keeps state-changing calls behind the existing speech and authorization gates.

**Status:** Full suite 81 passed, 1 strict xfailed; demo 22 passed, 1 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** The expected failure is intentional integration evidence. Branch remains
atishay/perception; no engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay live local audio plus injected vision

**Task:** Strengthen multimodal end-to-end evidence with the installed local ASR model.

**Changes:** Ran the checked-in synthetic speech WAV through the cached Faster Whisper base.en CPU
INT8 snapshot, paired it with a validated PNG and injected vision provider in one Agent context,
and recorded the mixed evidence in docs/feedback/MULTIMODAL_E2E.md.

**Status:** Local ASR transcribed the fixture and the paired context completed in 3.222 seconds.
Live vision was unavailable; the final remains informational and the reasoner remains a test double.

**Notes:** No source, engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal ordering coverage

**Task:** Broaden the deterministic multimodal end-to-end case across arrival orderings.

**Changes:** Parameterized the shared Agent-context test for audio-then-image and image-then-audio.
Both orderings preserve the two observations and produce the informational multimodal response.

**Status:** Full suite 82 passed, 1 strict xfailed; demo 23 passed, 1 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** The image-only strict xfail and additive proposal remain unchanged. No engine, contract,
lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal revision and frame retention

**Task:** Cover revised speech hypotheses while retaining image evidence in one multimodal context.

**Changes:** Added a demo Agent test that sends two audio revisions for one utterance and a PNG.
The newer revision replaces the old speech observation while the frame and corrected text remain
available to the reasoner.

**Status:** Full suite 83 passed, 1 strict xfailed; demo 24 passed, 1 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** The image-only strict xfail remains the engine integration boundary. No engine, contract,
lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay browser local-ASR multimodal run

**Task:** Connect the local ASR evidence to the real browser transport.

**Changes:** Started the demo with the cached Faster Whisper base.en CPU INT8 snapshot, uploaded
synthetic_speech.wav through Chrome, observed the faster-whisper/cpu-int8 acknowledgment and
transcript-bearing final, then uploaded a PNG and submitted follow-up text in the same session.
The browser event stream was clean and layout had no overflow.

**Status:** Mixed browser evidence recorded: real local audio inference plus demo/mock image/text.
Physical capture, live vision quality and non-mock reasoning remain unverified.

**Notes:** No source, engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay changed-frame integration gap

**Task:** Expose the active-frame replacement requirement for multimodal scenarios.

**Changes:** Added a strict expected-failure demo example showing that frame 2 reaches the current
reasoner while frame 1 remains in the view. The integrated engine branch already removes its prior
active frame; this branch records the boundary without editing engine-owned code.

**Status:** Full suite 83 passed, 2 strict xfailed; demo 24 passed, 2 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** The image-only expected failure and additive proposal remain in place.

## 2026-09-14 - Codex Atishay visible multimodal reasoner context

**Task:** Make the browser demo's informational response visibly expose all retained modalities.

**Changes:** DemoReasoner now includes prior observations in its response context. A fresh Chrome
WAV, PNG and text sequence showed the final response containing both prior audio and image context.

**Status:** Full suite 84 passed, 2 strict xfailed; demo 25 passed, 2 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** The response remains an explicitly labeled mock informational result. No engine, contract,
lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay combined WebSocket context regression

**Task:** Protect the visible combined multimodal response with an automated route test.

**Changes:** Added a WebSocket regression that uploads validated WAV and PNG payloads, submits a
follow-up transcript, and asserts media source IDs plus audio and image context in the final.

**Status:** Full suite 85 passed, 2 strict xfailed; demo 26 passed, 2 strict xfailed; perception
43 passed; Ruff and git diff --check clean.

**Notes:** A clean rerun passed after one transient Starlette test-client teardown failure.

## 2026-09-14 - Codex Atishay physical microphone browser smoke

**Task:** Verify the served microphone path with the machine's real audio input.

**Changes:** No repository source or dependency changes. Isolated Chrome without a fake audio-device
flag entered getUserMedia recording from the present Microphone Array, loaded the AudioWorklet,
uploaded a WAV over the session WebSocket and observed media_received=audio plus the mock final.

**Status:** Physical-device permission and capture passed. Pixel inspection remains unverified;
live vision quality, human speech accuracy and non-mock reasoning remain open.

**Notes:** Temporary profile and CDP harness only; no source, contract or dependency manifest changed.

## 2026-09-14 - Codex Atishay WebSocket multimodal revision retention

**Task:** Verify latest speech revision retention alongside a frame through the browser route.

**Changes:** Added a WebSocket test that sends a WAV, two transcript revisions for one utterance,
a PNG and follow-up text; the final retains the revised speech and image context without the old
hypothesis.

**Status:** Demo suite 27 passed, 2 strict xfailed; full suite 86 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal write safety

**Task:** Verify that a final image cannot authorize a write while speech is unfinished.

**Changes:** Added an owned demo regression using an explicit write manifest and proposal; partial
speech plus final image keeps correction_pending true and produces no executor call or effect.

**Status:** Demo suite 28 passed, 2 strict xfailed; full suite 87 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay WebSocket image-first ordering

**Task:** Verify image-before-audio ordering through the browser route.

**Changes:** Added a WebSocket regression that sends a PNG before a WAV and verifies the later audio
final retains image context in the same session.

**Status:** Demo suite 29 passed, 2 strict xfailed; full suite 88 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay malformed image recovery

**Task:** Verify recoverable handling of malformed PNG input in the WebSocket session.

**Changes:** Added a demo regression that receives a labeled demo/input error for invalid image data
and then accepts a text request through the same session.

**Status:** Demo suite 30 passed, 2 strict xfailed; full suite 89 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay image-only write safety

**Task:** Verify image-only evidence cannot authorize a write.

**Changes:** Added an owned regression with an explicit write proposal; the image-only session stays
correction pending and creates no executor call or effect.

**Status:** Demo suite 31 passed, 2 strict xfailed; full suite 90 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay changed-frame WebSocket reproducer

**Task:** Pin stale frame retention through the browser route.

**Changes:** Added a strict expected-failure test that sends two frames and a follow-up transcript;
the final currently exposes both frame observations.

**Status:** Full suite 90 passed, 3 strict xfailed; demo suite 31 passed, 3 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay vision backend failure

**Task:** Verify vision backend failures propagate as typed errors.

**Changes:** Added an owned regression for a failing injected vision provider; the agent emits
backend_failure and no final response.

**Status:** Full suite 91 passed, 3 strict xfailed; demo suite 32 passed, 3 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay WebSocket vision failure recovery

**Task:** Verify configured vision failure recovery through the real demo WebSocket boundary.

**Changes:** Added an owned regression with a failing injected vision provider. The route emits a
backend_failure error and the same session remains usable for a later text request.

**Status:** Focused regression passed. Expected suite counts after this change are 92 passed, 3 strict
xfailed; demo suite 33 passed, 3 strict xfailed; perception suite 43 passed.

**Notes:** This records failure propagation and session recovery only; it makes no live vision quality
claim. No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay loopback Ollama multimodal transport

**Task:** Cover the configured Ollama vision HTTP path inside a multimodal Agent composition.

**Changes:** Added an owned async regression with a local loopback HTTP protocol stub. The actual
OllamaVisionProvider sends the PNG request beside local injected ASR, and the Agent retains both
observations with the Ollama backend label and informational result.

**Status:** Focused regression passed. Expected suite counts after this change are 93 passed, 3 strict
xfailed; demo suite 34 passed, 3 strict xfailed; perception suite 43 passed.

**Notes:** The loopback service is a deterministic protocol stub, so this is transport and payload
evidence rather than live vision quality. No engine, contract, lockfile or dependency manifest changes
were made.

## 2026-09-14 - Codex Atishay in-flight frame stale-result coverage

**Task:** Cover a changed-device-frame race while the first vision result is still in flight.

**Changes:** Added an owned async Agent regression with a delayed frame 1 perception result. Frame 2
arrives and reaches the reasoner first; after frame 1 is released, its stale result is rejected and
never appears in a frame-bearing reasoner view.

**Status:** Focused regression passed. Expected suite counts after this change are 94 passed, 3 strict
xfailed; demo suite 35 passed, 3 strict xfailed; perception suite 43 passed.

**Notes:** This covers stale-result handling with a perception seam and makes no live vision quality
claim. No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay structural PNG validation

**Task:** Ensure malformed image payloads cannot reach the multimodal vision backend.

**Changes:** Hardened the owned PNG validator to check chunk boundaries, CRCs, legal IHDR metadata,
IDAT presence and terminal IEND structure. The demo now uses the same validator and removes rejected
materializations. Migrated image tests to real small PNG fixtures and added valid metadata, truncated,
bad-CRC and WebSocket recovery coverage.

**Status:** Full suite 98 passed, 3 strict xfailed; demo suite 36 passed, 3 strict xfailed; perception
suite 46 passed; Ruff and git diff --check clean.

**Notes:** Validation is structural and does not decode pixels or claim image understanding. No engine,
contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay configured vision WebSocket wiring

**Task:** Exercise the configured Ollama vision path through the actual demo WebSocket route.

**Changes:** Added an owned route regression that sets the vision environment configuration, runs a
loopback HTTP protocol service, uploads a real PNG, waits for the image observation, and submits a
follow-up transcript. The final contains both the service result and the spoken question.

**Status:** Full suite 99 passed, 3 strict xfailed; demo suite 37 passed, 3 strict xfailed; perception
suite 46 passed; Ruff, compilation and git diff --check clean.

**Notes:** The loopback service is a deterministic protocol stub and does not provide live vision quality
evidence. No engine, contract, lockfile or dependency manifest changes were made.


2026-09-14: Continued multimodal E2E hardening on atishay/perception. LocalPerception now exposes audio_backend_name for truthful injected-ASR versus Faster Whisper labeling, and failed post-header WAV validation removes its temporary materialization. Full suite: 101 passed, 3 strict xfailed.

2026-09-14: Added combined configured multimodal route coverage on atishay/perception: one WebSocket session sends validated WAV and PNG through local ASR and loopback vision, preserving labels, source IDs and informational output. Full suite: 102 passed, 3 strict xfailed.

2026-09-14: Added ASR failure recovery coverage on atishay/perception: a WebSocket backend_failure is followed by validated PNG and spoken input, with retained image context and informational output. Full suite: 103 passed, 3 strict xfailed.

2026-09-14: Fresh runtime evidence on atishay/perception combined cached Faster Whisper CPU INT8 audio with configured OllamaVisionProvider over a loopback service in 1.326 seconds; one session retained recognized speech and image evidence. Vision and reasoning limits remain explicit.

2026-09-14: PNG IDAT integrity hardened on atishay/perception: CRC-valid corrupt or incomplete zlib streams are rejected before vision inference. Full suite: 104 passed, 3 strict xfailed.
2026-09-14: Added the owned multimodal policy boundary: image captions cannot drive speech correction or backchannel decisions; focused and full validation passed at 105 tests with 3 strict xfails.

2026-09-14: Added recoverable structural validation for demo WebSocket messages and payloads; malformed multimodal input no longer terminates the session. Full validation: 107 passed, 3 strict xfails.

2026-09-14: Corrected truthful demo audio labeling: unknown injected backends now report local/unknown-audio, while Faster Whisper fixtures declare their identity. Full validation: 108 passed, 3 strict xfails.

2026-09-14: Ollama vision response shape hardening added on atishay/perception; list and null JSON roots are classified cleanly. Full validation: 110 passed, 3 strict xfails.

2026-09-14: Added malformed vision JSON recovery through the configured demo WebSocket route; list response emits backend_failure and later transcript completes. Full validation: 111 passed, 3 strict xfails.

2026-09-14: Added vision provider timeout evidence: transport TimeoutError is normalized to RuntimeError for backend recovery. Full validation: 112 passed, 3 strict xfails.

2026-09-14: Added two-connection multimodal session isolation regression; fresh WebSocket state excludes prior audio and image context. Full validation: 113 passed, 3 strict xfails.

2026-09-15: Demo upload boundary now rejects oversized encoded media before base64 decode and file creation. Full validation: 114 passed, 3 strict xfails.

2026-09-15: Added configured vision-timeout route recovery evidence; provider timeout emits backend_failure and later transcript completes in the same session. Full validation: 115 passed, 3 strict xfails.


2026-09-15: Multimodal provenance follow-up added on atishay/perception. Browser capture timestamps
now survive event translation, audio speech bounds are forwarded, and frame timestamps reach image
observations. Full validation: 117 passed, 3 strict xfailed; no protected files changed.


2026-09-15: Quota exhaustion now has provider and WebSocket recovery evidence on atishay/perception.
Contradictory visual evidence is captured as a strict expected controller failure with an additive
provenance/conflict proposal. Full validation: 119 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Browser capture timestamps now use envelope-level transport with payload compatibility.
Existing timing provenance coverage remains green. Full validation: 119 passed, 4 strict xfailed; no
protected files changed.


2026-09-15: Cross-modal in-flight race coverage passes: a delayed audio observation survives frame
arrival and reaches the same reasoner view. Full validation: 120 passed, 4 strict xfailed; no protected
files changed.
2026-09-16: Made the conflicting-frame strict example deterministic by waiting for frame one to reach the reasoner
before submitting frame two. The remaining expected failure is now isolated to missing controller conflict state;
no source, contract or protected files changed.
2026-09-16: Corrected the conflict reproducer to use two valid content-distinct PNG uploads and assert the injected
Tuesday/Wednesday captions. With --runxfail it reaches the expected write-safety assertion, isolating controller
conflict state. No source, contract or protected files changed.
2026-09-16: Reviewed origin/mridul/engine at 919ed27 in a disposable overlay with current owned demo/perception
paths. Targeted active-frame replacement and image-only informational tests pass upstream; the conflict case is
blocked before planning because the prior frame is removed. The remaining proposal needs pre-replacement comparison
or provenance. No protected files changed.


2026-09-15: Invalid PNG materialization cleanup now has direct regression evidence. Full validation:
121 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Identity-free injected vision adapters now receive local/unknown-vision labeling instead
of crashing or implying a model. Full validation: 122 passed, 4 strict xfailed; no protected files changed.


2026-09-15: OllamaVisionProvider now preserves structured HTTP quota details, including a 429 JSON
error body, through the classified failure boundary. Full validation: 123 passed, 4 strict xfailed;
no protected files changed.


2026-09-15: Added WebSocket-level HTTP 429 vision quota recovery evidence. The provider error body
becomes backend_failure and the same session accepts a later transcript. Full validation: 124 passed,
4 strict xfailed; no protected files changed.


2026-09-15: Added slow-image worker responsiveness evidence: a blocked vision provider no longer blocks
an async heartbeat. Full validation: 125 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Added slow-ASR worker responsiveness evidence alongside slow-image coverage. Both
replaceable perception paths keep an async heartbeat usable. Full validation: 126 passed, 4 strict
xfailed; no protected files changed.


2026-09-15: Browser multimodal output now uses textContent-backed DOM nodes rather than innerHTML; the
existing UI test covers the safe rendering path. Full validation: 126 passed, 4 strict xfailed; no
protected files changed.


2026-09-15: Browser media event translation now runs through asyncio.to_thread, keeping base64 decoding
and WAV/PNG validation off the WebSocket receive loop. Full validation: 126 passed, 4 strict xfailed;
no protected files changed.


2026-09-15: LocalPerception now rejects blank or non-string audio and image provider output before
creating observations. Full validation: 128 passed, 4 strict xfailed; no protected files changed.

2026-09-15: Bounded the demo reasoner's prior multimodal context to 16,384 characters while retaining
the newest evidence under truncation. Full validation: 129 passed, 4 strict xfailed; demo 56 passed
plus 4 strict xfailed; perception 57 passed. No protected files changed.

2026-09-15: Added syntactically invalid vision JSON byte coverage at the provider and WebSocket
boundaries. Both classify backend failure and preserve later transcript recovery. Full validation:
131 passed, 4 strict xfailed; demo 57 passed plus 4 strict xfailed; perception 58 passed. No protected
files changed.

2026-09-15: Tightened vision provenance labeling: model-only injected backends now remain
local/unknown-vision without an explicit ollama/ identity. Full validation: 132 passed, 4 strict
xfailed; demo 58 passed plus 4 strict xfailed; perception 58 passed. No protected files changed.

2026-09-15: Added opt-in finite LocalPerception deadlines for audio and image provider calls, with
modality-specific timeout errors and WebSocket audio recovery evidence. Full validation: 141 passed,
4 strict xfailed; demo 59 passed plus 4 strict xfailed; perception 66 passed. Synchronous work already
running in to_thread remains non-forcibly-cancellable. No protected files changed.

2026-09-15: Guarded LocalPerception timeout-helper cleanup during observer cancellation and covered an
already-running audio worker. Full validation: 142 passed, 4 strict xfailed; demo 59 passed plus 4
strict xfailed; perception 67 passed. No protected files changed.

2026-09-15: Added multimodal WebSocket recovery coverage: after a vision backend failure, a later
valid frame and WAV complete in the same session and the final context retains both observations.
Validation: 143 passed, 4 strict xfailed; no protected files changed.

2026-09-15: LocalPerception now has independent bounded audio/image workers with same-session frame
and same-utterance revision coalescing, stale-result suppression and shutdown cleanup. DemoPerception
retains the vision worker per session. Validation: 149 passed, 4 strict xfailed; no protected files
changed.

2026-09-15: Completed the bounded-worker failure matrix: stale vision exceptions and timeouts are
discarded after newer frames, while a recovered frame and WAV still reach one multimodal session.
Validation: 152 passed, 4 strict xfailed; no protected files changed.

2026-09-15: Scoped LocalPerception admission workers per session so concurrent session pending frames
cannot supersede each other; same-session coalescing remains bounded. Validation: 153 passed, 4 strict
xfailed; no protected files changed.
2026-09-15: Added one serialized WebSocket sender for controller outputs, media statuses and input
errors, with a forced concurrent-send regression. Added a configured route regression covering the real
LocalPerception model-path branch and OllamaVisionProvider HTTP request together. Validation: 155 passed,
4 strict xfailed; demo 64 passed plus 4 strict xfailed; perception 75 passed. No protected files changed.
2026-09-15: Added concurrent WebSocket session isolation evidence: two open sessions keep image context
separate while one completes a fresh transcript. Validation: 156 passed, 4 strict xfailed; demo 65
passed plus 4 strict xfailed; perception 75 passed. No protected files changed.
2026-09-16: Added a lifecycle admission barrier for LocalPerception and a closed guard for DemoPerception.
Late audio/image validation cannot create provider work after shutdown; closed WebSocket peers no longer
leave sender-task exceptions. Extended the configured WebSocket path to carry text, WAV and PNG together,
and recorded the pending timing-policy seam as a strict expected failure. Validation: 162 passed, 5 strict
xfailed; demo 68 passed plus 4 strict xfailed; perception 78 passed. No protected files changed.
2026-09-16: Added route-level valid-media cleanup evidence: real WAV and PNG files are present during the
WebSocket session and its temporary directory is removed after disconnect. Validation: 163 passed, 5 strict
xfailed; demo 69 passed plus 4 strict xfailed; perception 78 passed. No protected files changed.
2026-09-16: Extended configured WebSocket evidence to send two revisions for one WAV utterance and retain
only the corrected audio alongside text and PNG. The focused route regression and full suite passed; no
protected files changed.
2026-09-16: Extended concurrent WebSocket isolation to carry image and audio in one open session while a
second session completes fresh text. The second context remains free of both modalities; no protected files
changed.
2026-09-16: Added configured WebSocket audio failure/recovery evidence with a retained PNG: revision 0
fails, revision 1 recovers for the same utterance, and the final contains only corrected audio plus the frame.
Validation: 164 passed, 5 strict xfailed; demo 70 passed plus 4 strict xfailed; perception 78 passed.
2026-09-16: Configured multimodal route now asserts distinct generated event IDs for retained text, audio
and image observations, alongside existing source identity checks. No protected files changed.
2026-09-16: Promoted the owned timing-policy seam to accept optional ActivitySummary metadata and added a final
transcript guard proving pause timing cannot override completion. Shared engine/controller wiring remains pending.
Validation: 166 passed, 4 strict xfailed; demo 70 passed plus 4 strict xfailed; perception 80 passed. No protected
files changed.
2026-09-16: Opened the existing browser media, console and microphone captures directly. The shown viewport has no
visible clipping, overlap or broken text. The captures are dated 13–14 September, so fresh current-HEAD full-page
visual inspection remains open. No source or protected files changed.
2026-09-16 verification: Hardened WAV validation to read all declared PCM frames in bounded chunks and reject
truncated payloads before inference. Added a focused regression; full suite: 167 passed, 4 strict xfailed.
No protected files changed.
2026-09-16 verification: Hardened PNG validation to check decompressed scanline sizing and filter bytes,
including Adam7 row sizing, before vision inference. Added incomplete-scanline coverage; full suite: 168 passed,
4 strict xfailed. No protected files changed.
2026-09-16 verification: Added a valid Adam7 PNG regression and corrected empty-pass sizing; full suite: 169
passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Normalized Ollama vision configuration validation for non-string model/endpoints and
non-finite, boolean or non-positive timeouts. Added focused cases; full suite: 174 passed, 4 strict xfailed.
No protected files changed.
2026-09-16 verification: Added a browser WebSocket ready-state guard so early text, WAV or PNG actions produce
a labeled connecting error instead of throwing. Extended the existing page regression; demo suite: 70 passed,
4 strict xfailed. No protected files changed.
2026-09-16 verification: Fixed cross-utterance audio starvation by replacing pending work per utterance key while
keeping a bounded pending-key limit. Added the requested race regression; full suite: 175 passed, 4 strict xfailed.
No protected files changed.
2026-09-16 verification: Replaced the browser connecting-time send error with a bounded ordered queue that flushes
on WebSocket open and reports closed/full transport states. Extended the existing page regression; full suite:
175 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Fresh shallow public clone checked out atishay/perception from the shared GitHub
repository and included ATISHAY_START_HERE.md at commit 4892c185. The disposable clone was removed afterward;
no source or protected files changed.
2026-09-16 verification: Ran the served demo through a real local Uvicorn/WebSocket session with WAV, PNG and
transcript inputs. The sequential finals completed and the last context retained both audio and image evidence.
No protected files changed.
2026-09-16 verification: Ran the current head with the cached Faster Whisper base.en CPU INT8 model and a loopback
Ollama vision endpoint. The speech fixture was transcribed, PNG evidence was returned, and the final transcript
retained both modalities. This remains mock reasoning and protocol/backend evidence, not a quality benchmark.
2026-09-16 verification: Browser transcript controls now preserve one utterance ID across partial and final
hypotheses, increment revisions for each follow-up submission, and close the active utterance after the final
hypothesis. Focused demo tests and JavaScript syntax validation passed; no protected files changed.
2026-09-16 verification: Browser media IDs now come from a page-scoped monotonic allocator, preventing rapid WAV, microphone and PNG submissions from reusing source identities. Lazy send payloads also prevent rejected connecting-queue actions from consuming transcript revisions or media IDs; the direct browser queue/revision harness passed. No protected files changed.
2026-09-16 verification: Shielded threaded browser media materialization from receiver cancellation and drained active materialization tasks before temporary-session cleanup. Added a focused disconnect/cancellation regression; full suite: 176 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Hardened PNG validation against oversized declared dimensions by grouping scanline accounting, bounding decoded payloads at 64 MiB before decompression, and removing the unbounded zlib flush. Added a huge-dimension regression; full suite: 177 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: PNG validation now requires a valid palette before IDAT for indexed-color images and bounds palette entries by bit depth. Added a structural regression; full suite: 178 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Fresh current-head Uvicorn/WebSocket smoke accepted the checked-in WAV and a valid PNG in one session, then returned a mock final retaining both audio and image context. No protected files changed.
2026-09-16 verification: Tightened PCM target-rate, energy-activity, WebRTC VAD and pause-threshold validation to reject booleans, wrong numeric types and non-finite values with stable ValueErrors. Added focused cases; full suite: 187 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Energy activity now validates AudioBuffer sample-rate and sample-width metadata before frame timing calculations. Added invalid-metadata regressions; full suite: 188 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Captured the current demo head through local headless Chrome at 1280x1600. The full page showed no visible clipping, overlap or broken text; live interactive device behavior and live model quality remain separate evidence gaps. No source or protected files changed.
2026-09-16 verification: Added explicit labels for the transcript, WAV and PNG browser controls. A refreshed current-head 1280x1600 headless Chrome capture remained legible with no visible clipping or overlap. No protected files changed.
2026-09-16 verification: Energy activity now rejects PCM buffers with trailing partial samples instead of silently dropping bytes. Added focused coverage; full suite: 189 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Current-head Chrome CDP interaction drove text partial/final submission, checked-in WAV upload and generated PNG upload. The page showed connected/media acknowledgments and retained both prior modalities with zero console or page exceptions. No source or protected files changed.
2026-09-16 verification: Browser event translation now rejects explicit blank or non-string utterance and frame identities while preserving generated IDs for omitted fields. Added focused demo coverage; full suite: 196 passed, 4 strict xfailed. No protected files changed.
2026-09-16 verification: Browser event translation now rejects coerced revision/final/text values, non-finite or boolean timestamps, and inverted speech bounds before typed events are built. Added focused demo coverage; full suite: 202 passed, 4 strict xfailed. No protected files changed.
