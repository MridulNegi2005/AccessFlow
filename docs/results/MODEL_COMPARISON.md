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

The `Latest` column is the most recent run for that model and scenario. Trust it over the

`Passed` ratio beside it. A model that failed in an earlier era and passed on retest still

carries the old failure in the ratio.

Selection now uses the full recorded run timestamp, not a file modification date. Every

run recorded before this fix has no such timestamp and falls back to file mtime instead.

The generated table marks each such row `(mtime, order unverified)`. Treat those rows as

disclosed best-effort ordering, not verified chronology.

Ablated runs are excluded from every table. They carry a deliberate marker that the oracle

counts as an unexpected error. See `ABLATION_2026-09-15.md`.

## Current recommendation

`qwen/qwen3.8-27b` on Groq is the primary model. It has the lowest mean request time of any

model measured and the best per-scenario record.

It needs `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`. Without it every request is refused at

admission:

```

Request too large ... on output tokens per minute (OTPM): Limit 1000, Requested 1990

```

The adapter sends `max_tokens` only when `ACCESSFLOW_MAX_OUTPUT_TOKENS` is set. On the
uncapped path it sends none, so the provider assumes the model's default ceiling and

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

`qwen3.6-27b` scored 1/7. Of the six failures, five are HTTP 429 admission-control

rejections (rate limit or request too large) that predate the output cap, not a reasoning

failure. The sixth is a genuine HTTP 400 `json_validate_failed`: the provider rejected the

model's own generated output. See the evidence bundle below for the per-run breakdown.

Retest with the output cap before you discard the model on this record.

## Evidence bundle

Selected raw traces for the four Groq-hosted models above are committed at

[docs/evidence/model-comparison-2026-09-15/](../evidence/model-comparison-2026-09-15/),

not left in ignored `artifacts/`. A clean clone can read them with no provider calls, no

keys, and no local `artifacts/`:

```

python scripts/model_scoreboard.py --artifacts docs/evidence/model-comparison-2026-09-15/traces --write docs/results/MODEL_COMPARISON.md

```

That command reproduces only the Groq-hosted rows (`qwen3.8-27b`, `gpt-oss-120b`,

`gpt-oss-20b`, `qwen3.6-27b`) from the 57 runs in the bundle. The full table below,

including local-model and `offline-fake` rows, still needs a local `artifacts/` directory;

that evidence is not bundled. See the bundle's

[README](../evidence/model-comparison-2026-09-15/README.md) and `manifest.json` for the

cohort selection rule, the sanitisation applied to 11 rate-limited traces that logged the

Groq organization id, and an explicit eligibility classification per run (admission

failure, generated-output failure, or scored pass/fail).

`source_sha256` in that manifest hashes only `*.py` files under `src/accessflow/`. It does

not cover `scripts/`, the dependency lockfile, or environment settings, and these are

hosted-API calls that cannot be replayed offline. Treat the bundle as a reproducible

record of the scoreboard's arithmetic, not a reproducible record of the original model

behaviour.

<!-- generated -->
Generated from 240 recorded runs in `artifacts/`.
Regenerate with `python scripts/model_scoreboard.py --write docs/results/MODEL_COMPARISON.md`.

`Oracle passed` and per-scenario pass counts divide by scored runs only (null/unscored oracles excluded from that denominator, counted separately as `Unscored`). `Completed` divides by every attempted run regardless of scoring, so infrastructure failures do not disappear from the record.

`Mean request`/`Slowest` cover only requests marked successful. They are not end-to-end scenario latency and do not include timed-out or failed requests.

207 of 240 run(s) have no recorded run timestamp and fall back to file mtime for ordering; those are marked `(mtime, order unverified)` wherever shown.

## Excluded evidence

No files were excluded.

## Totals by model

| Model | Runs | Completed | Oracle passed | Unscored | Mean request (successful) | Slowest (successful) | Scenarios | HTTP errors | Last run |
|---|---|---|---|---|---|---|---|---|---|
| `offline-fake` | 74 | 69/74 | 67/68 | 6 | - | - | 9 | none | 2026-09-15T13:29:58+00:00 |
| `ollama/qwen3:4b` | 42 | 24/42 | 24/42 | 0 | 19.84 s | 42.76 s | 6 | none | 2026-09-14T19:07:07+00:00 (mtime, order unverified) |
| `groq/qwen/qwen3.8-27b` | 34 | 29/34 | 29/34 | 0 | 0.93 s | 1.77 s | 8 | 429 | 2026-09-15T13:52:59+00:00 |
| `ollama/qwen2.5:3b` | 20 | 8/20 | 7/20 | 0 | 8.59 s | 21.49 s | 4 | none | 2026-09-13T15:23:23+00:00 (mtime, order unverified) |
| `groq/openai/gpt-oss-120b` | 14 | 11/14 | 11/14 | 0 | 1.95 s | 3.24 s | 6 | 429 | 2026-09-14T19:09:11+00:00 (mtime, order unverified) |
| `nvidia/google/gemma-4-31b-it` | 12 | 6/12 | 6/12 | 0 | 24.90 s | 60.69 s | 4 | 403 | 2026-09-13T19:50:58+00:00 (mtime, order unverified) |
| `ollama/qwen2.5:7b-instruct` | 9 | 3/9 | 3/9 | 0 | 27.99 s | 51.59 s | 5 | none | 2026-09-14T19:25:21+00:00 (mtime, order unverified) |
| `groq/openai/gpt-oss-20b` | 7 | 6/7 | 6/7 | 0 | 1.41 s | 2.06 s | 5 | none | 2026-09-14T19:34:56+00:00 (mtime, order unverified) |
| `groq/qwen/qwen3.6-27b` | 7 | 1/7 | 1/7 | 0 | 2.55 s | 3.39 s | 4 | 400, 429 | 2026-09-13T19:36:34+00:00 (mtime, order unverified) |
| `ollama/gemma3:4b` | 7 | 0/7 | 0/7 | 0 | 15.55 s | 19.74 s | 5 | none | 2026-09-13T12:36:58+00:00 (mtime, order unverified) |

## Oracle results per scenario

| Scenario | `gpt-oss-120b` | `gpt-oss-20b` | `qwen3.6-27b` | `qwen3.8-27b` | `gemma-4-31b-it` | `offline-fake` | `gemma3:4b` | `qwen2.5:3b` | `qwen2.5:7b-instruct` | `qwen3:4b` |
|---|---|---|---|---|---|---|---|---|---|---|
| development-text-correction-01 | - | - | - | - | - | 14/14 (+1 unscored) | 0/2 | - | - | - |
| device-correction-during-pending-write | - | - | - | - | - | 14/14 | - | - | - | - |
| live-dev-audio-correction-01 | - | - | - | 3/4 | - | - | - | - | - | - |
| live-dev-development-text-correction-01 | 1/2 | 1/1 | 1/1 | 4/5 | 1/3 | 1/1 | 0/2 | 1/5 | 2/2 | 7/8 |
| live-dev-device-correction-before-plan | 1/1 | 1/1 | 0/2 | 5/5 | 2/3 | 1/1 | 0/1 | 2/5 | 1/2 | 7/8 |
| live-dev-frame-device-panel-01 | - | - | - | 1/1 | - | - | - | - | - | - |
| live-dev-lost-response-status-reconciliation | 1/1 | 1/1 | 0/2 | 6/6 | 2/3 | 1/1 | 0/1 | 3/5 | 0/2 | 4/8 |
| live-dev-stale-read-after-correction | 3/3 | - | - | 1/1 | - | - | - | - | - | 0/3 |
| live-dev-stale-read-after-device-correction | 4/4 | 3/3 | - | 4/5 | - | - | - | - | 0/1 | 0/3 |
| live-dev-support-read-then-service | 1/3 | 0/1 | 0/2 | 5/7 | 1/3 | 1/1 | 0/1 | 1/5 | 0/2 | 6/12 |
| lost-response-status-reconciliation | - | - | - | - | - | 21/22 | - | - | - | - |
| support-read-then-service | - | - | - | - | - | 14/14 | - | - | - | - |
| unknown | - | - | - | - | - | unscored (5) | - | - | - | - |

## Every model, every scenario

### `offline-fake`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| development-text-correction-01 | 15 | 14/14 | 15/15 | - | - | pass | 2026-09-15T13:29:58+00:00 |
| device-correction-during-pending-write | 14 | 14/14 | 14/14 | - | - | pass | 2026-09-15T13:29:58+00:00 |
| live-dev-development-text-correction-01 | 1 | 1/1 | 1/1 | - | - | pass | 2026-09-13T12:20:13+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 1 | 1/1 | 1/1 | - | - | pass | 2026-09-13T12:20:12+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 1 | 1/1 | 1/1 | - | - | pass | 2026-09-13T12:20:13+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 1 | 1/1 | 1/1 | - | - | pass | 2026-09-13T12:20:13+00:00 (mtime, order unverified) |
| lost-response-status-reconciliation | 22 | 21/22 | 22/22 | - | - | pass | 2026-09-15T13:29:58+00:00 |
| support-read-then-service | 14 | 14/14 | 14/14 | - | - | pass | 2026-09-15T13:29:58+00:00 |
| unknown | 5 | 0/0 | 0/5 | - | - | unscored (None) | 2026-09-13T11:06:28+00:00 (mtime, order unverified) |

### `ollama/qwen3:4b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 8 | 7/8 | 7/8 | 14.61 s | 20.58 s | pass | 2026-09-13T20:37:24+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 8 | 7/8 | 7/8 | 18.41 s | 27.00 s | pass | 2026-09-13T20:36:45+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 8 | 4/8 | 4/8 | 23.58 s | 40.08 s | pass | 2026-09-13T20:37:02+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-correction | 3 | 0/3 | 0/3 | 17.33 s | 23.11 s | fail (timeout) | 2026-09-14T18:39:40+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-device-correction | 3 | 0/3 | 0/3 | 14.14 s | 23.30 s | fail (timeout) | 2026-09-14T19:07:07+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 12 | 6/12 | 6/12 | 22.07 s | 42.76 s | pass | 2026-09-13T20:37:51+00:00 (mtime, order unverified) |

### `groq/qwen/qwen3.8-27b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-audio-correction-01 | 4 | 3/4 | 3/4 | 0.93 s | 1.25 s | pass | 2026-09-15T13:30:11+00:00 |
| live-dev-development-text-correction-01 | 5 | 4/5 | 4/5 | 0.97 s | 1.09 s | pass | 2026-09-14T19:50:26+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 5 | 5/5 | 5/5 | 0.83 s | 0.86 s | pass | 2026-09-14T19:43:21+00:00 (mtime, order unverified) |
| live-dev-frame-device-panel-01 | 1 | 1/1 | 1/1 | 1.25 s | 1.39 s | pass | 2026-09-15T13:52:59+00:00 |
| live-dev-lost-response-status-reconciliation | 6 | 6/6 | 6/6 | 0.99 s | 1.77 s | pass | 2026-09-15T10:18:19+00:00 |
| live-dev-stale-read-after-correction | 1 | 1/1 | 1/1 | 0.96 s | 1.23 s | pass | 2026-09-14T19:46:16+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-device-correction | 5 | 4/5 | 4/5 | 0.84 s | 1.17 s | pass | 2026-09-15T13:31:56+00:00 |
| live-dev-support-read-then-service | 7 | 5/7 | 5/7 | 0.93 s | 1.53 s | pass | 2026-09-15T09:45:09+00:00 |

### `ollama/qwen2.5:3b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 5 | 1/5 | 1/5 | 7.37 s | 8.86 s | fail (timeout) | 2026-09-13T15:23:23+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 5 | 2/5 | 2/5 | 12.03 s | 21.49 s | pass | 2026-09-13T15:19:47+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 5 | 3/5 | 3/5 | 8.35 s | 9.47 s | pass | 2026-09-13T15:20:03+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 5 | 1/5 | 2/5 | 7.84 s | 9.92 s | fail (timeout) | 2026-09-13T15:21:43+00:00 (mtime, order unverified) |

### `groq/openai/gpt-oss-120b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 2 | 1/2 | 1/2 | 1.55 s | 1.55 s | pass | 2026-09-13T19:18:48+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 1 | 1/1 | 1/1 | 2.25 s | 2.25 s | pass | 2026-09-13T19:17:18+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 1 | 1/1 | 1/1 | 1.85 s | 2.03 s | pass | 2026-09-13T19:17:22+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-correction | 3 | 3/3 | 3/3 | 1.93 s | 2.80 s | pass | 2026-09-14T18:41:31+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-device-correction | 4 | 4/4 | 4/4 | 1.95 s | 3.24 s | pass | 2026-09-14T19:09:11+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 3 | 1/3 | 1/3 | 2.17 s | 2.30 s | pass | 2026-09-13T19:21:41+00:00 (mtime, order unverified) |

### `nvidia/google/gemma-4-31b-it`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 3 | 1/3 | 1/3 | 6.09 s | 6.09 s | fail (backend_failure) | 2026-09-13T19:50:58+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 3 | 2/3 | 2/3 | 7.26 s | 8.75 s | pass | 2026-09-13T19:47:15+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 3 | 2/3 | 2/3 | 29.17 s | 60.69 s | pass | 2026-09-13T19:47:47+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 3 | 1/3 | 1/3 | 37.26 s | 57.33 s | fail (timeout) | 2026-09-13T19:49:27+00:00 (mtime, order unverified) |

### `ollama/qwen2.5:7b-instruct`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 2 | 2/2 | 2/2 | 20.87 s | 21.17 s | pass | 2026-09-13T15:27:53+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 2 | 1/2 | 1/2 | 45.34 s | 45.34 s | pass | 2026-09-13T15:24:12+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 2 | 0/2 | 0/2 | 24.23 s | 27.58 s | fail (timeout) | 2026-09-13T15:25:52+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-device-correction | 1 | 0/1 | 0/1 | 51.59 s | 51.59 s | fail (timeout) | 2026-09-14T19:25:21+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 2 | 0/2 | 0/2 | 21.59 s | 25.55 s | fail (timeout) | 2026-09-13T15:27:32+00:00 (mtime, order unverified) |

### `groq/openai/gpt-oss-20b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 1 | 1/1 | 1/1 | 1.12 s | 1.12 s | pass | 2026-09-13T19:26:30+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 1 | 1/1 | 1/1 | 1.52 s | 1.52 s | pass | 2026-09-13T19:21:52+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 1 | 1/1 | 1/1 | 1.25 s | 1.38 s | pass | 2026-09-13T19:22:52+00:00 (mtime, order unverified) |
| live-dev-stale-read-after-device-correction | 3 | 3/3 | 3/3 | 1.45 s | 2.06 s | pass | 2026-09-14T19:34:56+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 1 | 0/1 | 0/1 | 1.45 s | 1.45 s | fail (timeout) | 2026-09-13T19:25:30+00:00 (mtime, order unverified) |

### `groq/qwen/qwen3.6-27b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| live-dev-development-text-correction-01 | 1 | 1/1 | 1/1 | 1.72 s | 1.72 s | pass | 2026-09-13T19:30:32+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 2 | 0/2 | 0/2 | - | - | fail (backend_failure) | 2026-09-13T19:33:14+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 2 | 0/2 | 0/2 | 3.39 s | 3.39 s | fail (backend_failure) | 2026-09-13T19:34:56+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 2 | 0/2 | 0/2 | - | - | fail (backend_failure) | 2026-09-13T19:36:34+00:00 (mtime, order unverified) |

### `ollama/gemma3:4b`

| Scenario | Runs | Passed | Completed | Mean request (successful) | Slowest (successful) | Latest | Last run |
|---|---|---|---|---|---|---|---|
| development-text-correction-01 | 2 | 0/2 | 0/2 | 13.98 s | 19.72 s | fail (timeout) | 2026-09-13T12:17:26+00:00 (mtime, order unverified) |
| live-dev-development-text-correction-01 | 2 | 0/2 | 0/2 | 15.42 s | 19.74 s | fail (timeout) | 2026-09-13T12:36:58+00:00 (mtime, order unverified) |
| live-dev-device-correction-before-plan | 1 | 0/1 | 0/1 | - | - | fail (backend_failure) | 2026-09-13T12:28:14+00:00 (mtime, order unverified) |
| live-dev-lost-response-status-reconciliation | 1 | 0/1 | 0/1 | - | - | fail (backend_failure) | 2026-09-13T12:28:51+00:00 (mtime, order unverified) |
| live-dev-support-read-then-service | 1 | 0/1 | 0/1 | 18.97 s | 18.97 s | fail (timeout) | 2026-09-13T12:30:49+00:00 (mtime, order unverified) |
