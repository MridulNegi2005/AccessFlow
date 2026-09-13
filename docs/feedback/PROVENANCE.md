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

## synthetic_pause_correction.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally with the installed Windows speech synthesizer; no participant or third-party recording
- Modality: 6.024 second mono PCM WAV, 16-bit, 22.05 kHz
- Intended split: Development-only pause, correction and endpoint timing check
- Script: Book Tuesday. [1.5 second break] Actually, Wednesday at five.
- SHA-256: 49B0B26FD1EBCAE0772B2559A4ABA3782444F59FAB7E7E7038122F06157C872B
- Backend: Faster Whisper and WebRTC timing measurements only; not a held-out case

## Held-out generated speech cases

These files were generated after the earlier development fixtures and thresholds were
fixed. “Held-out” means held out from that local development pass; the generated voice is
not representative speech and supplies no clinical or population evidence.

### heldout_fluent.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally with the installed Windows speech synthesizer; no participant or third-party recording
- Modality: 3.449 second mono PCM WAV, 16-bit, 22.05 kHz
- Intended split: Held-out local ASR and endpoint check
- Script: Please book a screen repair for Friday at ten.
- SHA-256: 0D6A41360CC1102B2A359B3C303E913733FB83A5939D54ABD2C364E8FBE5DCF9
- Backend: Faster Whisper and WebRTC measurements only

### heldout_repetition.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally with the installed Windows speech synthesizer; no participant or third-party recording
- Modality: 4.724 second mono PCM WAV, 16-bit, 22.05 kHz
- Intended split: Held-out repetition and correction transcription check
- Script: I want Tuesday, Tuesday, actually Wednesday at five.
- SHA-256: D16355E7D1E702EBC309227E18BD9925A3EC7290CC7D454754D89DBAAE55853F
- Backend: Faster Whisper and WebRTC measurements only

### heldout_pause.wav

- Author: Codex for AccessFlow development
- Date: 2026-09-13
- Consent/license: Generated locally with the installed Windows speech synthesizer; no participant or third-party recording
- Modality: 5.958 second mono PCM WAV, 16-bit, 22.05 kHz
- Intended split: Held-out internal-pause boundary check
- Script: I tried restarting already. [1.2 second inserted break] The screen still flickers.
- Labeled pause: 2.549-3.749 seconds
- SHA-256: AE2C76972D9C398E7E9C102A381A09B44B3D4C2FC8A6937D3EA257D998E39210
- Backend: Faster Whisper and WebRTC measurements only
