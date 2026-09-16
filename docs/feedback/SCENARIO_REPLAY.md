# Weighted scenario replay

Recorded 16 September 2026 on `atishay/perception` at commit `095c393`.

## What ran

The offline replay gate `tests/perception/test_scenario_replay.py` loaded the 60-case
`docs/feedback/SCENARIO_MATRIX.json` inventory and sent every case through the owned
`LocalPerception` boundary in one session. Text cases used the text pass-through path;
WAV cases used an injected replay ASR; inline PNG payloads used an injected replay
vision provider. The replay asserted one observation per case, preserved each event
ID and source ID, retained final metadata, and matched the planned modality counts.

| Modality | Cases | Observations | Backend | Result |
|---|---:|---:|---|---|
| Text | 30 | 30 | `local/text-pass-through` | pass |
| Audio | 18 | 18 | `local/injected-asr` | pass |
| Image | 12 | 12 | `fake/replay-vision` | pass |
| **Total** | **60** | **60** |  | **pass** |

## Verification

- Focused inventory and replay tests: `5 passed`.
- Full repository suite: `230 passed, 4 strict xfailed, 2 warnings`.
- Ruff passed for the replay and inventory tests.
- `git diff --check` passed.

This is offline fake-mode routing and metadata evidence. The injected providers return
the authored stimuli by design, so this run does not measure ASR accuracy, image grounding,
reasoning quality, latency, endpoint behavior, or user benefit. Live local and hosted
scoring remain separate work.
