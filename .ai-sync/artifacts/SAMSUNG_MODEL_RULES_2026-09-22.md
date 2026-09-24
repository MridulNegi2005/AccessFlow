# Samsung Theme 5 model rules — verified 22 September 2026

This note answers Mridul's question about cloud/local inference, parameter counts
and the observed quota. It uses the supplied participant kit, not a web claim
about another Samsung event or another theme.

## What Samsung allows and requires

| Question | Supplied Theme 5 rule |
|---|---|
| Cloud APIs or on-device? | Both hosted APIs and open/local models are explicitly allowed. |
| Mandatory model family? | Any model is welcome; Gemini API and Gemma are encouraged, not required. |
| Maximum parameter count? | No parameter-count ceiling was found in the supplied Theme 5 guide or kit model/runtime rules. |
| CPU-only or GPU restriction? | No Theme 5 CPU-only condition was found. The overview's CPU/minimal-GPU condition appears under Theme 1. Local model feasibility and organizer reproducibility still matter. |
| Own hosted service? | Model inference may use an API; the agent's decision logic must live in the submission, not be routed through the team's own server. Public checkpoints or included model-hosting scripts must make open-model setups reproducible. |
| Runtime? | Python 3.10–3.12, agent class imported in-process, two asynchronous queues; do not block the shared event loop. |
| Time limits? | 300 seconds for optional setup, 120 seconds wall clock per scenario, official time scale 1. API latency counts. |
| Model configuration? | Seed what is possible, using temperature 0 or supported fixed seeds. The evaluator uses three repetitions and the per-scenario median. |
| Dependencies/secrets? | Declare requirements and key names in submission.yaml. Register secret values through the event portal, never commit them. |
| Memory? | Session-scoped conversational state. Model setup assets are distinct from retaining a previous user's conversation as input. |

Primary sources: the kit's `README.md`, `docs/SUBMISSION.md` (Models and dependencies,
Determinism requirements), `docs/PROTOCOL.md` (Runtime contract), and original
`Theme 5_Guide.pdf` section 6 (reviewed via the existing extracted text). The original
overview page 4 labels its CPU condition explicitly as Theme 1. These files are
distributed separately from the repository; later organizer clarifications may
supersede them. Absence of a published hardware ceiling is not evidence that an
arbitrary local setup will be provisioned by the evaluator.

## What the quota actually was

Groq returned HTTP 429 with `ITPM` limit **7000** for the selected account/model:
input tokens per minute. Our third planning request in the recorded interruption
case requested another 3732 input tokens after 5869 were used. This is provider
admission control, not a Samsung parameter cap or Samsung token budget.

The configured Qwen identifier is `qwen/qwen3.8-27b`. The model's parameter count,
the API token rate, and context/output limits are different quantities. The output
cap 950, hosted context-character cap 32768 and partial debounce 1.0 seconds in our
recorded profile are team configuration choices, not Samsung requirements. Actual
API quotas can change; refer to per-run diagnostics rather than treating one
observed value as permanent.

## Atishay's separate issue

Send him `reviews/ATISHAY_TIMING_FOLLOWUP_2026-09-22.md`. The newer frame timed out
waiting for the previous native worker's permit in one combined run. Isolated
reruns and subsequent complete runs passed. This is an intermittent failure with
an investigation path, not a proven root cause or a closed repair. Atishay owns
the perception deadline semantics and its tests; Mridul has not edited those files.
