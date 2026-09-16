# Mixed multimodal scenario replay

Recorded 16 September 2026 on `atishay/perception` at commit `5a58f27`.

The replay sent the complete 60-case inventory through one `Agent` session. Text used
the demo pass-through, audio used the cached Faster Whisper base.en CPU INT8 adapter,
inline PNGs used the replaceable injected vision seam, and the reasoner captured the
controller context with informational responses. No state-changing tools were supplied.

| Modality | Cases | Observations | Backend | Result |
|---|---:|---:|---|---|
| Text | 30 | 30 | `demo/mock-text` | pass |
| Audio | 18 | 18 | `faster-whisper/cpu-int8` | pass |
| Image | 12 | 12 | `fake/replay-vision` | pass |
| **Total** | **60** | **60** |  | **pass** |

- Total elapsed time: 12.38 seconds.
- Every case preserved its event ID, source ID, final flag and modality.
- Every case produced an informational controller final.
- Full per-case output and context metadata: `docs/feedback/MULTIMODAL_SCENARIO_RESULTS.json`.

The vision responses are injected labels because the local Ollama service and model were
unavailable during the preflight. Reasoning is a mock capture. The run therefore proves
owned transport, perception, context and response wiring, while live vision grounding,
non-mock reasoning, human speech quality, latency certification and user benefit remain
unmeasured.
