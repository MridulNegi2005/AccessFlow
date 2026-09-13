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

## 2026-09-13 - WebRTC VAD and Faster Whisper on pause-and-correction speech

- Fixture: tests/fixtures/audio/synthetic_pause_correction.wav
- Fixture duration: 6.024 seconds; source format 1 channel, 16-bit PCM, 22,050 Hz
- SHA-256: 49B0B26FD1EBCAE0772B2559A4ABA3782444F59FAB7E7E7038122F06157C872B
- WebRTC settings: aggressiveness 2, 20 ms frames, normalized to 16 kHz
- Energy baseline: 93/302 active frames across eight fragmented windows
- WebRTC VAD: 139/301 active frames across three windows; 0.640 seconds trailing silence
- Faster Whisper base.en through LocalPerception.observe: 1.334 seconds; realtime factor 0.221
- Transcript: Book Tuesday. Actually, Wednesday at 5.

The source script includes a generated 1.5 second break between the two utterances. The
observed VAD windows preserve the broad two-part structure, while the transcript preserves
the correction wording. This is a development case, not a held-out accuracy or endpoint
benchmark.

## 2026-09-13 - Held-out generated speech cases

- Backend: Faster Whisper 1.2.1 through LocalPerception.observe
- Model: Systran/faster-whisper-base.en, snapshot 3d3d5dee26484f91867d81cb899cfcf72b96be6c
- Device: CPU, Intel(R) Core(TM) Ultra 5 125H
- Python: 3.12.10
- Compute type: int8

| Case | Duration | Adapter time | RTF | Transcript |
|---|---:|---:|---:|---|
| heldout_fluent.wav | 3.449 s | 3.243 s | 0.940 | Please book a screen repair for Friday at 10. |
| heldout_repetition.wav | 4.724 s | 0.834 s | 0.176 | I want Tuesday, Tuesday, actually Wednesday at 5. |
| heldout_pause.wav | 5.958 s | 0.812 s | 0.136 | I tried restarting already. The screen still flickers. |

The transcripts preserve the repeated phrase, correction and two-part pause case. The
number words were emitted as numerals by the model. These are three generated-voice
cases held out from the earlier local development examples; they do not establish
held-out human speech accuracy, generalization, accessibility benefit or clinical value.
