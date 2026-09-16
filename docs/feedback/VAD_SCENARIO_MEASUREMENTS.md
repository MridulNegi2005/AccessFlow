# Weighted scenario timing measurements

Recorded 16 September 2026 on `atishay/perception` at commit `cd4444e`.

All 18 audio cases were loaded through the owned PCM path and classified with
`webrtcvad-wheels 2.0.14` at 16 kHz, 20 ms frames and aggressiveness 2. Pause candidates
used a 0.4 second threshold.

- Active frames: 2463 of 3764.
- Cases with an internal pause candidate: 10.
- Cases with a trailing candidate: 18.
- Maximum analysis time for one case: 0.0916 seconds.

| Case | Split | Active frames | Active windows | Internal candidates | Trailing candidates | Trailing silence (s) |
|---|---|---:|---:|---:|---:|---:|
| audio-01 | development | 189/265 | 2 | 1 | 1 | 0.64 |
| audio-02 | development | 139/301 | 3 | 1 | 1 | 0.64 |
| audio-03 | held_out | 130/172 | 1 | 0 | 1 | 0.66 |
| audio-04 | held_out | 173/236 | 3 | 0 | 1 | 0.64 |
| audio-05 | held_out | 162/297 | 2 | 1 | 1 | 0.62 |
| audio-06 | development | 114/162 | 2 | 0 | 1 | 0.62 |
| audio-07 | development | 131/246 | 3 | 2 | 1 | 0.64 |
| audio-08 | development | 120/210 | 3 | 1 | 1 | 0.66 |
| audio-09 | development | 139/193 | 2 | 0 | 1 | 0.66 |
| audio-10 | development | 112/151 | 1 | 0 | 1 | 0.66 |
| audio-11 | development | 115/190 | 2 | 1 | 1 | 0.64 |
| audio-12 | development | 126/163 | 2 | 1 | 0 | 0.0 |
| audio-13 | development | 90/163 | 2 | 1 | 1 | 0.62 |
| audio-14 | development | 135/172 | 1 | 0 | 1 | 0.64 |
| audio-15 | development | 170/270 | 4 | 1 | 1 | 0.64 |
| audio-16 | held_out | 162/237 | 2 | 1 | 1 | 0.62 |
| audio-17 | held_out | 130/172 | 1 | 0 | 1 | 0.66 |
| audio-18 | held_out | 126/164 | 1 | 0 | 1 | 0.64 |

Full per-case windows and candidates are in `docs/feedback/VAD_SCENARIO_RESULTS.json`.

WebRTC output is acoustic activity and endpoint-candidate evidence. It is not a speech
classifier or semantic completion decision. These are generated local fixtures, and pause
candidates must be reconciled with transcript revisions and controller policy.
