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
