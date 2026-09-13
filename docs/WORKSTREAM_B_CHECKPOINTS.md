# Workstream B checkpoint history

Preserved from Atishay branch d61d4dc on 13 September 2026.
These are historical checkpoint reports, not current combined test counts.

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
- Adds no dependency or shared-contract change; a maintained audio library should replace `audioop` before Python 3.13 support.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 21 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                                               -> All checks passed
```

Python 3.12 reports the expected `audioop` deprecation warning. No live ASR, speech VAD,
vision quality, hosted backend or hardware latency is claimed. Next: connect an explicitly
installed local ASR model and measure backend timing on declared hardware.
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

No Faster Whisper weights are installed or evaluated in this environment yet. Next: measure
an explicitly installed model on declared hardware, then connect timing decisions to the
available event contract without making every pause a completion.
