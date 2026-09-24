# First Samsung public text runs — 22 September 2026

Live backend: Groq `qwen/qwen3.8-27b`, maximum output tokens 950, official time
scale 1, default tail 6000 ms. External actions were the organizer's mock tools.
All three runs used the same committed AccessFlow source at `b5125f2`; the diagnostic
runner was added as uncommitted work for the second and third runs. These cases are now
exposed development cases. They are not held-out evidence, three-run medians,
multimodal results or a submission score.

| Case | Supplied scorer total | Observed outcome |
|---|---:|---|
| `pub_01_text_simple` | 100.0 | Search succeeded; a grounded final response followed. No setup error or agent crash. |
| `pub_03_text_chained_booking` | 56.9 | Search succeeded; booking was blocked by the controller's tool-origin value guard. No confirmed booking or final response. |
| `pub_08_text_tool_failure` | 81.5 | A failed search was retried once and succeeded, but final-answer inference was canceled when the standard tail window ended. |

The second run received only 0.3 of available **task** credit. Its overall 56.9
also includes latency and safety points; it must not be called a 56.9% task
completion rate. A fast filler is not evidence of a fast substantive answer.

The chained trace shows a completed user request for an 8 AM flight to Denver
for Alice. Qwen performed the search, then proposed `book_flight` using the
returned `FL-DEN-8AM` identifier. The controller asked for confirmation of that
tool-origin identifier. This reproduces a limitation in legitimate chained
actions; it does not justify allowing arbitrary tool-provided values to overwrite
user-fixed details.

The failure case received 0.7 of available task credit. Its first read failed at
2906 ms, the retry was dispatched at 3734 ms, and success arrived at 5578 ms.
The final reasoning request was still running when the harness ended near 6109 ms.
This validates that read recovery runs with the actual provider, while exposing
insufficient final-answer time in this attempt. It does not establish a latency
distribution. A bounded controller retry for transient reads is a possible next
optimization; do not extend the official tail or substitute a canned final to
inflate the score.

`pub_01_first.json` came from the initial inline diagnostic runner. It records
model/configuration, a scenario hash, score and trace, but lacks the fuller Git,
kit and runner provenance fields of the second report. Its source-commit statement
above was checked from the unchanged source tree, not captured in that report.
`pub_03_first.json` was produced by `scripts/run_samsung_check.py` and includes
planner proposals, source/kit/runner hashes, Git state and model telemetry.

Reports here are byte-identical copies of their original local artifacts;
`manifest.json` records hashes. Configured API keys were checked absent before
copying. Organizer scenario source, annotations, answer keys and raw media are
not included in this folder. Scorer feedback is included as evaluation output.

Reproduce a new single attempt after explicitly loading the selected profile:

```powershell
$env:ACCESSFLOW_SAMSUNG_BACKEND = "groq"
$env:ACCESSFLOW_MAX_OUTPUT_TOKENS = "950"
# Configure the Groq key/model/URL from your local profile; do not commit keys.
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --scenario pub_03_text_chained_booking.json --output artifacts/samsung/new-pub03.json
```

The runner does not load `.env` implicitly, switch providers, overwrite old
reports, or pass the scenario dictionary to the participant. Failed setup or
execution remains an attempted run with an explicit failure and retained trace.
