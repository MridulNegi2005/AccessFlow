# Controller responsiveness: 13 September 2026

Tested code: `7a67b44a1d63f14cfa95a6729c618bac58009ae5`, clean working tree. Python 3.11.15 on the Windows host.

Command: `uv run accessflow responsiveness --samples 100 --output-dir artifacts/responsiveness-7a67b44`.

400/400 synthetic probes passed: 100 separate sessions per condition. This is sequential controller instrumentation with pending async workers, not real-model load, speech latency, throughput or accessibility validation.

| Condition | Samples | Acknowledgment p95 (ms) |
|---|---:|---:|
| final_ack_reasoner_blocked | 100 | 0.419 |
| fluent_final_request | 100 | 0.630 |
| interrupt_ack_reasoner_blocked | 100 | 0.153 |
| tool_cancel_blocked | 100 | 0.356 |

Cancellation input-to-output p95: 0.217 ms. Controller `_cancel` entry-to-output p95: 0.144 ms (100 samples).

The complete sampling and aggregate p95 checks met the internal 300 ms acknowledgment and 50 ms cancellation-dispatch targets for this synthetic setup. These are not official evaluator thresholds.

[Report](../../docs/results/responsiveness-7a67b44.json) and [raw samples](../../docs/results/responsiveness-7a67b44.jsonl) include source hashes, configuration, causal IDs and gate states. All recorded durations were independently recomputed from timestamps; aggregate p95 values were checked with Python statistics.quantiles using the inclusive method.

Limitations: single fresh process, simple final-flag policy, scripted transcript pass-through, small session state, no ASR/vision/model inference, playback, native CPU saturation, network variability or user study. The benchmark uses zero partial debounce to establish its setup gates; probes measure final inputs and explicit interruptions. Real turn-policy comparisons and multimodal runs remain outstanding.

Atishay checkpoint `d61d4dc` was discovered after this code was prepared. Its perception/UI changes are not part of this measurement; integration review is next.
