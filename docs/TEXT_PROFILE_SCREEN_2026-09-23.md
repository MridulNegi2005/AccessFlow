# Public text profile screen — 23 September 2026

Owner: Mridul. All six public text scenarios were attempted once on the same
implementation. Five scored100; the interruption scenario scored89.6. All18
provider requests succeeded. This is useful development evidence, not an official
aggregate, three-run median, hidden-set result or submission-ready declaration.

## Configuration and results

Engine commit7086d6e, source SHA256
`74880bbf4732929e7d2a2d955dc4063bfc6620e01668f685e00bd6fe10ca1bd4`.
Groq Qwen `qwen/qwen3.8-27b`, compact-v2, evidence read-answer mode, JSON mode off,
950 output tokens,32768 context characters,1.0s partial debounce, fast read retry.
Each existing single-case runner used time scale1, tail6000ms, setup cap300s and
scenario cap120s. Explicit tool documentation was supplied. External tools are mocks.

The six cases ran sequentially with70s between scenarios. No attempt was retried,
replaced, skipped or silently switched to a different model. The engine/model/
protocol implementation stayed frozen. Reporting-only tests ran during the screen;
these numbers are not an isolated hardware latency benchmark.

| Public case | Scorer | Outcome | Last text turn to substantive reply |
|---|---:|---|---:|
| pub_09 unfamiliar tool | 100.0 | Weather lookup; actual forecast and temperature fields | 2453ms |
| pub_08 tool failure | 100.0 | One exact read retry, then returned both flight options | 5547ms |
| pub_01 simple lookup | 100.0 | Chicago/Friday search, both actual options returned | 3703ms |
| pub_03 chained booking | 100.0 | One Denver search, one confirmed mock booking for Alice | 5953ms |
| pub_02 interruption | 89.6 | Cancelled Boston, searched New York, asked for missing booking details | 3781ms |
| pub_04 no-tool question | 100.0 | Ordinary conversational response; no tool calls | 718ms |

The latency column measures delivered final-text/interruption events to the next
final response or clarification. It excludes fillers. It is not measured physical
speech endpoint or microphone/audio playback latency. Scenario elapsed final times,
inputs, plans, tool ledger and provider timings are retained in the raw reports.

## Interruption trace: what actually happened

Boston read dispatched1703ms; interruption delivered1922ms; the harness recorded
`tool_cancelled` at2797ms, alongside the replacement New York search. Therefore
signal-to-observed-cancellation was875ms. The official harness records this as a
direct trace event, not a separate logged `action=cancel_tool`. The scorer awarded
full recovery, latency and safety points, but these broad categories do not by
themselves prove every implementation timing target.

New York read completed5016ms. At5703ms the agent asked which flight the user wanted
and the passenger's full name. It never emitted a booking. The scorer missed its
`final_nyc` checkpoint because this was a clarification, not a final response.
The user request did not provide a flight choice or passenger name, so changing the
agent to invent either merely to improve this score would be incorrect. The spoken
correction, preserved date, cancellation and new search are visible in evidence.

This timing includes semantic correction inference; it is not the same metric as
controller cancellation emission after an invalidation decision. No p95 or broad
interruption-reliability claim follows from this one sample.

## Quality and quota interpretation

The evidence-selected answers returned actual fields in the inspected lookups.
The booking still completed through committed tool evidence, and no-tool prose
still worked. The read-answer option did not replace an outstanding requested
write with a lookup-only final in the chained-booking case.

Limitations remain: field selection can omit relevant context or qualifiers,
clarifications are free-form, and these public cases are already exposed. The
confirmed booking reply is still JSON-shaped and awkward for voice. This screen
does not validate accessibility, clinical benefit, actual media perception or
naturalness of speech. No frontend or perception code changed.

All18 successful provider requests reported29112 input tokens in total, including
six warm-ups. The interruption case alone reported7392 inputs over its full run,
with no quota rejection. A rolling provider limit cannot be treated as a simple
static per-scenario ceiling;70s spacing and one successful screen do not prove quota
robustness in Samsung's consecutive three-repetition evaluation.

No default was changed: ordinary prose and the full prompt remain defaults. This
candidate needs repeated/comparative and broader modality evidence before adoption.

## Reproducible screening and reporting checks

`scripts/run_samsung_screen.py` launches the existing runner in separate processes,
requires an explicit supported backend/model and a fresh output directory, retains
failed attempts, records missing usage, detects source drift and does not calculate
an official aggregate. Each child retains the official in-scenario timing.

With explicit backend/model/credentials/profile already configured:

```powershell
uv run --offline --frozen python -m scripts.run_samsung_screen --kit ../participant-kit/participant-kit --scenarios pub_09_text_unseen_tool.json pub_08_text_tool_failure.json pub_01_text_simple.json pub_03_text_chained_booking.json pub_02_text_interrupt.json pub_04_text_no_tool.json --cooldown 70 --output artifacts/new-text-screen
```

The first reporting implementation missed the actual `clarification_request` name
and did not list direct harness cancellation events. Raw child reports always
contained them. Its original driver, plan, attempt records and summary are retained;
`reviewed-summary-final.json` extracts those events with the corrected summarizer.
No raw evidence was overwritten or a model scenario rerun to repair a summary.

Tests also found/reporting fixes covered malformed-report handling, preserving a
child-timeout reason and detecting source changes during the final child. The
initial8 tests produced7fail/1pass; final focused reporting/runner validation is
26passed in0.94s, Ruff clean. Nineteen of those tests are new. The final driver was
tested with controlled child-process doubles; the six live cases used the archived
initial driver. Do not conflate those sources. Implementation source was identical
for all six and remains the already full-suite-tested1144pass/2skip/1xfail checkpoint.
A new whole-repository suite was not needed for this reporting-only change.

## Next work and ownership

A: improve confirmed-action wording without inventing effects or discarding raw
result/call/operation evidence. Reuse bounded literal formatting after current
commit/reconciliation gates; never route writes through read-only selectors. Cover
uncommitted success, unknown outcomes, cancellation, late commit and reconciliation.
Then continue repeated/comparative official checks and packaging/platform work.

Both teammates coordinate any result-card or speech presentation adoption. Mridul
owns validated text/result/provenance and outcome rules; Atishay owns UI, voice
playback and perception. Media/timing, current B integration, Docker/native platform
and human submission materials remain separate gates. No release tag, workflow
activation, submission or real action occurred.

[Exact reports and hashes](evidence/samsung-text-screen-2026-09-23/README.md)
