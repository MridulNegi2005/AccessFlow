# Public interruption development evidence — 22 September 2026

Three incremental runs of Samsung `pub_02_text_interrupt`, using live Groq
`qwen/qwen3.8-27b` and organizer mock tools. All attempted runs are retained.

| Attempt | Total | Outcome |
|---|---:|---|
| `pub_02_interrupt_attempt1.json` | 65.3 | Corrected search succeeded and stale search cancelled; spoken snapshots stayed Boston, filler repeated, final model call hit quota with no spoken error. |
| `pub_02_feedback_attempt1.json` | 84.3 | Corrected New York snapshot and acknowledgment, no repeated filler, honest processing-failure explanation. Early city acknowledgment still missed; final model call hit quota. |
| `pub_02_no_final_debounce_attempt1.json` | 89.6 | Finished correction no longer waits for partial debounce. Early city acknowledgment, current state, cancellation, latency and safety checks pass. Final useful answer still missing due to quota. |

These totals are supplied-scorer totals, not completion percentages. The latest
task fraction is 0.739; recovery, latency and safety fractions are 1.0. A score
increase is not a completed task. Every attempt encountered a final-request
HTTP 429; these failures remain open rather than being converted to canned finals.

## Latest trace

The first search dispatched at 1657 ms. The interruption appeared at 1922 ms.
The old search was cancelled and the accepted correction spoken at 2891 ms:
`Updated destination to 'New York'.` The same snapshot retains date `tomorrow`.
The new search also dispatched at 2891 ms and succeeded at 5094 ms. The model
request following that result failed, and a bounded explanation appeared at
5391 ms. No booking or other write occurred. No claim was made that the request
had completed successfully.

The observed interruption-to-updated-ack gap was 969 ms, versus 1782 ms in the
feedback-only attempt. Model/network times also differed, so this is not an exact
one-second latency experiment or a repeatable median. The deterministic tests
independently show that final corrections skip the partial debounce while partial
speech still waits for it.

Latest provider quota diagnostic: input-token limit 7000/minute, 5869 used,
3732 requested. Four model requests including warm-up: three succeeded, one failed.
The rate limit is measured account/model behavior, not a universal provider limit.

## Profile and provenance

Official clock scale 1, normal tail 6000 ms, wall cap 120 seconds. Hosted profile:
output cap 950, context-character cap 32768, partial debounce 1.0 seconds, fast
read retry enabled, explicit `docs/TOOLS.md` with verbatim return examples.
No environment-file modification, provider fallback, changed scenario clock or
organizer answer data supplied to the planner. Three distinct source checkpoints
are recorded by source hashes and Git base/dirty evidence; this is incremental
development, not a matched single-variable trial across all three runs.

Each report is a byte-identical copy of its local original. `manifest.json`
contains checked SHA-256 hashes; configured key values were scanned absent.
Raw organizer source, scenario files and media are not copied here.

To reproduce, configure the same Groq key/model/URL and the environment flags in
`../samsung-retry-2026-09-22/README.md`, then run:

```powershell
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_02_text_interrupt.json --output artifacts/samsung/new-interruption-attempt.json
```

Use a fresh output filename. Allow quota recovery between runs; do not mistake a
successful setup or search for end-to-end completion.

## Source validation and ownership

Final suite: **1029 passed, 1 skipped, 1 xfailed**, 2 dependency warnings,
53.64 seconds. New feedback/debounce tests: 8 passed. Ruff and diff checks clean.
The native Windows symlink privilege skip and existing conflicting-frame xfail
remain open; the separately reported intermittent B frame timeout did not recur
in either full run during this slice. No B-owned code, tests or handoff edited.

Implementation details: `../../CORRECTION_FEEDBACK_2026-09-22.md`.
Next A-side work is reducing repeated model-input cost without weakening
validation/provenance, then rerunning interruption and other public text cases.
Actual media paths and calibrated speech timing still require Atishay coordination.
