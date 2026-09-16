# Controller responsiveness measurements

```powershell
uv run accessflow responsiveness --samples 100 --output-dir artifacts/responsiveness
```

This command measures the real queue-based controller with synthetic, gated workers.
Each condition uses independent sessions. It is an orchestration benchmark, not an ASR,
live-model, speech playback or user-benefit evaluation. A waiting async worker does not
simulate CPU saturation, network variability or a particular model's resource consumption.

The probes cover ordinary final input, final input while earlier reasoning is pending,
explicit interruption while reasoning is pending, and interruption of a pending write.
Gates keep work unfinished until the required acknowledgment/cancellation has been emitted.
For tool cancellation, the outgoing cancellation is emitted before its transport starts;
the check proves the controller does not wait for transport completion.

## Timing boundaries

- Input-to-acknowledgment: acceptance into the input queue to acceptance of the causally
  matched acknowledgment in the output queue. This includes controller/perception dispatch.
- Input-to-cancellation: input queue acceptance to the matched cancellation output.
- Cancellation entry-to-emission: entry into the controller's `_cancel` method to outgoing
  queue acceptance. Instrumentation lives in an evaluation-only subclass. This measures
  dispatch after the controller has decided to invalidate; it excludes semantic detection.

All timestamps come from the same `perf_counter` clock. Queue acceptance is measured at
`put`, not when a later consumer reads the output. Raw samples identify their events and
timing boundaries so durations can be checked independently. No speech-end time is inferred
from input arrival, and no acknowledgment duration is called a substantive response time.

## Interpreting results

The report records per-condition counts and quantiles, source/configuration metadata and
the raw JSONL path. Failed or missing samples remain in the denominator. The internal
targets are p95 acknowledgment below 300 ms and cancellation dispatch below 50 ms, with
complete successful sampling required before declaring a target met. These are team
targets, not Samsung thresholds. CLI exit code 1 means a probe failed or a target was missed.

Tests verify gate ordering, causal measurements, cleanup and incomplete-sample accounting;
they do not require sub-millisecond timing on every development machine. Inspect individual
conditions rather than relying only on an aggregate that could hide a slower path.

Local output is under ignored `artifacts/`. Selected measured evidence may be copied into
`docs/results/` with its tested code commit and raw samples. This does not replace the
planned turn-policy baselines, stale-result ablation, real-media evaluation or held-out set.

Measured development evidence: [13 September run](results/RESPONSIVENESS_2026-09-13.md).
