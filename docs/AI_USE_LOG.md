# AI-use development log

## 2026-09-13 — Codex bootstrap

- Feature origin: User-approved AccessFlow plan; original friend-agent proposal and prior
  ideation should be described honestly in the final organizer disclosure.
- Tool: Codex (current coding session).
- Prompt: Implement the approved AccessFlow implementation/collaboration plan; prioritize
  Git initialization, folder organization and context so Atishay can start independently.
- Output: Contracts, interfaces, fakes, initial controller, project configuration and docs.
- Human modifications/review: Not yet recorded; do not imply team review has occurred.
- Validation: Record actual commands/results in handoffs. No live-model evidence yet.

Append each future milestone with prompts, outputs, edits, tests and reviewer. This log
supports the mandatory organizer form; it is not a completed or signed disclosure form.

## 2026-09-13 - Codex Atishay audio fixture checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a reproducible audio fixture with explicit provenance and format validation.
- Output: Added a synthetic tone WAV, SHA-256 provenance and a checked-in fixture test.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 16 passed; Ruff passed for owned paths.
- Backend/dependencies: Python standard-library audio generation; no dependency or contract changes.
## 2026-09-13 - Codex Atishay ASR checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Make the optional local Faster Whisper path testable without model downloads.
- Output: Added model-path validation, CPU int8 factory configuration and segment aggregation tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 23 passed; Ruff passed for owned paths.
- Backend/dependencies: Faster Whisper remains optional; no dependency or contract changes; no live model run.
## 2026-09-13 - Codex Atishay PCM checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a small reusable PCM loader and deterministic activity baseline without changing shared contracts.
- Output: Added mono/stereo loading, rate conversion, RMS activity frames and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Perception suite 21 passed; full suite verification follows; Ruff passed for owned paths.
- Backend/dependencies: Python standard library `audioop`; deprecation recorded, no lockfile change.
## 2026-09-13 - Codex Atishay demo checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Build a minimal fake-agent browser demo that renders controller output events.
- Output: Added FastAPI WebSocket routing, typed event conversion, mock-labeled controls and smoke tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 6 passed; full suite 37 passed; Ruff passed for owned paths.
- Backend/dependencies: Existing FastAPI stack; no dependency or contract changes. Test-client deprecation warnings recorded.
## 2026-09-13 - Codex Atishay vision checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a replaceable PNG provider path while preserving frame and event provenance.
- Output: Added standard-library PNG validation, injected provider execution and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused perception suite 15 passed; Ruff passed for owned paths.
- Backend/dependencies: Injected provider seam; no dependency or contract changes.

## 2026-09-13 - Codex Atishay turn-policy checkpoint

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Implement a compact synchronous turn policy against the existing v0.1 observation contract.
- Output: Added correction, backchannel, partial-speech and stale-revision decisions with focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Full suite 29 passed; Ruff passed for owned paths.
- Backend/dependencies: Model-free heuristic; no dependency or contract changes.

## 2026-09-13 — Codex Atishay handoff

- Feature origin: User request to prepare Atishay’s independent repository start point.
- Tool: Codex (current coding session).
- Prompt: Verify the public clone/branch path and provide accurate `ATISHAY_START_HERE.md` guidance.
- Output: Confirmed the clone and branch checkout; clarified that direct pushes need collaborator
  access and that fork-based pull requests are the fallback.
- Human modifications/review: Awaiting Atishay’s review.
- Validation: `uv run --python 3.12 --extra dev pytest tests/test_contract.py` — 4 passed.
- Backend/dependencies: No live backend and no committed dependency changes.

## 2026-09-13 - Codex Atishay PCM maintenance checkpoint

- Feature origin: The approved AccessFlow Workstream B plan and the handoff requirement to replace deprecated audioop.
- Tool: Codex (current coding session).
- Prompt: Replace the owned audioop PCM path with a small maintained implementation without changing the shared contract.
- Output: Added standard-library PCM decoding, stereo downmixing, linear resampling and RMS helpers; added 1/2/3/4-byte coverage.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused audio suite 9 passed; Ruff passed for owned paths; no audioop import remains.
- Backend/dependencies: No dependency or lockfile change; no live ASR/VAD evidence.

## 2026-09-13 - Codex Atishay local ASR measurement

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Run the explicitly installed Faster Whisper base.en CPU INT8 backend on the checked-in audio fixture and record timing honestly.
- Output: Installed the optional runtime in the ignored virtual environment, downloaded the model into the ignored models directory and recorded the first local pass.
- Human modifications/review: Awaiting Atishay review.
- Validation: Model loaded in 0.464 s; inference took 0.677 s for 0.500 s of audio; realtime factor 1.354; transcript was empty as expected for a synthetic tone.
- Backend/dependencies: Faster Whisper 1.2.1, Systran/faster-whisper-base.en, CPU int8; no tracked dependency or contract change.
## 2026-09-13 - Codex Atishay demo teardown repair

- Feature origin: Full-suite verification of the Workstream B demo.
- Tool: Codex (current coding session).
- Prompt: Fix the WebSocket demo cleanup so normal disconnects await the queue-driven agent shutdown cleanly.
- Output: The demo now cancels only transport tasks, sends a typed session-end event and waits briefly for the agent before cancelling as a last resort.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 6 passed; full suite 50 passed; Ruff passed for owned paths.
- Backend/dependencies: No dependency or contract change.
## 2026-09-13 - Codex Atishay illustrative speech ASR run

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Generate a clearly labeled non-participant speech fixture and run the installed Faster Whisper base.en CPU INT8 adapter.
- Output: Added synthetic_speech.wav with provenance and recorded a LocalPerception.observe run.
- Human modifications/review: Awaiting Atishay review.
- Validation: 5.304 s fixture; adapter elapsed 5.874 s; realtime factor 1.108; transcript matched the known script apart from the final number wording.
- Backend/dependencies: Faster Whisper 1.2.1, CPU int8; no tracked dependency or contract change.
## 2026-09-13 - Codex Atishay timing-only activity summary

- Feature origin: The approved AccessFlow Workstream B plan and the v0.1 contract limitation around timer events.
- Tool: Codex (current coding session).
- Prompt: Add a timing-only activity summary that reports pauses without converting them into turn completion, and record an additive contract proposal.
- Output: Added contiguous activity windows, silence durations, pause signal tests and a pending timing metadata proposal.
- Human modifications/review: Awaiting Atishay and Mridul review.
- Validation: Focused audio/timing suite 13 passed; Ruff passed for owned paths; no shared contract changed.
- Backend/dependencies: Standard library energy frames; no dependency or lockfile change.
## 2026-09-13 - Codex Atishay optional WebRTC activity backend

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Add a lazy optional WebRTC VAD adapter with deterministic injection tests, then compare it with the energy baseline on the two generated fixtures.
- Output: Added 8/16/32/48 kHz and 10/20/30 ms format validation, optional package loading, and activity comparison evidence.
- Human modifications/review: Awaiting Atishay review.
- Validation: Focused perception suite 15 passed; Ruff passed for owned paths. Tone: WebRTC 25/25 active frames. Generated speech: WebRTC 189/265 active frames and 0.640 s trailing silence.
- Backend/dependencies: webrtcvad-wheels 2.0.14 in the ignored environment only; no tracked dependency, lockfile or contract change.

## 2026-09-13 - Codex Atishay pause-and-correction fixture

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Generate a non-participant speech fixture with an explicit pause and self-correction, then measure ASR and acoustic activity.
- Output: Added synthetic_pause_correction.wav with provenance and recorded WebRTC and Faster Whisper results.
- Human modifications/review: Awaiting Atishay review.
- Validation: 6.024 s fixture; WebRTC 139/301 active frames across three windows with 0.640 s trailing silence; ASR elapsed 1.334 s and realtime factor 0.221; transcript preserved the correction wording.
- Backend/dependencies: Faster Whisper 1.2.1 and webrtcvad-wheels 2.0.14 in the ignored environment; no tracked dependency, lockfile or contract change.

## 2026-09-13 - Codex Atishay browser media upload boundary

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Make selected WAV and PNG files travel through the minimal browser demo as validated session-scoped media while retaining the explicit mock perception boundary.
- Output: Added base64 upload decoding, size/type validation, temporary session storage, browser file encoding and focused tests.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 9 passed; full suite verification follows; Ruff passed for owned paths.
- Backend/dependencies: Existing FastAPI WebSocket stack; no dependency or contract change. Microphone remains mock.

## 2026-09-13 - Codex Atishay browser microphone capture

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Replace the mock microphone button with browser-side PCM-to-WAV capture through the existing validated session upload route.
- Output: Added getUserMedia capture, 16-bit WAV encoding, stream shutdown and static UI checks.
- Human modifications/review: Awaiting Atishay review.
- Validation: Demo suite 9 passed; Ruff passed for owned paths. Browser permission and device capture were not available for this run.
- Backend/dependencies: Existing browser APIs and FastAPI WebSocket route; no dependency or contract change.

## 2026-09-13 - Codex Atishay endpoint candidate extraction

- Feature origin: The approved AccessFlow Workstream B plan.
- Tool: Codex (current coding session).
- Prompt: Extract internal and trailing pause candidates from activity windows without treating any pause as semantic completion.
- Output: Added timestamped PauseCandidate values and focused tests for short gaps, all-silence input and internal/trailing separation.
- Human modifications/review: Awaiting Atishay and Mridul review.
- Validation: Perception suite 18 passed; Ruff passed for owned paths. WebRTC found a 2.260 s internal and 0.640 s trailing candidate on the pause-correction fixture.
- Backend/dependencies: Existing optional webrtcvad-wheels 2.0.14 local environment; no tracked dependency, lockfile or contract change.

## 2026-09-13 - Codex Atishay feedback and demo recording safeguards

- **Task:** Prepare the owned feedback and presentation artifacts.
- **Changes:** Added a voluntary session worksheet with explicit capture-consent gates and
  a 4m40s demo recording script tied to verified mock/local boundaries.
- **Status:** Documentation checkpoint validated locally; no participant capture or demo
  recording performed.
- **Notes:** Manual browser/device smoke, held-out endpoint quality, engine integration,
  feedback notes and final presentation remain. No shared contract or dependency change.
## 2026-09-13 - Codex Atishay local demo smoke

- **Task:** Verify the browser demo after the documentation checkpoint.
- **Changes:** Served the demo locally and checked the HTTP response and required UI
  markers for getUserMedia, WAV encoding and the demo/mock backend label.
- **Status:** HTTP 200; full suite 61 passed with 2 dependency deprecation warnings.
- **Notes:** Browser-control initialization failed, so permission and physical-device
  microphone capture remain unverified. Temporary server was stopped.
## 2026-09-13 - Codex Atishay held-out generated speech evaluation

- **Task:** Measure fluent, repetition/correction and labeled-pause cases after the
  development fixtures.
- **Changes:** Added generated WAV cases, machine-readable labels/results and a provenance
  check. Ran Faster Whisper base.en CPU INT8 and WebRTC VAD with the fixed local settings.
- **Status:** All three transcripts preserved the intended wording; the labeled 1.2 second
  break was fully overlapped by a 1.980 second candidate with 0.606 IoU.
- **Notes:** Generated voice only; this is not human speech accuracy or endpoint-quality
  evidence. Fixture check passed; no shared contract or dependency change.
## 2026-09-13 - Codex Atishay opt-in local audio demo path

- **Task:** Verify real WAV routing through the browser demo with an existing local model.
- **Changes:** Added an environment-gated LocalPerception delegate, dynamic backend label and
  configuration/test coverage.
- **Status:** Cached Faster Whisper base.en CPU INT8 completed a checked-in WAV through the
  WebSocket route; acknowledgment backend was faster-whisper/cpu-int8 and the controller
  produced an informational final.
- **Notes:** Demo default remains demo/mock for text and image. Browser device capture, live
  vision and non-mock reasoning remain unverified. No shared contract or dependency change.
## 2026-09-13 - Codex Atishay visible local transcript output

- **Task:** Make local audio evidence visible in the browser demo.
- **Changes:** Included the latest observation text in the mock reasoner informational final
  and added a regression assertion.
- **Status:** Demo suite 11 passed; full suite 64 passed; Ruff clean.
- **Notes:** The reasoner remains mock and informational; no action authority or shared
  contract change.
## 2026-09-13 - Codex Atishay presentation content outline

- **Task:** Prepare the content draft for the required presentation template.
- **Changes:** Added an eight-slide outline covering the scenario, architecture, safety,
  measurements, backend labels and remaining gates.
- **Status:** Template-neutral content draft complete; official template and final assembly
  remain.
- **Notes:** All current claims are tied to generated fixtures or offline tests. No
  participant data, source, contract or dependency change.
## 2026-09-13 - Codex Atishay session path isolation

- **Task:** Harden the browser demo media boundary.
- **Changes:** Rooted no-byte fallback paths in the per-session temporary directory and
  added a regression test against a client-supplied private path.
- **Status:** Demo suite 12 passed; full suite 65 passed; Ruff clean.
- **Notes:** No shared contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay local model configuration guard

- **Task:** Fail clearly when the optional local Faster Whisper model path is invalid.
- **Changes:** Added directory validation, a labeled demo/config WebSocket error and
  regression coverage.
- **Status:** Demo suite 14 passed; full suite 67 passed; Ruff clean.
- **Notes:** Default mock mode and valid local mode remain unchanged. No shared contract or
  dependency change.
## 2026-09-13 - Codex Atishay opt-in local Ollama vision path

- **Task:** Add and test an optional local PNG vision backend.
- **Changes:** Added loopback-only Ollama generate provider, LocalPerception backend labeling,
  environment-gated demo routing and mocked success/error tests.
- **Status:** Provider and demo delegate pass; no live Ollama service or vision-quality claim.
- **Notes:** No model download, shared contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay local vision availability check

- **Task:** Check for a local Ollama service before any live vision run.
- **Result:** ollama command not found and loopback port 11434 was closed.
- **Status:** No installation or download attempted; live vision remains unverified.
- **Notes:** No source, contract, dependency or lockfile change.
## 2026-09-13 - Codex Atishay WebSocket media protocol smoke

- **Task:** Verify browser WAV and PNG transport through the session-scoped demo route.
- **Changes:** Added media-received status events with source IDs and end-to-end WebSocket
  regression tests for base64 WAV and PNG payloads.
- **Status:** Demo suite 18 passed; full suite 77 passed; Ruff and git diff --check clean.
- **Notes:** WAV reaches the mock controller final. PNG transport is validated and preserved,
  but the current v0.1 agent requires a paired transcript for a controller final. No shared
  contract, dependency or lockfile change.

## 2026-09-13 - Codex Atishay functional Chrome browser smoke

- **Task:** Verify the local demo using Chrome and its actual text, WAV and PNG controls.
- **Result:** Connected WebSocket, text acknowledgment/final, WAV media status/final and PNG
  media status plus paired transcript final were observed. No horizontal overflow was observed.
- **Status:** Functional browser matrix passed; physical microphone/device capture, pixel
  inspection and separate console capture remain unverified.
- **Dependency note:** Local-only websockets 17.1 was installed because committed Uvicorn
  dependencies did not provide WebSocket support. No pyproject or lockfile change was made;
  propose this dependency to the shared owner.
## 2026-09-13 - Codex Atishay synthetic microphone browser smoke

- **Task:** Exercise browser microphone start, stop, WAV encoding and upload without recording
  a person.
- **Result:** Chrome's synthetic device entered recording state; stop uploaded WAV and the
  session emitted media_received=audio and the mock final.
- **Status:** Synthetic microphone path passed. Physical device permission/capture, pixel
  inspection and separate console capture remain unverified.
- **Notes:** No participant or physical recording was used. No source, contract, dependency or
  lockfile change.

## 2026-09-14 - Codex Atishay multimodal end-to-end evidence

**Task:** Prioritize multimodal end-to-end coverage for the hidden scenario weighting.

**Changes:** Replaced the browser's inline recorder Blob with the demo-served
recorder-worklet.js, added the route and focused test, and added a combined audio-plus-image
Agent test using injected local ASR and vision providers. Fresh Chrome CDP evidence covered text,
synthetic microphone, WAV, PNG plus paired transcript, clean console output and no overflow.

**Status:** Full suite 81 passed; demo suite 22 passed; perception suite 43 passed; Ruff and
git diff --check clean. Evidence is functional synthetic/injected coverage only; physical
microphone, pixel inspection, live ASR/vision quality and non-mock reasoning remain unverified.

**Notes:** origin/mridul/engine was fetched at ad04bca for review. Branch remains
atishay/perception; no engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay image-only controller gap

**Task:** Extend multimodal evidence to image-only informational planning.

**Changes:** Added a strict expected-failure demo test for a frame-only Agent session and an
additive proposal for an informational evidence basis that preserves write authorization gates.

**Status:** Full suite 81 passed, 1 strict xfailed; demo suite 22 passed, 1 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean. The xfail is the known current
controller integration gap, not a perception or transport failure.

**Notes:** Branch remains atishay/perception. No engine, contract, lockfile or dependency manifest
changes were made.

## 2026-09-14 - Codex Atishay live local audio plus injected vision

**Task:** Strengthen the multimodal end-to-end evidence with a real local audio backend.

**Changes:** Ran synthetic_speech.wav through the cached Faster Whisper base.en CPU INT8 model,
paired it with a validated PNG and injected vision provider in one Agent context, and added
docs/feedback/MULTIMODAL_E2E.md.

**Status:** The local ASR transcript and injected frame observation reached one context and produced
an informational final in 3.222 seconds. Live vision and non-mock reasoning remain unverified.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal ordering coverage

**Task:** Broaden multimodal end-to-end coverage across input arrival orderings.

**Changes:** Parameterized the demo Agent-context test for audio-then-image and image-then-audio.
Both sequences pass while the image-only controller gap remains an explicit strict xfail.

**Status:** Full suite 82 passed, 1 strict xfailed; demo suite 23 passed, 1 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal revision and frame retention

**Task:** Cover revised audio hypotheses alongside image evidence in one Agent context.

**Changes:** Added a demo regression for two audio revisions and one PNG. Revision 1 replaces
revision 0 while frame provenance remains available to the reasoner.

**Status:** Full suite 83 passed, 1 strict xfailed; demo suite 24 passed, 1 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay browser local-ASR multimodal run

**Task:** Connect local ASR evidence to the real browser transport.

**Changes:** Ran Chrome against the demo with the cached Faster Whisper base.en CPU INT8 snapshot,
uploaded synthetic_speech.wav, verified the faster-whisper/cpu-int8 acknowledgment and recognized
transcript, then uploaded a PNG and follow-up text in the same session.

**Status:** Browser mixed evidence passed with no console/page errors or horizontal overflow. Image
and text remained demo/mock; live vision and non-mock reasoning remain unverified.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay changed-frame integration gap

**Task:** Expose active-frame replacement for multimodal scenarios.

**Changes:** Added a strict expected-failure demo example proving frame 2 reaches the reasoner while
frame 1 remains in the current view. The engine branch's integrated behavior was inspected; no
engine-owned files were changed.

**Status:** Full suite 83 passed, 2 strict xfailed; demo suite 24 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** The xfail is an engine integration boundary, alongside the existing image-only response
xfail.

## 2026-09-14 - Codex Atishay visible multimodal reasoner context

**Task:** Make the demo's informational response expose retained audio and image context.

**Changes:** DemoReasoner now appends prior observations to the latest-input response. Chrome
verified a WAV, PNG and text sequence whose final visibly included both prior modalities.

**Status:** Full suite 84 passed, 2 strict xfailed; demo suite 25 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** The response remains a labeled mock informational result; no engine, contract, lockfile
or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay combined WebSocket context regression

**Task:** Protect the browser-observed combined multimodal response with automated coverage.

**Changes:** Added a WebSocket test for validated WAV, PNG and follow-up transcript in one session.
It asserts received source IDs and audio/image context in the final response.

**Status:** Full suite 85 passed, 2 strict xfailed; demo suite 26 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** One transient Starlette teardown cancellation occurred during a full run; a clean rerun
passed. No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay physical microphone browser smoke

**Task:** Verify the browser microphone path against the machine's present audio input after the
fake-device smoke.

**Changes:** No repository source or dependency changes. An isolated headless Chrome run omitted
the fake audio-device flag, entered getUserMedia recording from the present Microphone Array,
loaded the served AudioWorklet, stopped cleanly, uploaded a WAV through the session WebSocket and
observed media_received=audio plus the mock informational final.

**Status:** Physical microphone permission and capture passed. Pixel inspection remains unverified;
live vision quality, human speech accuracy and non-mock reasoning remain open.

**Notes:** The run used an isolated Chrome profile and temporary CDP harness; no fake audio-device
flag was used and no person or recording was stored in the repository.

## 2026-09-14 - Codex Atishay WebSocket multimodal revision retention

**Task:** Verify that the browser transport preserves the latest speech revision beside image
evidence in one session.

**Changes:** Added a demo WebSocket regression that uploads a validated WAV, sends two transcript
revisions for one utterance, uploads a PNG and submits follow-up text. It asserts the older speech
hypothesis is absent while the revised text and image context remain visible.

**Status:** Demo suite 27 passed, 2 strict xfailed; full suite 86 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay multimodal write safety

**Task:** Verify that final image evidence cannot authorize a write while speech remains partial.

**Changes:** Added a demo Agent regression with an explicit write manifest and proposal. A partial
spoken request followed by a final injected image leaves correction_pending true and invokes no
write tool.

**Status:** Demo suite 28 passed, 2 strict xfailed; full suite 87 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay WebSocket image-first ordering

**Task:** Verify that image evidence remains available when it arrives before audio in one browser
session.

**Changes:** Added a demo WebSocket regression that sends a validated PNG before a validated WAV
and asserts that the later audio final retains image context and both source IDs.

**Status:** Demo suite 29 passed, 2 strict xfailed; full suite 88 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay malformed image recovery

**Task:** Verify malformed PNG input is recoverable without terminating the browser session.

**Changes:** Added a demo WebSocket regression that sends invalid base64 PNG content, asserts the
labeled demo/input error, then submits text successfully through the same session.

**Status:** Demo suite 30 passed, 2 strict xfailed; full suite 89 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay image-only write safety

**Task:** Verify that image evidence alone cannot authorize a state-changing write.

**Changes:** Added an owned Agent regression with a vision result that resembles a booking request,
an explicit write manifest and a write proposal. With no spoken request, correction_pending remains
true and the executor records no call or effect.

**Status:** Demo suite 31 passed, 2 strict xfailed; full suite 90 passed, 2 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay changed-frame WebSocket reproducer

**Task:** Pin stale image evidence at the browser transport boundary.

**Changes:** Added a strict expected-failure regression that sends two PNG frames through one WebSocket
session, then sends text and asserts the final context contains only the active frame.

**Status:** Full suite 90 passed, 3 strict xfailed; demo suite 31 passed, 3 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** The failure is intentional until the engine integration removes the prior active frame.
No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay vision backend failure

**Task:** Verify configured vision failures are surfaced without a false informational response.

**Changes:** Added an owned Agent regression with a failing injected vision backend. The image event
produces a backend_failure error with no final response.

**Status:** Full suite 91 passed, 3 strict xfailed; demo suite 32 passed, 3 strict xfailed;
perception suite 43 passed; Ruff and git diff --check clean.

**Notes:** This verifies failure propagation only and makes no live vision quality claim. No engine,
contract, lockfile or dependency manifest changes were made.

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


## 2026-09-14 - Codex Atishay upload cleanup and backend identity

**Task:** Close two multimodal demo boundary ambiguities after the end-to-end coverage pass.

**Changes:** Added an audio backend identity on LocalPerception so injected ASR is not presented as Faster Whisper, and removed temporary WAV files when post-header PCM validation rejects the upload. Added focused tests for truthful labeling and cleanup.

**Status:** Full suite 101 passed, 3 strict xfailed; owned demo and perception suites 85 passed, 3 strict xfailed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.

## 2026-09-14 - Codex Atishay combined configured multimodal route

**Task:** Add route-level evidence that configured local audio and vision providers can contribute to one multimodal session.

**Changes:** Strengthened the WebSocket regression to call DemoPerception.from_environment with both modality settings, substituting only the ASR implementation for deterministic text. It verifies validated WAV and PNG transport, backend labels, source IDs, both observations in one reasoner view and informational output.

**Status:** Full suite 102 passed, 3 strict xfailed; owned demo and perception suites 86 passed, 3 strict xfailed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.

## 2026-09-14 - Codex Atishay ASR failure multimodal recovery

**Task:** Verify that an audio backend failure can recover into a later multimodal request through the demo WebSocket.

**Changes:** Added a route regression that emits backend_failure for ASR, then accepts a validated PNG and spoken follow-up in the same session. It verifies retained image evidence and informational output; the test waits for the actual image observation to avoid assuming worker completion order.

**Status:** Full suite 103 passed, 3 strict xfailed; owned demo and perception suites 87 passed, 3 strict xfailed; Ruff, compilation and git diff --check clean. One existing WebSocket teardown cancellation was transient: the affected test passed in three isolated reruns and the subsequent full suite passed. No engine, contract, dependency or lockfile change.

## 2026-09-14 - Codex Atishay live local-ASR loopback-vision route

**Task:** Capture a stronger mixed multimodal runtime result through the served WebSocket.

**Run:** Enabled the cached Faster Whisper base.en CPU INT8 snapshot and configured OllamaVisionProvider against a local loopback protocol service. A validated WAV and PNG passed through one session, and a follow-up text final retained both observations.

**Result:** 1.326 seconds; Faster Whisper returned the known fixture sentence, the provider request checked model, safety prompt, PNG bytes and stream=false, and the final was informational. Vision was a deterministic loopback response and reasoning remained the demo mock; this is not live vision-quality or non-mock-reasoning evidence.

## 2026-09-14 - Codex Atishay PNG IDAT integrity

**Task:** Prevent CRC-valid but corrupt PNG compression streams from reaching the vision backend.

**Changes:** Added concatenated IDAT zlib stream validation with complete-stream and trailing-data checks, plus a focused malformed-IDAT regression. Pixel data is still not decoded or interpreted.

**Status:** Full suite 104 passed, 3 strict xfailed; owned demo and perception suites 88 passed, 3 strict xfailed; Ruff, compilation and git diff --check clean. No engine, contract, dependency or lockfile change.
2026-09-14: Multimodal policy boundary added on atishay/perception: image observations now remain context-only for speech correction and backchannel matching, with a focused regression. Validation: 105 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Hardened the owned demo WebSocket parser against non-object browser messages and payloads; malformed multimodal input now returns a recoverable demo/input error. Validation: 107 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Corrected the demo backend label fallback so unidentified injected audio is reported as local/unknown-audio rather than Faster Whisper; known Faster Whisper identity remains explicit. Validation: 108 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Hardened OllamaVisionProvider against syntactically valid non-object JSON roots; list and null responses now produce a classified invalid JSON shape error. Validation: 110 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Added configured WebSocket coverage for malformed Ollama JSON: a list response becomes backend_failure and a later transcript remains usable. Validation: 111 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Added OllamaVisionProvider timeout coverage; transport TimeoutError normalizes to the stable RuntimeError boundary used by multimodal recovery. Validation: 112 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Added WebSocket session-reset isolation coverage: a fresh connection cannot inherit the prior session's audio or image context. Validation: 113 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Added a pre-decode base64 length guard for the demo's 8 MiB raw-media budget; oversized multimodal uploads are rejected without materialization. Validation: 114 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Added configured WebSocket coverage for vision transport timeout recovery; actual OllamaVisionProvider failure emits backend_failure and a later transcript completes. Validation: 115 passed, 3 strict xfailed; no protected files changed.


2026-09-15: Preserved browser multimodal source timing in the owned demo path: event timestamps,
audio speech bounds and frame observation timing now have focused regressions. Validation: 117 passed,
3 strict xfailed; no protected files changed.


2026-09-15: Added multimodal vision quota recovery coverage and a strict conflicting-frame example with
an additive controller proposal. Validation: 119 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Browser timestamp transport aligned with the event envelope and legacy payload fallback
retained. Validation: 119 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Verified delayed audio remains in multimodal context when a newer frame arrives; added a
passing cross-modal race regression. Validation: 120 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Added direct invalid-PNG upload cleanup regression. Validation: 121 passed, 4 strict
xfailed; no protected files changed.


2026-09-15: Added truthful unknown-vision labeling and regression coverage for identity-free
injected adapters. Validation: 122 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Preserved structured HTTP quota details from OllamaVisionProvider, including a 429 JSON
error body, and verified the classified provider failure boundary. Validation: 123 passed, 4 strict
xfailed; no protected files changed.


2026-09-15: Added WebSocket-level HTTP 429 vision quota recovery evidence. The provider error body
becomes backend_failure and the same session accepts a later transcript. Validation: 124 passed,
4 strict xfailed; no protected files changed.


2026-09-15: Added a slow-image worker responsiveness regression. The event loop remains usable while a
vision provider is blocked. Validation: 125 passed, 4 strict xfailed; no protected files changed.


2026-09-15: Added a slow-ASR worker responsiveness regression alongside the existing slow-image check.
Both perception paths keep the event loop responsive. Validation: 126 passed, 4 strict xfailed; no
protected files changed.


2026-09-15: Hardened browser rendering of untrusted multimodal output with textContent-backed DOM
nodes and extended the UI regression. Validation: 126 passed, 4 strict xfailed; no protected files
changed.


2026-09-15: Moved browser base64 media decoding and WAV/PNG validation to a worker-backed receive path.
Focused media/recovery coverage and full validation: 126 passed, 4 strict xfailed; no protected files
changed.


2026-09-15: Added malformed provider-output guards for blank or non-string ASR and vision results.
Validation: 128 passed, 4 strict xfailed; no protected files changed.

2026-09-15: Used a read-only subagent review to audit the bounded multimodal context diff. Addressed
its findings by truncating the item that reaches the remaining capacity, preserving newest evidence,
and adding exact-bound, oversized-item and request-completeness assertions. Validation: 129 passed,
4 strict xfailed; no protected files changed.

2026-09-15: Used a read-only subagent audit to identify the missing syntactically invalid vision JSON
scenario. Added direct provider coverage and WebSocket recovery coverage while preserving the existing
classified failure boundary. Validation: 131 passed, 4 strict xfailed; no protected files changed.

2026-09-15: Added a truthful backend-label regression after auditing injected vision provenance. The
demo now requires an explicit ollama/ backend identity before exposing an Ollama model label.
Validation: 132 passed, 4 strict xfailed; no protected files changed.

2026-09-15: Used a subagent design review to validate an opt-in LocalPerception deadline and its
non-forcible thread-cancellation limitation. Implemented modality-specific timeout classification,
direct audio/image tests, configuration validation, and WebSocket recovery. Validation: 141 passed,
4 strict xfailed; no protected files changed.

2026-09-15: Applied the subagent-reviewed cancellation cleanup fix by moving LocalPerception's
scheduling yield inside its child-task cleanup guard. Added a regression for observer cancellation
while a synchronous worker continues to completion. Validation: 142 passed, 4 strict xfailed; no
protected files changed.

2026-09-15 verification: Added a WebSocket regression for vision failure recovery into a later valid
image plus audio session. Both modalities and their source identities remain in the final context.
Full validation: 143 passed, 4 strict xfailed; demo 60 passed plus 4 strict xfailed; perception 67
passed. No protected files changed.

2026-09-15 verification: Implemented the subagent-reviewed bounded multimodal admission slice:
independent audio/image workers coalesce obsolete work, preserve session identity, suppress stale
results, and close on demo shutdown. Added concurrency, revision, rapid-frame and session-isolation
regressions. Full validation: 149 passed, 4 strict xfailed; demo 61 passed plus 4 strict xfailed;
perception 72 passed. No protected files changed.

2026-09-15 verification: Used a read-only subagent audit to identify missing stale provider-failure
coverage. Added direct exception and timeout suppression tests and a recovered multimodal WebSocket
regression. Full validation: 152 passed, 4 strict xfailed; demo 62 passed plus 4 strict xfailed;
perception 74 passed. No protected files changed.

2026-09-15 verification: Applied the subagent audit finding for cross-session pending isolation. Local
audio/image workers are now created per session, with a regression for competing active and pending
frames across two sessions. Full validation: 153 passed, 4 strict xfailed; demo 62 passed plus 4 strict
xfailed; perception 75 passed. No protected files changed.
2026-09-15 verification: Used two read-only subagent audits to identify the next multimodal gaps. Routed
controller events, media statuses and recoverable input errors through one WebSocket sender and added a
non-overlap regression. Added a WebSocket composition regression using the real LocalPerception model-path
branch with a deterministic factory and the real OllamaVisionProvider HTTP request. Full validation: 155
passed, 4 strict xfailed; demo 64 passed plus 4 strict xfailed; perception 75 passed. No protected files
changed.
2026-09-15 verification: Added a concurrent WebSocket session-isolation regression. Two live sessions
remain open together while one receives an image and the other completes a transcript; the second final
contains no inherited image context. Full validation: 156 passed, 4 strict xfailed; demo 65 passed plus
4 strict xfailed; perception 75 passed. No protected files changed.
2026-09-16 verification: Used two read-only subagent audits to identify a shutdown admission race and
an unintegrated timing boundary. Fixed the owned lifecycle race: LocalPerception closes admission before
late validation can register workers, and DemoPerception ignores work after close. The demo sender now
terminates cleanly when the peer is closed. Added parameterized audio/image validation-race and
post-close regressions for all DemoPerception modalities, plus a strict timing-channel example. Extended
the configured WebSocket composition regression to carry text, WAV and PNG together with timing, identity,
revision and backend assertions. Full validation: 162 passed, 5 strict xfailed; demo 68 passed plus 4
strict xfailed; perception 78 passed. No protected files changed.
2026-09-16 verification: Added a route-level cleanup regression proving valid uploaded WAV and PNG files
are present inside the live session directory and removed after WebSocket disconnect. Full validation: 163 passed,
5 strict xfailed; demo 69 passed plus 4 strict xfailed; perception 78 passed. No protected files changed.
2026-09-16 verification: Extended the configured WebSocket composition regression with two WAV hypotheses
for one utterance. It now proves the later revision and timing replace the earlier audio while text and PNG
remain in the same final context. Focused and full validation remained green; no protected files changed.
2026-09-16 verification: Extended concurrent WebSocket session isolation to carry image and audio in one
session while a second open session completes fresh text. The second session receives neither modality;
focused validation passed and no protected files changed.
2026-09-16 verification: Added configured-route identity assertions: the retained text, corrected audio and
image observations each carry a distinct generated envelope event ID while their source IDs remain stable.
Focused validation passed; no protected files changed.
2026-09-16 verification: Added configured WebSocket audio recovery coverage: a valid PNG remains in context
while revision 0 fails, revision 1 recovers for the same utterance, and only the corrected audio reaches the
final context. Full validation: 164 passed, 5 strict xfailed; demo 70 passed plus 4 strict xfailed;
perception 78 passed. No protected files changed.
2026-09-16 verification: Promoted the timing-policy example from strict expected failure and added a final-transcript
guard proving an acoustic pause cannot override completion. HeuristicTurnPolicy now accepts optional ActivitySummary
metadata; shared engine/controller wiring remains pending. Full validation: 166 passed, 4 strict xfailed; demo 70
passed plus 4 strict xfailed; perception 80 passed. No protected files changed.
2026-09-16 verification: Made the conflicting-frame strict example deterministic by waiting for frame one to reach the
reasoner before submitting frame two. It still fails only at the controller conflict-state assertion; no source,
contract or protected files changed.
2026-09-16 verification: Corrected the conflict reproducer to use two valid content-distinct PNG uploads and assert
the injected Tuesday/Wednesday captions. With --runxfail it now reaches the expected write-safety assertion, proving
the controller gap is observable. No source, contract or protected files changed.
2026-09-16 verification: Reviewed origin/mridul/engine at 919ed27 in a disposable overlay with the current
owned demo/perception paths. Targeted active-frame replacement and image-only informational tests pass upstream;
the conflict case is blocked before planning because the prior frame is removed. Recorded the required
pre-replacement comparison/provenance seam; no protected files changed.
2026-09-16 verification: Opened the existing browser media, console and microphone captures directly. The shown
viewport has no visible clipping, overlap or broken text. The captures are dated 13–14 September, so fresh
current-HEAD full-page visual inspection remains open. No source or protected files changed.
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
