# Local ASR measurements

## 2026-09-13 - Faster Whisper base.en CPU INT8

- Backend: Faster Whisper 1.2.1
- Model: Systran/faster-whisper-base.en
- Local snapshot: 3d3d5dee26484f91867d81cb899cfcf72b96be6c
- Device: CPU, Intel(R) Core(TM) Ultra 5 125H
- Installed RAM: 16,573,128,704 bytes (about 15.43 GiB)
- Python: 3.12.10
- Compute type: int8
- Fixture: tests/fixtures/audio/synthetic_tone.wav
- Fixture duration: 0.500 seconds
- Model load time: 0.464 seconds
- Inference time: 0.677 seconds
- Realtime factor: 1.354 (backend call only)
- LocalPerception.observe elapsed time: 1.233 seconds
- LocalPerception.observe realtime factor: 2.466
- Detected language: en
- Transcript: empty string

The fixture is a deterministic 440 Hz tone and contains no speech. The empty transcript is
therefore expected. The direct backend call establishes that the installed local backend loads and completes
on the declared CPU. A second pass through LocalPerception.observe completed in 1.233 seconds, including adapter validation, model initialization and inference. It does not measure speech accuracy,
acoustic VAD quality or user-perceived latency.

The model files were downloaded into the ignored models directory and are not part of the
repository. Future speech measurements must use consented or openly licensed fixtures with
their provenance recorded before any quality claim.

## 2026-09-13 - Faster Whisper base.en on generated speech

- Backend: Faster Whisper 1.2.1 through LocalPerception.observe
- Model: Systran/faster-whisper-base.en, snapshot 3d3d5dee26484f91867d81cb899cfcf72b96be6c
- Device: CPU, Intel(R) Core(TM) Ultra 5 125H
- Python: 3.12.10
- Compute type: int8
- Fixture: tests/fixtures/audio/synthetic_speech.wav
- Fixture format: 1 channel, 16-bit PCM, 22,050 Hz
- Fixture duration: 5.304 seconds
- Adapter elapsed time: 5.874 seconds
- Realtime factor: 1.108
- Transcript: My screen keeps flickering after the update. Book Wednesday at 5.

This is a single generated-voice development case. The transcript matches the known script
apart from the final number wording. It is useful for checking the local seam and a timing
observation, but it is not a held-out accuracy result or a representative speech benchmark.
