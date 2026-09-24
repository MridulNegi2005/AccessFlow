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

## 2026-09-16 - Weighted multimodal inventory audio scoring

- Mode: live local ASR through `LocalPerception.observe`
- Model: Systran/faster-whisper-base.en, snapshot `3d3d5dee26484f91867d81cb899cfcf72b96be6c`
- Device: Intel(R) Core(TM) Ultra 5 125H; Python 3.12.10; compute type `int8`
- Inventory: 18 generated WAV cases from the weighted scenario matrix
- Reference words: 132; word errors: 13; micro-WER: 0.098
- Mean realtime factor: 0.158; maximum realtime factor: 0.251
- Full per-case transcripts, timing and edit counts: `docs/feedback/ASR_SCENARIO_RESULTS.json`

| Case group | Count | Result |
|---|---:|---|
| Development | 12 | 12 adapter observations completed |
| Held-out | 6 | 6 adapter observations completed |
| Total | 18 | 18 adapter observations completed |

The fixtures are generated voice or generated acoustic material. The scores compare known local scripts and do not establish human speech accuracy, generalization, accessibility benefit, vision quality, reasoning quality or end-to-end task completion.

## 2026-09-24 - Opt-in ASR timing and decoder-evidence probe

`python -m accessflow.perception.asr_evidence` directly invokes the installed Faster Whisper model with `beam_size=5` and `word_timestamps=True`. It records the fixture SHA-256 and format, model snapshot, segment and word offsets, decoder estimates, and model load/inference time. It is a **diagnostic direct-model probe**, not `LocalPerception.observe`, a browser microphone test, an agent turn, or an official Samsung run. The probe does not infer turn finality or calibrated confidence. It emits JSON to stdout and does not save raw audio.

Backend: Faster Whisper 1.2.1, `Systran/faster-whisper-base.en`, snapshot `3d3d5dee26484f91867d81cb899cfcf72b96be6c`, CPU INT8 on Intel Core Ultra 5 125H. The runs below used the already-installed local model and checked-in **generated** WAV fixtures. Timings are individual warm-machine observations, not a latency distribution.

| Fixture (SHA-256 prefix) | Model load | Inference | Decoded evidence |
|---|---:|---:|---|
| `synthetic_pause_correction.wav` (`49b0b26f`) | 1.713 s | 2.150 s | `Book Tuesday Actually, Wednesday at 5`; two segments at 0.00–0.64 s and 2.68–5.04 s. |
| `held_out/heldout_repetition.wav` (`d16355e7`) | 1.096 s | 1.676 s | `I want Tuesday, Tuesday, actually Wednesday at 5.`; one segment at 0.00–3.74 s. Separate word offsets retain both `Tuesday` tokens (0.40–0.74 s and 1.34–1.82 s) and `Wednesday` (2.64–3.10 s). |
| `synthetic_tone.wav` (`9038a655`) | 1.025 s | 1.432 s | No decoded segments on one generated half-second tone. This is not a silence-detection benchmark. |

For the repetition clip, the model emitted word decoder probabilities of approximately 0.986 and 0.989 for the two `Tuesday` tokens and 0.997 for `Wednesday`; the segment's `avg_logprob` was -0.285 and `no_speech_prob` was 0.000354. These are **raw decoder estimates, not calibrated correctness probabilities**. The generated source and exposure history prevent calling the case fresh unseen human speech. The probe's `word_timestamps=True` path can alter the exact punctuation/text and runtime relative to the default live `LocalPerception` path; the earlier adapter transcript and timing above must not be treated as directly comparable. Segment offsets are model-relative to the submitted WAV, not session-clock capture timestamps or proof of when a turn is complete.

The public `Observation` currently flattens transcript text and sets audio finality without carrying these offsets/estimates. Until Atishay and Mridul agree C24-1/2's provenance, clock, revision, finality and uncertainty fields—and Mridul changes the shared contract/controller—this probe does **not** feed agent decisions. Real microphone capture, human speech, physical interruption and official raw-MP3 evaluation remain unverified.

## 2026-09-25 — No-speech microphone boundary

The user explicitly requested that no speech be required. The local page at `http://127.0.0.1:8000/` showed microphone permission state `prompt` and waited for browser permission; the in-app browser did not expose an actionable permission dialog. Reloading canceled the pending capture request and returned the page to its microphone-off “Tap to speak” state. No microphone bytes were captured or uploaded, and no spoken phrase was requested. This is a permission/UI observation only, not a microphone or acoustic test. Ollama and local model manifests were absent and ports 11434/11435 were closed, so no live vision model result was available. Generated-fixture ASR and the model-backed worker/Agent regression remain the available non-human evidence.

## 2026-09-24 - Real child-worker and Agent seam on generated WAVs

The existing installed Faster Whisper 1.2.1 `Systran/faster-whisper-base.en` snapshot `3d3d5dee26484f91867d81cb899cfcf72b96be6c` ran through the actual `ProcessPerception` child process on this Intel Core Ultra 5 125H/Windows host (Python 3.12.10, CPU INT8). Sources were the checked-in **generated** `held_out/heldout_repetition.wav` (SHA-256 `d16355e7d1e702ebc309227e18bd9925a3ec7290cc7d454754d89dbaae55853f`) and `synthetic_pause_correction.wav` (SHA-256 `49b0b26fd1ebcae0772b2559a4aba3782444f59fab7e7e7038122f06157c872b`).

- Direct child-worker call 1, including spawn/model load: 4.921 s; transcript `I want Tuesday, Tuesday, actually Wednesday at 5.`
- Same live child-worker call 2: 1.650 s; transcript `Book Tuesday. Actually, Wednesday at 5.` The child PID was reused and was no longer alive after `aclose()`.
- One separate run through the actual `Agent` controller plus the real ASR child worker took 4.678 s from queued audio to a final. The reasoner was a deterministic **mock**, the policy was the final-flag baseline, and the tool manifest was empty. Its view contained the recognized repeated-Tuesday/corrected-Wednesday audio observation with matching event/source IDs and `faster-whisper/cpu-int8` provenance; the final's `caused_by_event_id` matched the audio event. There were zero tool calls/effects and the child stopped after close.

The opt-in owned regression `tests/perception/test_live_worker_agent.py` checks the Agent/worker seam with `ACCESSFLOW_TEST_WHISPER_MODEL_PATH` set to an installed snapshot; it skips when no path is supplied rather than downloading a model. It now uses Atishay’s `HeuristicTurnPolicy` and verifies that the ASR correction causes an acknowledgment and a final tied to the same audio event, with zero mock tool effects. The focused local run passed. This is actual local ASR on generated voice, **not** human microphone audio, official MP3 admission, a real reasoning-model result or booking behavior. The worker returned `final=True` and `speech_start=speech_end=0.0` because the current shared audio contract has no clip finality or measured clock mapping; C24-1/2 remains unresolved. Single-run wall times are not latency percentiles.
