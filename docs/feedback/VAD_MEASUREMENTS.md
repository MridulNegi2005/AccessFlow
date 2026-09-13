# Acoustic activity measurements

## 2026-09-13 - WebRTC VAD versus energy baseline

- Backend: webrtcvad-wheels 2.0.14 through accessflow.perception.webrtc_activity
- Device: CPU, Intel(R) Core(TM) Ultra 5 125H
- Python: 3.12.10
- WebRTC settings: aggressiveness 2, 20 ms frames, normalized 16 kHz 16-bit mono PCM

### synthetic_tone.wav

- Duration: 0.500 seconds
- Energy baseline: 25/25 active frames; one window from 0.000 s to 0.500 s
- WebRTC VAD: 25/25 active frames; one window from 0.000 s to 0.500 s
- Interpretation: both backends classify the deterministic tone as active audio. This is a
  useful false-positive boundary for speech claims.

### synthetic_speech.wav

- Duration: 5.304 seconds after normalization to 16 kHz
- Energy baseline: 138/266 active frames across fragmented windows
- WebRTC VAD: 189/265 active frames across two windows, with 0.640 s trailing silence
- Settings: aggressiveness 2, 20 ms frames
- Interpretation: WebRTC supplies a different acoustic segmentation from the energy baseline
  on this generated voice. It does not establish accuracy, pause quality or user benefit.

Both fixtures are generated development assets with provenance recorded in
docs/feedback/PROVENANCE.md. No participant audio was used.
