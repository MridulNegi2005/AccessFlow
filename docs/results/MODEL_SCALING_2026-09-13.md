# Local model scaling comparison, 13 September 2026

This test asks one question. Does a larger open model fix the planner failures?

The four cases are developer-authored text development scenarios with mock tools.
They are not the held-out set and not an official score.

## Method

Both runs used the same source commit, the same prompt, the same guards and the same
scenarios. Only the model changed. Configuration was Ollama on port 11435, GPU option 99,
4096 context, temperature 0, a 90-second request timeout and a 95-second controller
inference deadline. Each model ran once.

## Result

| Scenario | qwen2.5:3b | qwen2.5:7b-instruct |
|---|---|---|
| development-text-correction-01 | fail | pass |
| device-correction-before-plan | pass | pass |
| lost-response-status-reconciliation | pass | fail |
| support-read-then-service | fail | fail |
| **Total** | **2/4** | **2/4** |

| Measure | qwen2.5:3b | qwen2.5:7b-instruct |
|---|---|---|
| Mean successful request | 10.1 s | 26.5 s |
| Slowest successful request | 21.5 s | 45.3 s |
| Total suite runtime | 239 s | 267 s |

## Findings

1. The larger model gave no accuracy gain. Both models passed two of four cases.
2. The two models passed different subsets. This is not a simple capability ordering.
   Each model ran once, so a per-case difference may be run variance, not stable capability.
3. `support-read-then-service` failed on both models. This case is the consistent failure.
4. The larger model cost about 2.6 times the request latency for no accuracy gain.
5. The 7B mean of 26.5 seconds and maximum of 45.3 seconds are large against the official
   120-second scenario cap. Response latency is 15 percent of the official score.

## The earlier deadline defect

A first 7B run reported 1/4 and three `backend_failure` results. The traces show the
controller cancelled those requests at 25.0 seconds. The 25-second controller inference
deadline was a fixed constant and the `--request-timeout` flag did not change it.
The model never answered. That run measured the deadline, not the model.

Commit `e5aa8af` makes both deadlines settable. A qwen2.5:3b run at the old 20-second
request cap also scored 1/4 for the same reason. The 2/4 figure in the earlier handoff is
correct and reproduces once the deadline is adequate.

Treat any earlier result that reports `backend_failure` as unmeasured, not as a
planning error.

## Conclusion

A modest local size increase does not fix the planner. The local hardware cannot test the
capacity hypothesis further, because a 7B model already approaches the latency budget on a
4 GB card. A hosted backend is required to test a larger model and to measure latency that
is competitive.

The Groq adapter for that test is implemented in commit `9261035`. It needs an API key.

Reports and traces: `artifacts/fair-qwen2-5-3b/` and `artifacts/fair-qwen2-5-7b-instruct/`.
Superseded deadline-limited runs: `artifacts/cmp-qwen3b-baseline/` and `artifacts/cmp-qwen7b/`.
