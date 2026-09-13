# AccessFlow

A conversational agent prototype for unfinished speech, corrections and safe mock actions.
Samsung PRISM Theme 5; Mridul + Atishay. **Bootstrap in progress, not an evaluated submission.**

## Start here

- Atishay and his AI: [ATISHAY_START_HERE.md](ATISHAY_START_HERE.md)
- Current verified status: [docs/STATUS.md](docs/STATUS.md)
- Agreed plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Interfaces and ownership: [docs/CONTRACT.md](docs/CONTRACT.md), [AGENTS.md](AGENTS.md)
- Daily notes: [docs/handoffs/](docs/handoffs/)

## Current progress

### Checkpoint 1 - 13 September 2026: perception foundation

Atishay's Workstream B has started on `atishay/perception`.

- Added `LocalPerception` for transcript pass-through and raw PCM WAV validation.
- Preserved utterance IDs, revisions, source event IDs and speech timestamps.
- Added an injected ASR seam for deterministic tests and a lazy Faster Whisper CPU INT8
  path that requires an already-installed local model.
- Kept blocking WAV and transcription work off the event loop with `asyncio.to_thread`.
- Image input is explicitly refused until a real replaceable vision provider is supplied;
  no canned caption is treated as perception.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest -q  -> 21 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                             -> All checks passed
```

The tests prove contract and adapter behavior only. No live ASR, vision quality, hosted
backend result or hardware latency is claimed yet. Next: turn timing policies, partial
transcript cases, a replaceable vision adapter and the minimal fake-agent demo.

## Checkpoint 2 - 13 September 2026: turn policy baseline

Added the first synchronous `HeuristicTurnPolicy` under Atishay's owned workstream.

- Final speech completes only when the observation is marked final; partial speech always continues.
- Explicit markers such as "actually" and "I mean" become `possible_correction` decisions.
- Repeated words remain ordinary speech unless a correction marker is present.
- Short acknowledgments such as "mm-hmm" become `backchannel` decisions.
- Older revisions cannot complete a turn when a newer observation is already present.
- The policy is deterministic, synchronous and model-free, so it does not block the dispatcher.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 13 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/turn_policy tests/perception
                                                               -> All checks passed
```

The current contract has no timer or silence event, so this baseline does not claim acoustic
pause detection. Next: a replaceable PNG vision adapter with frame identity and evidence
metadata, followed by the minimal fake-agent demo.

## Checkpoint 3 - 13 September 2026: replaceable vision seam

Added the first image path to `LocalPerception` without changing the shared v0.1 contract.

- Validates the PNG signature, IHDR chunk and non-zero dimensions before provider work.
- Uses an injected vision provider so tests remain deterministic and future backends stay replaceable.
- Emits `Observation(modality="image")` with `frame_id`, source event ID, revision 0 and frame timestamp.
- Refuses missing providers and malformed images instead of generating a canned caption.
- Keeps validation and provider execution off the event loop.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 15 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                               -> All checks passed
```

This proves the adapter seam and provenance behavior only. No live vision model quality or
hardware latency is claimed. Next: add a minimal fake-agent demo that renders output events
without duplicating authoritative engine state.

## Checkpoint 4 - 13 September 2026: minimal fake-agent demo

Added a small FastAPI WebSocket demo under `demo/` that uses the existing queue-based
controller and renders serialized `OutputEvent` snapshots.

- Text, WAV/mock-audio, microphone/mock-audio and PNG/mock-image controls are visible in the browser.
- Browser messages are translated into typed v0.1 events before entering the controller.
- The frontend renders returned state snapshots and does not maintain slots, planning or action state.
- Every mock input and response is labeled `demo/mock`; this demo is not live ASR or vision evidence.
- The WebSocket smoke test confirms a transcript produces both acknowledgment and final output events.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/demo -q  -> 6 passed
uv run --python 3.12 --extra dev ruff check demo tests/demo
                                                       -> All checks passed
```

FastAPI's test client currently emits dependency deprecation warnings; they do not fail the
suite. Next: add real WAV fixture provenance and timing/VAD integration while retaining the
mock demo as an explicit development mode.
## Checkpoint 5 - 13 September 2026: audio fixture provenance

Added a deterministic synthetic WAV fixture at `tests/fixtures/audio/synthetic_tone.wav`.

- The fixture is generated locally with Python's standard `wave`, `struct` and `math` libraries.
- It is mono PCM, 16-bit, 16 kHz and 0.5 seconds long; it contains a 440 Hz tone, not speech.
- Its provenance, intended development-only use and SHA-256 are recorded in `docs/feedback/PROVENANCE.md`.
- A perception test validates the checked-in file through the same raw WAV route used by `LocalPerception`.
- No participant voice, third-party recording or ASR quality claim is attached to this asset.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 16 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                               -> All checks passed
```

Next: connect a real local transcription backend to an explicitly installed model and add
speech-activity timing behind a replaceable adapter, with backend and hardware measurements.
## Checkpoint 6 - 13 September 2026: PCM and activity baseline

Added an isolated PCM loader and fixed-window energy activity helper in
`src/accessflow/perception/audio.py`.

- Downmixes mono or stereo PCM WAV input and converts it to a requested sample rate.
- Exposes frame start/end times and RMS levels for deterministic timing experiments.
- Keeps this as an energy baseline, not a speech classifier or clinical VAD.
- Covers the checked-in tone fixture, stereo resampling, silence/tone boundaries and invalid configuration.
- Adds no dependency or shared-contract change; Checkpoint 8 later replaced the deprecated audioop path with standard-library primitives.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 21 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                               -> All checks passed
```

The CP6 baseline used audioop; Checkpoint 8 removed that deprecation from the PCM path. No live ASR, speech VAD, vision quality, hosted backend or hardware latency is claimed. Next: connect an explicitly installed local ASR model and measure backend timing on declared hardware.
## Checkpoint 7 - 13 September 2026: local ASR seam

Hardened the optional Faster Whisper path in `LocalPerception` without downloading models during a scenario.

- Requires an existing local model directory before starting inference.
- Adds a factory seam for deterministic tests and future backend substitution.
- Requests `device="cpu"` and `compute_type="int8"`, then aggregates returned segment text.
- Keeps the model import, load and transcription work off the event loop.
- Labels the output `faster-whisper/cpu-int8`; the factory tests are not a live model benchmark.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 23 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                               -> All checks passed
```

At the time of this checkpoint no Faster Whisper weights had been evaluated; Checkpoint 9 records the first local measurement. Next: measure
an explicitly installed model on declared hardware, then connect timing decisions to the
available event contract without making every pause a completion.

## Checkpoint 8 - 13 September 2026: dependency-free PCM backend

Replaced the deprecated Python 3.12 audioop calls in the owned PCM path with small
standard-library decoder, stereo downmixer, linear resampler and RMS helpers.

- Supports 1-, 2-, 3- and 4-byte PCM sample widths.
- Keeps the existing mono/stereo loading and target-rate behavior without adding a dependency
  or changing the shared contract.
- Adds focused coverage for all supported sample widths.
- Keeps the activity output explicitly labeled as an energy baseline, not a speech classifier.

Evidence from this checkpoint:

~~~text
uv run --python 3.12 --extra dev pytest tests/perception/test_audio.py -q  -> 9 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                                         -> All checks passed
~~~

This removes the current audioop deprecation warning from the PCM path. It does not establish
production resampling quality or acoustic VAD quality. Next: measure an explicitly installed
local ASR model on declared hardware.

## Checkpoint 9 - 13 September 2026: local ASR timing measurement

Ran the installed Faster Whisper base.en model through the local CPU INT8 path on the
checked-in WAV fixture.

- Hardware: Intel Core Ultra 5 125H, 16 GB installed RAM, Python 3.12.10.
- Model/runtime: Systran/faster-whisper-base.en, snapshot 3d3d5dee26484f91867d81cb899cfcf72b96be6c, faster-whisper 1.2.1.
- Audio duration: 0.500 s; model load: 0.464 s; inference: 0.677 s; backend realtime factor: 1.354. LocalPerception.observe elapsed 1.233 s, realtime factor 2.466.
- The model returned an empty transcript and detected English, which is expected for the
  synthetic 440 Hz tone. This is timing/backend evidence, not speech recognition quality.

The full measurement record is in docs/feedback/ASR_MEASUREMENTS.md. The model remains in the
ignored models directory and is not committed.

## Checkpoint 10 - 13 September 2026: illustrative speech ASR run

Added a locally synthesized, non-participant speech fixture and ran it through
LocalPerception with the installed Faster Whisper base.en CPU INT8 backend.

- Fixture: 5.304 s mono PCM, 16-bit, 22.05 kHz; generated with the installed Windows speech synthesizer.
- SHA-256: B42354F90462A08AD23DF835256289116DEFDE4287AB2AC3D9D3CF2E87BCD5E6.
- Transcript: “My screen keeps flickering after the update. Book Wednesday at 5.”
- Adapter elapsed time: 5.874 s; realtime factor: 1.108.
- This is one illustrative generated-voice case, not a held-out accuracy benchmark or a claim
  about participant speech.

The fixture and ASR details are recorded in docs/feedback/PROVENANCE.md and
docs/feedback/ASR_MEASUREMENTS.md.

## Checkpoint 11 - 13 September 2026: timing-only activity summary

Added an offline timing summary over the energy frames without changing the shared v0.1
contract or treating a pause as turn completion.

- Reports contiguous active windows, active duration and leading/trailing silence.
- Exposes pause_detected only as an acoustic timing signal; all-silence input is not a pause after speech.
- Adds an additive contract proposal for carrying timing metadata into a future adapter.

Evidence from this checkpoint:

~~~text
uv run --python 3.12 --extra dev pytest tests/perception/test_audio.py -q  -> 13 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                                         -> All checks passed
~~~

The current engine still consumes the v0.1 observation contract and has no timer event.
This is an offline timing baseline, not acoustic VAD quality or a semantic completion claim.
## Checkpoint 12 - 13 September 2026: optional WebRTC activity backend

Added a lazy optional WebRTC VAD adapter over normalized 16-bit PCM frames, with injected
detector tests and no shared contract change.

- Accepts 8, 16, 32 or 48 kHz audio and 10, 20 or 30 ms frames.
- Keeps acoustic activity separate from semantic turn completion and tool safety.
- Compared the adapter with the energy baseline on both provenance-tracked fixtures.
- On the tone, both methods marked 25/25 frames active, showing that activity detection alone
  is not evidence of speech.
- On generated speech, WebRTC marked 189/265 frames active in two broad windows and left
  0.640 s trailing silence; the energy baseline marked 138/266 frames across fragmented windows.

The comparison is an illustrative backend observation, not a VAD quality benchmark. Details are
in docs/feedback/VAD_MEASUREMENTS.md. The local environment uses webrtcvad-wheels 2.0.14;
the shared lockfile remains unchanged pending review.

## Checkpoint 13 - 13 September 2026: pause-and-correction fixture

Added a second generated speech fixture containing “Book Tuesday.”, a deliberate 1.5 second
break, and “Actually, Wednesday at five.”

- Fixture: 6.024 s mono PCM, 16-bit, 22.05 kHz; SHA-256
  49B0B26FD1EBCAE0772B2559A4ABA3782444F59FAB7E7E7038122F06157C872B.
- Faster Whisper returned “Book Tuesday. Actually, Wednesday at 5.” in 1.334 s
  (realtime factor 0.221).
- WebRTC VAD produced three windows around the spoken portions and 0.640 s trailing silence.
- The timing and transcript are illustrative development evidence; this fixture is not held out.

## Checkpoint 14 - 13 September 2026: browser media upload boundary

Extended the minimal demo to upload selected WAV and PNG bytes through the WebSocket route.

- The server decodes base64 payloads, enforces an 8 MiB limit and validates RIFF/WAV or PNG headers.
- Uploaded files are materialized in a per-session temporary directory and removed with the session.
- The existing typed AudioEvent and FrameEvent routes receive the materialized paths.
- The browser microphone button remains explicitly mock; selected-file upload is real transport only.
- The demo still uses demo/mock perception and makes no live ASR or vision claim.

Evidence from this checkpoint:

~~~text
uv run --python 3.12 --extra dev pytest tests/demo -q  -> 9 passed
uv run --python 3.12 --extra dev ruff check demo tests/demo
                                                       -> All checks passed
~~~

Python 3.11 and `uv` are required:

```powershell
uv sync --extra dev
uv run pytest tests/test_contract.py
```

This is the canonical repository root. Organizer PDFs and prior research live outside
the repository in `../sources` and `../research`. Do not commit credentials, private
recordings or organizer materials without checking redistribution permission.

The internal protocol is v0.1, **not Samsung's unpublished wire schema**. Offline fakes
prove contracts and orchestration only. No live ASR, vision quality, official-kit score,
hardware latency or accessibility benefit is claimed by passing those tests.

The shared GitHub remote is being set up at the user's request. Registration, final
submission tag and submission are separate human steps. No API credentials are required
for contract tests.
