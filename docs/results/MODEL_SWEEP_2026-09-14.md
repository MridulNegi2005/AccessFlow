# Model sweep, 14 September 2026

Scenarios: `scenarios/live_dev`, four developer-authored text cases with mock tools.
Same prompt, same guards, same deadlines. Only the model and backend change.
Not the held-out set and not an official score.

## Hosted results

| Model | text | device | lost-response | support | Score | Mean request |
|---|---|---|---|---|---|---|
| `qwen/qwen3.8-27b` | pass | pass | pass | pass | **4/4** | 0.91 s |
| `openai/gpt-oss-120b` | pass | pass | pass | pass | **4/4** | 1.95 s |
| `openai/gpt-oss-20b` | pass | pass | pass | fail | 3/4 | 1.32 s |
| `qwen/qwen3.6-27b` | pass | fail | fail | fail | 1/4 | 1.72 s |

qwen3.6-27b is not a quality result. Three of its four runs never reached the model.

## Local results

GTX 1650, 4096 MiB VRAM. Details in LOCAL_REPEAT_2026-09-14.md.

| Model | Size | Score | Mean request |
|---|---|---|---|
| `qwen3:4b` | 2.5 GB | 3/4, 2/4, 2/4 over three trials | 14 s to 40 s |
| `qwen2.5:3b` | 1.9 GB | 2/4 | 10.06 s |
| `qwen2.5:7b` | 4.7 GB | 2/4, measured while spilling to shared memory | 26.54 s |
| `gemma3:4b` | 3.3 GB | 0/4 | n/a |

## The capacity wall

`support-read-then-service` needs four slots and a two-step read-then-write chain. It
separates the models cleanly:

- Every model at or below 20 B fails it. The plans omit the slot updates their own
  dependencies reference, so the chain never completes.
- Both 27 B and 120 B models pass it.

The wall sits between 20 B and 27 B. `gpt-oss-20b` failed on a timeout with no rate-limit
error, after one successful request. That is the same signature as the local models, at
1.3 s per request instead of 20 s, which confirms the cause is planning capacity and not
elapsed time.

## Free-tier limits differ by dimension

Limits are enforced per model, so switching models gives a fresh budget.

| Model | Limit hit | Value |
|---|---|---|
| `qwen/qwen3.8-27b` | input tokens per minute | 7000 |
| `openai/gpt-oss-120b` | input tokens per minute | throttled at suite pace |
| `qwen/qwen3.6-27b` | **output** tokens per minute | **1000** |

A single plan needs roughly 660 to 1120 output tokens. An output limit of 1000 therefore
allows about one request per minute, which makes qwen3.6-27b unusable for a suite whatever
its quality. It also returned `400 json_validate_failed` with an empty `failed_generation`,
so it could not produce valid JSON for this schema.

Pacing one scenario per 55 to 95 seconds avoided throttling for the other models.

## NVIDIA NIM

Blocked. The key lists models successfully but every inference request returns
`403 Forbidden, Authorization failed`, across `google/gemma-4-31b-it`,
`mistralai/mistral-7b-instruct-v0.3`, `nvidia/llama-3.1-nemotron-70b-instruct` and
`openai/gpt-oss-20b`. The key is well formed: 115 characters, `nvapi-` prefix, no
whitespace or quotes. The rejection is account-side, not a client defect. Gemma 4 remains
untested.

## Recommendation

1. `qwen/qwen3.8-27b` is the best tested option: 4/4 and the fastest at 0.91 s mean.
2. `openai/gpt-oss-120b` is a verified 4/4 fallback on a separate per-model budget.
   Configuring two backends protects a long run from one provider's limit.
3. Do not rely on any model at or below 20 B for the two-step chain.
4. Keep the local backend working. The official guide never states that the evaluation
   environment has outbound network access.

Traces: `artifacts/groq-paced`, `artifacts/groq-gptoss120b`, `artifacts/groq-gptoss20b_*`,
`artifacts/groq-qwen36-27b*`, `artifacts/nv-gemma4-31b`.
