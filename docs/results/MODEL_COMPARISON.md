# Model comparison

This is the single record of model performance for this project. Answer any question about
model choice from this file. Do not answer from memory.

Everything below the generated marker comes from `run_metadata` rows in `artifacts/`.
Regenerate after any model run:

```
python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md
```

## How to read the totals

The totals mix runs from different days, and the controller changed between them. Three
changes moved scores independently of the model:

1. The write-continuation constraint, 14 September. It took `qwen3:4b` on
   `support-read-then-service` from never passing to passing.
2. The request and inference deadline flags, 14 September. A hard-coded 25 second deadline
   cancelled requests that were still in flight.
3. Full GPU offload, 14 and 15 September. A partial offload made local requests two to four
   times slower.

An aggregate pass rate therefore understates any model that was tested early and not
retested. Prefer the per-scenario table, and prefer recent runs.

Ablated runs are excluded from both tables. They carry a deliberate marker that the oracle
counts as an unexpected error. See `ABLATION_2026-09-15.md`.

## Current recommendation

`qwen/qwen3.8-27b` on Groq is the primary model. It has the lowest mean request time of any
model measured and the best per-scenario record.

It needs `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`. Without it every request is refused at
admission:

```
Request too large ... on output tokens per minute (OTPM): Limit 1000, Requested 1990
```

The adapter sends no `max_tokens`, so the provider assumes the model's default ceiling and
compares that against the per-minute output budget. This is an admission check on one
request, not accumulated usage, so pacing does not avoid it. An earlier reading of this
failure as a model limitation was wrong.

`openai/gpt-oss-120b` is the fallback. It has never been refused at admission and needs no
output cap. `openai/gpt-oss-20b` is faster and cheaper and now clears the hardest fixture.

## Local models

No local model completes a three-turn fixture on a GTX 1650 with 4096 MiB.

- `qwen3:4b` is fast enough at 12 to 14 seconds per request with all 37 layers on the GPU.
  It repeats a completed read instead of writing, so it fails the three-turn fixtures.
  It still passes the single-turn fixtures.
- `qwen2.5:7b-instruct` needs about 5100 MiB for full offload, so 17 of 29 layers run on the
  CPU at 51.6 seconds per request. It reaches three requests inside the 120 second cap.

Pin `ACCESSFLOW_OLLAMA_NUM_GPU=37` for `qwen3:4b` only. See `INFERENCE_TUNING_2026-09-14.md`.

## Known provider limits

| Model | Limit | Value | Workaround |
|---|---|---|---|
| `qwen/qwen3.8-27b` | output tokens per minute | 1000 | `ACCESSFLOW_MAX_OUTPUT_TOKENS=950` |
| `openai/gpt-oss-120b` | tokens per minute | 8000 | pace one run per 95 seconds |
| `qwen/qwen3.6-27b` | output tokens per minute | 1000 | untested with the output cap |

`qwen3.6-27b` scored 1/7 and returned `400 json_validate_failed`. Those runs predate the
output cap, so the score is not a quality measurement. Retest before you discard the model.

<!-- generated -->
Generated from 207 recorded runs in `artifacts/`.
Regenerate with `python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md`.

## Totals by model

| Model | Runs | Completed | Oracle passed | Mean request | Slowest | Scenarios | HTTP errors | Last run |
|---|---|---|---|---|---|---|---|---|
| `offline-fake` | 50 | 45/50 | 43/44 | - | - | 9 | none | 2026-09-15 |
| `ollama/qwen3:4b` | 42 | 24/42 | 24/42 | 19.84 s | 42.76 s | 6 | none | 2026-09-15 |
| `groq/qwen/qwen3.8-27b` | 25 | 21/25 | 21/25 | 0.94 s | 1.53 s | 6 | 429 | 2026-09-15 |
| `ollama/qwen2.5:3b` | 20 | 8/20 | 7/20 | 8.59 s | 21.49 s | 4 | none | 2026-09-13 |
| `groq/openai/gpt-oss-120b` | 14 | 11/14 | 11/14 | 1.95 s | 3.24 s | 6 | 429 | 2026-09-15 |
| `nvidia/google/gemma-4-31b-it` | 12 | 6/12 | 6/12 | 24.90 s | 60.69 s | 4 | 403 | 2026-09-14 |
| `ollama/qwen2.5:7b-instruct` | 9 | 3/9 | 3/9 | 27.99 s | 51.59 s | 5 | none | 2026-09-15 |
| `groq/openai/gpt-oss-20b` | 7 | 6/7 | 6/7 | 1.41 s | 2.06 s | 5 | none | 2026-09-15 |
| `groq/qwen/qwen3.6-27b` | 7 | 1/7 | 1/7 | 2.55 s | 3.39 s | 4 | 400, 429 | 2026-09-14 |
| `ollama/gemma3:4b` | 7 | 0/7 | 0/7 | 15.55 s | 19.74 s | 5 | none | 2026-09-13 |

## Oracle results per scenario

| Scenario | `gpt-oss-120b` | `gpt-oss-20b` | `qwen3.6-27b` | `qwen3.8-27b` | `gemma-4-31b-it` | `offline-fake` | `gemma3:4b` | `qwen2.5:3b` | `qwen2.5:7b-instruct` | `qwen3:4b` |
|---|---|---|---|---|---|---|---|---|---|---|
| development-text-correction-01 | - | - | - | - | - | 10/11 | 0/2 | - | - | - |
| device-correction-during-pending-write | - | - | - | - | - | 10/10 | - | - | - | - |
| live-dev-development-text-correction-01 | 1/2 | 1/1 | 1/1 | 4/5 | 1/3 | 1/1 | 0/2 | 1/5 | 2/2 | 7/8 |
| live-dev-device-correction-before-plan | 1/1 | 1/1 | 0/2 | 5/5 | 2/3 | 1/1 | 0/1 | 2/5 | 1/2 | 7/8 |
| live-dev-lost-response-status-reconciliation | 1/1 | 1/1 | 0/2 | 5/5 | 2/3 | 1/1 | 0/1 | 3/5 | 0/2 | 4/8 |
| live-dev-stale-read-after-correction | 3/3 | - | - | 1/1 | - | - | - | - | - | 0/3 |
| live-dev-stale-read-after-device-correction | 4/4 | 3/3 | - | 2/3 | - | - | - | - | 0/1 | 0/3 |
| live-dev-support-read-then-service | 1/3 | 0/1 | 0/2 | 4/6 | 1/3 | 1/1 | 0/1 | 1/5 | 0/2 | 6/12 |
| lost-response-status-reconciliation | - | - | - | - | - | 9/10 | - | - | - | - |
| support-read-then-service | - | - | - | - | - | 10/10 | - | - | - | - |
| unknown | - | - | - | - | - | 0/5 | - | - | - | - |
