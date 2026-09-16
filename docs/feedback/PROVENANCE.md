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

## Weighted multimodal inventory assets

The 16 September inventory assets below are generated locally for the weighted scenario set. They contain no participant recordings or third-party images. The matrix records the full per-case provenance and SHA-256 values; these assets establish fixture identity and format availability, not model quality or user benefit.

| ID | Modality | Split | Fixture | Generator | Bytes | SHA-256 |
|---|---|---|---|---|---:|---|
| audio-06 | audio | development | `tests/fixtures/audio/audio-06.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 143550 | `7C6FD7255A3AFB7BE2D6AD9A62BBC71594D591C7975AB962F7F2487330698E91` |
| audio-07 | audio | development | `tests/fixtures/audio/audio-07.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 217190 | `FFBC38F16BEC25FDC85B6E50CBDE52005762475C8D22BE945A63941278C8669A` |
| audio-08 | audio | development | `tests/fixtures/audio/audio-08.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 186104 | `74BCB7E2A55912BBF4A75E167277C1AA131AE1E9F1B0ABE8015A801BBAE9FF69` |
| audio-09 | audio | development | `tests/fixtures/audio/audio-09.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 170444 | `89E4359A32C642C32BEAE8BFFFD0F94727834B3555CD1003E87F15AEFB4D8DD0` |
| audio-10 | audio | development | `tests/fixtures/audio/audio-10.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 134064 | `E358BC7D2547D460F5D413346CC9CF9C62CA2D01B558AB2341572C75B09F8CDA` |
| audio-11 | audio | development | `tests/fixtures/audio/audio-11.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 168462 | `41FFC4204B235AF6435139949E917BE4FA88DEA9064A3F6080B78109215F5374` |
| audio-12 | audio | development | `tests/fixtures/audio/audio-12.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 122604 | `57DF935EC17C07190A5A20816C5F7AA04448A52597E4060B31B931F91E3CABDA` |
| audio-13 | audio | held_out | `tests/fixtures/audio/audio-13.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 144654 | `16F61BBB74026723B0559CDB8213FF469AA212061550BDE568F3F57D8B7FC323` |
| audio-14 | audio | held_out | `tests/fixtures/audio/audio-14.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 152360 | `672FF49F2EA57B8603BE9FFD13FCC70790D3DA0C6797146483FEC10D759513B9` |
| audio-15 | audio | held_out | `tests/fixtures/audio/audio-15.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 239010 | `4DADB58C984CD23619CD512CB02A882E65ADEA2C1BD5AC839D83F7A7EE0A0187` |
| audio-16 | audio | held_out | `tests/fixtures/audio/audio-16.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 209912 | `E0D85733542D881A10D4F49CA232840AE9244C5A117ECA8E97D022AC43AD3AC0` |
| audio-17 | audio | held_out | `tests/fixtures/audio/audio-17.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 152144 | `0D6A41360CC1102B2A359B3C303E913733FB83A5939D54ABD2C364E8FBE5DCF9` |
| audio-18 | audio | held_out | `tests/fixtures/audio/audio-18.wav` | Windows System.Speech.Synthesis.SpeechSynthesizer | 145526 | `C3BEA2FFA097C8459DE1BC8B5B93297077B82DDDEE2FFAFF211C8A811A288C0E` |
| image-01 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2338 | `234427960545A5F087E0179E3A04893E940FFA2ADB838639B530BC42E72F27E7` |
| image-02 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2377 | `1BD20185DF8E7733E80873F1D0E710E1F50BAB00B97A117260001FFD45733B23` |
| image-03 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2332 | `45AC6F40AA2D0233BCF5751C18BEBE5A1BBEB6A0A70EE980A2E6280BFE5DD49E` |
| image-04 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2356 | `A2739DD06B21AF58F90E47506C877A7912DE60BEE52A49F2CE832530CB3D9ECF` |
| image-05 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2375 | `89FBE57BCF3F114CB9BD88C0E9EC5200A3AD646A3FD5762811F47121F33DA14B` |
| image-06 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2337 | `BBE0E42A081F6157C396A2BA67A3C5FA7FBBE0E9E98E3BBE1245AC6D259C6069` |
| image-07 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2374 | `C79ECC0BCA30E9EA0B35F3F63C7235B88D5DAAB9E58C3C0E37C8BA05E54508AD` |
| image-08 | image | development | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2387 | `F9D48B5D235CB57CC38BE864BFA1D2B55D152517E75D1DD950BD71462B0E6DD9` |
| image-09 | image | held_out | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2387 | `830F8D332FAABBE773B2EE5DCCFB10FA001D5E23BB903B4CB440DA19C2D25654` |
| image-10 | image | held_out | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2333 | `B17CF6387540EF6CB72526802F4052B2DC771FEB3FE5171053E0E2399AC1E23D` |
| image-11 | image | held_out | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2397 | `1D60329C8BF4AECAE4E7BBFE1C580336CAD2B9026FBABFFBB56F19A6E4CE3784` |
| image-12 | image | held_out | `inline SCENARIO_MATRIX payload` | AccessFlow deterministic standard-library PNG writer | 2338 | `E02A11FE4B59DDF46010B28E445729A78DC075F1EB3521DE315319CFDFCFA227` |
