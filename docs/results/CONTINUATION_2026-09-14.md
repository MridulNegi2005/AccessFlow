# Write-continuation constraint, 14 September 2026

A schema and prompt change that lets a 2.5 GB local model complete the two-step chain that
previously only 27 B and larger models could finish.

## The observed failure

Earlier notes described the small-model failure on `support-read-then-service` as omitted
slots. The trace shows otherwise. On qwen3:4b the first planning turn was correct:

```
OUT tool_call  inspect_support_notes args={'symptom': 'flicker'} deps=['symptom']
       slots={symptom: flicker, device: Panel-A, day: Wednesday, hour: 17:00}
IN  tool_result success
OUT acknowledge {'result': {'rows': [... 'recommendation': 'Service visit ...'}]}
IN  session_end
```

Slot extraction, tool choice and dependencies were all correct. The model was called a
second time, received the read result, and answered with it instead of calling the write
tool. The failure is continuation, not extraction and not capacity.

## The change

The controller already tracks `speech_write_requested`. That signal now reaches the planner
through an additive `write_pending` field on `SessionView`, which defaults to false, so every
existing reasoner and test double stays valid.

When a write is requested and no write call has been dispatched or confirmed, the planner:

1. adds a `required_next_step` of kind `complete_requested_write`, stating that a completed
   read is evidence for the effect and never a substitute for it; and
2. builds the output schema with `response` typed `null`.

The second point is the important one. The model cannot answer with prose while a requested
write is outstanding. Its only valid options are a tool call or an explicit clarification,
both of which the controller can act on. This reuses the mechanism already proven by
`allow_write_calls`, which binds tool names to the supplied manifest.

The write tool stays available during this turn. This is a continuation, not the read-only
turn used for unresolved write outcomes.

## Result

qwen3:4b, 2.5 GB, GTX 1650, thinking disabled, identical fixtures and deadlines.

| Measure | Before | After |
|---|---|---|
| Suite totals | 3/4, 2/4, 2/4 | 3/4, 4/4 |
| `support-read-then-service` | fail, fail, fail | pass at 78 s, timeout, pass at 58 s |

The one failure after the change was a 100-second scenario-cap timeout, not an incorrect
plan. Scenario runtimes were 16 s to 59 s for the cases that completed.

Hosted regression check, `qwen/qwen3.8-27b` on Groq: 4/4 unchanged, 0.83 s to 1.53 s per
request. The offline `scenarios/dev` suite remains 4/4. 244 tests and Ruff pass.

## What this means

1. The 20 B to 27 B capacity wall recorded in MODEL_SWEEP_2026-09-14.md was partly an
   artefact of the output contract, not model capability alone. A 4 B model completes the
   chain once prose is not an allowed answer.
2. Local remains latency-bound rather than capability-bound. Requests take 16 s to 41 s
   here, so the 120-second cap is still the binding constraint.
3. The constraint is a controller decision expressed in the schema, not a prompt hint. It
   holds regardless of which model is behind the adapter.

Traces: `artifacts/qwen3-4b-continuation.jsonl`, `artifacts/qwen3-4b-c1`,
`artifacts/qwen3-4b-c2`, `artifacts/groq-continuation_*.jsonl`.
