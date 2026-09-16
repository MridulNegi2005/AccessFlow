# Local planner comparison, 13 September 2026

These are four developer-authored text development cases, using actual local reasoning
and in-memory mock tools. They are not the final held-out set or an official score.
Raw reports include configuration, hardware/runtime evidence, typed plans and source hashes.

Both runs explicitly used Ollama `qwen2.5:3b`, GPU option 99, 4096 context, temperature 0,
20-second HTTP and 25-second controller inference deadlines. Scenario completion waits
were 100 seconds. No hosted or paid fallback was used. Defaults remain Gemma 3 4B.

| Source | Prompt | Passed task criteria | Remaining failures |
|---|---|---|---|
| `82a9d0c` | Original grounded prompt | 1/4 | Missing slot updates; repeated write after unknown outcome |
| `f543d3c` | Explicit slot/completion guidance and ledger status projection | 1/4 | Invented tool-name prefix twice; repeated write instead of status query |

The second run's passing case was support leading to service; the first run's was text
correction. This is not evidence of an overall accuracy improvement. In particular, the
first run's passing case omitted argument dependencies. A subsequent controller audit
proved those omissions could allow stale reads or contradictory argument values. Task
criteria passing alone did not prove dependency safety.

Reports and traces: `planner-2026-09-13/qwen-original-report.json`, `qwen-original-case-*.jsonl`,
`qwen-guided-report.json`, and `qwen-guided-case-*.jsonl`. Failed runs are retained unchanged.
Model cleanup reported unloaded after each case. Source hashes in each trace take precedence
over the commit containing these copied artifacts.

Next iteration: enforce argument/slot dependencies in the controller, preserve operation
identity across model-generated nonce changes, and bind generation tool names to supplied
manifests. Evaluate the known cases and then the four independently authored, previously
unread AI development probes. Those probes are not clinical data or teammate held-out cases.
