# Public informational response evidence — 22 September 2026

`pub_04_no_tool_attempt1.json` is one live Groq Qwen `qwen/qwen3.8-27b` attempt
against Samsung's exposed no-tool text case. Supplied scorer total **100.0**;
task, latency and safety fractions 1.0. No tool call was emitted.

The user asked what the agent can help with. The final accurately described the
manifested flight, manual and support-ticket capabilities. Input arrived at110ms;
acknowledgment was at110ms and the informational final at735ms. The scorer's10ms
acknowledgment delta uses its scheduled-event reference; delivered-input-to-final
elapsed time was625ms. Do not present acknowledgment latency as final-answer latency.

Two provider requests including warm-up, both successful:49 warm-up input tokens
and3001 planning input tokens. No API failure, cancellation or fallback. This does
not prove that multi-step requests fit the observed account quota.

## Profile and provenance

Full prompt profile, output cap950, context-character cap32768, partial debounce1.0s,
fast read retry enabled, explicit docs/TOOLS.md interface reference. Official time
scale1, unchanged tail6000ms and wall cap120s. Environment changes were scoped to
the child process. Configured key values were checked absent before copying.

This run was recorded after the informational-follow-up fix and before the later
first-plan write-success guard extension. Its exact source hashes and dirty/base
revision are retained in the report. The latter write guard is verified by the
separate deterministic suite; this read-only run does not exercise it.

`manifest.json` contains the verified SHA-256 hash of the byte-identical local
report copy. Organizer raw scenarios, source and media are excluded.

## Reproduce

Configure the existing declared Groq key/model/URL and hosted profile, then:

```powershell
$env:ACCESSFLOW_SAMSUNG_PROMPT_PROFILE = "full"
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_04_text_no_tool.json --output artifacts/samsung/new-no-tool-attempt.json
```

Use a fresh output file. This single public scenario is not a repeated-run median,
hidden-set result or live evidence of follow-ups after bookings. The latter is
covered by explicitly labelled mock integration tests in
`tests/engine/test_informational_followups.py` and `test_request_scope.py`.
Implementation and failure history: `../../INFORMATIONAL_FOLLOWUPS_2026-09-22.md`.
