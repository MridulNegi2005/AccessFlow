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
