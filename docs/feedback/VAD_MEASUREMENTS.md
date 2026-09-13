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

## 2026-09-13 - Endpoint candidates over WebRTC activity

- Threshold: 0.400 seconds
- synthetic_speech.wav: internal candidate 2.520-3.300 seconds (0.780 s); trailing candidate 4.660-5.300 seconds (0.640 s)
- synthetic_pause_correction.wav: internal candidate 0.960-3.220 seconds (2.260 s); trailing candidate 5.380-6.020 seconds (0.640 s)

The pause-correction internal candidate spans the generated 1.5 second break plus speech
classification margins. Candidates are timing signals only and do not complete an utterance.

## 2026-09-13 - Held-out endpoint check

Settings: WebRTC VAD aggressiveness 2, 20 ms frames, normalized 16 kHz 16-bit mono PCM;
endpoint candidate threshold 0.400 seconds.

| Case | Active frames | Windows | Internal candidates | Trailing candidate |
|---|---:|---|---|---|
| heldout_fluent.wav | 130/172 | 0.180-2.780 s | none | 2.780-3.440 s (0.660 s) |
| heldout_repetition.wav | 173/236 | 0.100-1.180, 1.460-2.180, 2.420-4.080 s | none at threshold | 4.080-4.720 s (0.640 s) |
| heldout_pause.wav | 162/297 | 0.100-1.880, 3.860-5.320 s | 1.880-3.860 s (1.980 s) | 5.320-5.940 s (0.620 s) |

The labeled inserted break in heldout_pause.wav is 2.549-3.749 seconds. The candidate
overlaps the full 1.200-second label, with start error -0.669 seconds, end error
+0.111 seconds and interval-over-union 0.606. The early start shows that this simple
windowed candidate includes acoustic margins; it is a timing signal, not a precise
speech boundary or semantic completion decision.

The fluent and repetition cases produced no internal candidate at the fixed threshold.
The repetition case still produced several acoustic activity windows, which reinforces
that activity segmentation must not be used to delete repeated words or infer intent.
