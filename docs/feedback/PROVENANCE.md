# Recording and feedback provenance

No recordings or participant feedback collected by this bootstrap.
For every future fixture record author, date, consent/license, intended split, modality,
backend-independent expected outcome and whether speech is illustrative or naturally recorded.
Do not commit private recordings or infer clinical representativeness from team examples.

## synthetic_tone.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally; no participant or third-party recording
- Modality: 0.5 second mono PCM WAV, 16-bit, 16 kHz, deterministic 440 Hz tone
- Intended split: Development ingestion and format validation only
- Expected outcome: The WAV validator accepts the file; no speech transcript is expected
- SHA-256: 9038A6555BC5598B60B954D69637DC83BFC2322C9A55A6ABF644863EB67DF8B5
- Backend: Backend-independent fixture; it must not be used as live ASR quality evidence
## synthetic_speech.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally with the installed Windows speech synthesizer; no participant or third-party recording
- Modality: 5.304 second mono PCM WAV, 16-bit, 22.05 kHz
- Intended split: Development-only illustrative ASR and ingestion check
- Script: My screen keeps flickering after the update. Book Wednesday at five.
- SHA-256: B42354F90462A08AD23DF835256289116DEFDE4287AB2AC3D9D3CF2E87BCD5E6
- Backend: Faster Whisper measurement only; not a clinical or representative speech sample
