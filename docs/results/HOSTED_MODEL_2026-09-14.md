# Hosted model comparison, 14 September 2026

This test asks whether a larger hosted model fixes the planner failures.

The four cases are developer-authored text development scenarios with mock tools.
They are not the held-out set and not an official score.

## Method

All runs used the same source commit, the same prompt, the same guards and the same
scenarios. Only the model and the backend changed. Deadlines were a 90-second request
timeout and a 95-second controller inference deadline.

The hosted backend is Groq, model `qwen/qwen3.8-27b`, temperature 0, `json_object`
response format. The configured default `llama-3.3-70b-versatile` is not available on
this account. Check the model list before every scored run.

## Result

| Scenario | gemma3:4b local | qwen2.5:3b local | qwen2.5:7b local | qwen3.8-27b hosted |
|---|---|---|---|---|
| development-text-correction-01 | fail | fail | pass | **pass** |
| device-correction-before-plan | fail | pass | pass | **pass** |
| lost-response-status-reconciliation | fail | pass | fail | **pass** |
| support-read-then-service | fail | fail | fail | **pass** |
| **Total** | **0/4** | **2/4** | **2/4** | **4/4** |

| Measure | qwen2.5:3b | qwen2.5:7b | qwen3.8-27b hosted |
|---|---|---|---|
| Mean successful request | 10.06 s | 26.54 s | **0.91 s** |
| Slowest successful request | 21.49 s | 45.34 s | **1.03 s** |
| Slowest scenario runtime | 95 s | 95 s | **2.0 s** |

The hosted run used 6 requests, a mean of 1459 prompt tokens and 8756 input tokens in total.
The gemma3:4b column is the earlier result in LOCAL_MODEL_2026-09-13.md.

## Findings

1. The hosted 27B model passed all four cases. `support-read-then-service` had failed on
   every local model. The remaining planner failures were model capacity, not the
   interface contract.
2. The hosted model was about 29 times faster than the local 7B per request.
3. The slowest hosted scenario used 2.0 seconds of the official 120-second cap.
4. No warm-up was required. The local cold start was 145 seconds against a 300-second hook.

## Free-tier rate limiting

Two batched suite runs scored 3/4 and 2/4. Every one of those failures was HTTP 429, not a
planning error:

```
Rate limit reached ... input tokens per minute (ITPM): Limit 7000, Used 6757, Requested 1667
```

The limit is 7000 input tokens per minute. Requests average 1459 prompt tokens, so the
ceiling is about 4.8 requests per minute. A four-scenario suite sends about 6 requests and
throttles itself.

Running one scenario every 75 seconds produced 4/4 with zero throttled requests. The
4/4 figure above is that paced run.

Consequences for a 60-scenario evaluation:

- About 120 requests at 1459 tokens is about 175000 input tokens.
- At 7000 tokens per minute that is about 25 minutes of rate-limited time.
- A 429 inside a scenario consumes that scenario's 120-second cap and scores as a failure.

The system prompt is 781 tokens, which is 54 percent of the average request. Reducing it
raises throughput under this limit more than any other free change.

## Required follow-up

1. The official guide does not state that the evaluation environment has outbound network
   access. A hosted-only submission scores zero if the harness is sandboxed. Keep the local
   backend working and keep backend selection explicit.
2. Measure whether request pacing or a shorter prompt keeps a full suite inside the limit.
3. Repeat runs. Each model ran once per configuration, so per-case differences between the
   local models may be variance rather than capability.

Traces: `artifacts/groq-paced/` is the paced 4/4 run. `artifacts/groq-qwen3-8-27b/` and
`artifacts/groq-qwen3-8-27b-run2/` are the throttled batched runs, retained unchanged.
