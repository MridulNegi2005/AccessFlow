# Transient-read retry evidence — 22 September 2026

Two serial, exposed Samsung public development runs using live Groq Qwen
`qwen/qwen3.8-27b` and Samsung mock tools. Source hashes, runner hash, kit hashes,
scenario, model configuration and documentation provenance match across reports.
The controlled configuration difference is `fast_read_retry`; generated IDs,
timestamps, provider timing and provider quota state are not controlled.

| Measurement | Fast retry enabled | Model-directed retry control |
|---|---:|---:|
| Supplied scorer total | 100.0 | 81.5 |
| First error received, ms | 3125 | 3000 |
| Retry action emitted, ms | 3140 | 3922 |
| Error-to-retry gap, ms | 15 | 922 |
| Successful read result, ms | 4984 | 5766 |
| Final response, ms | 5734 | None |
| Model requests including warm-up | 3 | 4 |
| Model outcomes | 3 successful | 3 successful, 1 HTTP 429 |

The fast run returned both actual Seattle options, with their times and prices.
The control also completed its second read, but its final model request was rejected:
the provider reported input quota 7000/minute, 5590 used, 3484 requested.
Do not attribute the control's missing final solely to response latency or the
tail cutoff. Eliminating one model round trip reduced both elapsed retry time
and token demand in this pair. This is one configuration comparison, not a
statistical latency study, pure network-independent ablation, completion percentage,
hidden-set result or release certification. Earlier `pub_08_first.json` used a
different source/profile and is not the matched control.

## Configuration and reproduction

Both runs used official time scale 1, tail 6000 ms, wall cap 120 seconds,
output cap 950, hosted context-character cap 32768, partial debounce 1.0 seconds,
and explicitly selected `docs/TOOLS.md` below the kit root. No clock extension,
canned final, paid fallback or actual external booking was used.

Configure the chosen Groq model/key/URL locally. In PowerShell:

```powershell
$env:ACCESSFLOW_SAMSUNG_BACKEND = "groq"
$env:ACCESSFLOW_MAX_OUTPUT_TOKENS = "950"
$env:ACCESSFLOW_MAX_CONTEXT_CHARS = "32768"
$env:ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S = "1.0"
$env:ACCESSFLOW_SAMSUNG_FAST_READ_RETRY = "1"
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_08_text_tool_failure.json --output artifacts/samsung/new-fast-attempt.json
```

For a control, set the retry flag to `"0"` and choose a fresh output path.
Allow quota recovery between runs; do not repeatedly request known-exhausted quota.
The reports include actual flags, sanitized model telemetry, plans, execution
ledger, hashes and official traces. Copies are byte-identical to local originals;
`manifest.json` records their SHA-256 hashes. Configured API key values were checked
absent before copying. Raw organizer scenario files, source and media are excluded.

## Controller guarantees exercised

Only a current, failed read with a whitelisted transient error may automatically
retry once. Arguments, dependency revisions, request and logical operation ID stay
the same; the new physical call ID records `retry_of_call_id`. The model and
controller share the two-attempt budget. Writes are never automatically retried.
Unresolved corrections, changed inputs, invalidated dependencies and stopped tasks
block this route. Failed or late old payloads never become usable results.

A current delegated write contract may follow this exact controller-issued read
replacement. The source ID changes; selectors, fixed mappings, constraints and
permission do not. Expired barriers remain intact. Separate deterministic tests
exercise successful read-retry-to-write continuation; this public case makes no write.

## Software validation and remaining issues

New fast-retry tests: 25 passed. Final combined run: **1021 passed, 1 skipped,
1 xfailed**, 2 dependency warnings, 71.79 seconds. Ruff and diff checks passed;
offline-fake development scenarios passed 4/4. The preceding combined run had
one B-owned stale-frame timeout failure (1020 passed); three isolated reruns and
the final full run passed on unchanged B files. That intermittent issue remains
open in `../../reviews/ATISHAY_TIMING_FOLLOWUP_2026-09-22.md`.

The skip requires Windows native symlink privileges; the existing conflicting-frame
xfail is unresolved. No claim that every test case passed. Further public text,
interruption, unfamiliar tool and repeated-run coverage is still needed. MP3,
vision and calibrated speech timing require coordination with Atishay.
