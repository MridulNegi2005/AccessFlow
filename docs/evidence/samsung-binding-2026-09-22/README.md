# Chained-action development evidence — 22 September 2026

One public case, three incremental attempts using live Groq Qwen
`qwen/qwen3.8-27b` and Samsung mock external tools. The original pre-binding
baseline in `../samsung-text-2026-09-22/pub_03_first.json` scored 56.9: search
worked, but the tool-origin identifier guard prevented booking.

| Retained attempt | Scorer total | What actually happened |
|---|---:|---|
| `pub_03_binding_attempt1.json` | 38.5 | Model output failed validation; no accepted plan or tool call. Field-level cause was not captured, so it remains unknown. |
| `pub_03_binding_documented_attempt1.json` | 15.4 | Full tool documentation supplied; a completed-request call hit HTTP 429. Provider reported 7000 input tokens/minute, 4386 used and 4482 requested. No accepted plan or tool call. |
| `pub_03_binding_compact_attempt1.json` | 100.0 | Two valid planning requests, one successful search, one successful booking, and a confirmed final before the normal tail ended. |

All scores are supplied-scorer totals, not completion percentages. These are
exposed, single development runs; do not aggregate them into a success rate or
claim repeated reliability, multimodal quality, hidden-set performance or release readiness.
The successful configuration differs from the earlier failures; this is diagnostic
iteration, not an isolated ablation of the binding mechanism.

## Verified successful execution

The first plan pinned passenger Alice and delegated flight_id from its own
search call's `/flights` collection, uniquely matching `/depart` to the spoken
requested time normalized by the model as `08:00`. The contract was captured
before the search result. The second plan supplied that actual read call ID and
the selected `FL-DEN-8AM`. The controller independently checked the row, source,
request, dependencies, fixed mappings and authorization before dispatch.

Search dispatched at 1860 ms and completed at 3782 ms. Booking dispatched at
4922 ms, completed at 6250 ms, and produced the confirmed final at 6250 ms.
The harness's last user event is at 900 ms and standard tail is 6000 ms; no timing
extension was made. The final uses the existing confirmed-result formatter,
not a model success claim before the effect.

Three provider requests including warm-up: all successful, none cancelled.
Planning input counts were 3013 and 3615 tokens. This leaves little headroom
under the observed free-tier quota; larger requests, corrections and repeated
runs can still rate-limit. This is not a provider-wide quota guarantee.

## Configuration and provenance

- Official `time_scale=1`, unchanged tail 6000 ms and wall cap 120 seconds.
- Groq, temperature 0, output cap 950, input character cap explicitly 32768.
- Samsung partial debounce explicitly 1.0 seconds for this hosted test profile;
  default remains 0.08 seconds. A final arriving before the debounce canceled
  speculative work before a provider request; completed speech was not delayed.
- Documentation explicitly selected as `docs/TOOLS.md` inside the kit. Loader
  records exact full-file hash/bytes and strict UTF-8 provenance. The planner
  receives only verbatim `Success:` lines beneath headings naming runtime tools,
  with line numbers and a separate excerpt hash. Unknown formats keep the bounded
  full document. Missing layouts remain unknown; examples are never live results.
- Local Ollama retains its 4096-token/14000-character profile. No paid fallback
  or persistent environment change was configured.

Reports include Git base/dirty source evidence, runner/kit hashes, model telemetry,
plans and official traces. All are byte-identical copies of local originals;
`manifest.json` contains verified hashes. Configured API keys were scanned absent.
Raw kit source, scenario answer keys and media are not included.

## Reproduce a new attempt

Configure the same model/key/URL locally, then in PowerShell:

```powershell
$env:ACCESSFLOW_SAMSUNG_BACKEND = "groq"
$env:ACCESSFLOW_MAX_OUTPUT_TOKENS = "950"
$env:ACCESSFLOW_MAX_CONTEXT_CHARS = "32768"
$env:ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S = "1.0"
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_03_text_chained_booking.json --output artifacts/samsung/new-chained-attempt.json
```

Use a new output path; the runner will not overwrite evidence. Allow the provider
quota to recover between runs rather than retrying into a known exhausted window.
Still open: repeated text coverage, failed-read final latency, cancellation scenarios,
actual MP3/vision integration with Atishay, frame-conflict coordination, Docker,
security review of unrelated file boundaries and submission materials.
