# Compact input profile experiment — 23 September 2026

Status: **opt-in `compact-v2`**, not the default. The full profile and package default
remain `full`; `compact-v1` retains its existing presentation. No provider/model switch,
quota workaround, automatic paid fallback or weakened controller check is introduced.

## Change

The new profile combines the existing compact instruction/schema presentation with
typed input-default elision. SessionView and ToolManifest use Pydantic serialization
with `exclude_defaults=True`; arbitrary user/tool dictionaries are never traversed
by a generic remove-empty filter. Consequently false, zero, null, empty lists/maps
inside tool arguments/results and slot values remain actual evidence.

The instructions explicitly describe omitted protocol defaults. Tests reconstruct
typed models and compare their full values, including uncertain writes, source IDs,
retry lineage, selection bindings and literal manifest schema values. Round-trip
equivalence establishes serialization meaning, not identical model interpretation.

Documentation text, relative source identity, selected line numbers and any unknown
metadata remain available to the planner. Known audit-only hashes/byte counts/encoding
metadata are omitted from the prompt, but preserved in the exported evidence.
The excerpt remains a separate untrusted documentation field, not a live result.

Local validation still checks the full original dynamic output schema: explicit plan
decisions, tool-name restrictions, unresolved-write restrictions and required progress.
No observations/results are truncated, no session history is replaced with a summary,
and no cross-session cache is added. Existing context limits remain unchanged.

Telemetry records protocol-data character counts before and after default elision,
alongside actual provider token usage and existing instruction/schema hashes. Character
counts are not token estimates. Output/cancellation behavior is not inferred from them.

## Live evidence

All runs used Groq `qwen/qwen3.8-27b`, temperature 0, output cap 950, context-character
cap 32768, partial debounce 1.0 seconds, fast read retry, explicit `docs/TOOLS.md`,
official time scale 1 and unchanged 6000ms tail. The credentials were loaded only into
child-process environment. `.env`, model choice, organizer scenarios and scorer were not edited.

The full control started over two minutes after the compact interruption report;
the chained run followed a further quota-recovery interval. These are sequential
public-development attempts, not randomized or repeated statistical comparisons.

| Run | Scorer total | Planning input tokens | Actual result |
|---|---|---|---|
| Interruption, compact-v2 | 89.6 | 2057 / 2423 / 2768 | All three calls succeeded; corrected search, then useful clarification at 5672ms |
| Interruption, full control | 89.6 | 3008 / 3373 / third rejected | Third call hit HTTP429: limit7000, used5865, requested3744 |
| Chained booking, compact-v2 | 100.0 | 2059 / 2656 | One search, one grounded mock write, confirmed final at6500ms |

Warm-up used49 input tokens in each run and is excluded from planning columns.
The first interruption request used31.6% fewer tokens versus this full control.
That reduction is for the combined compact-v2 profile, not default elision alone.
Its per-turn protocol serialization removed611,606 and648 characters respectively;
other reductions come from compact instructions/schema and audit-metadata omission.

The interruption clarification lists the two returned New York flights and asks
which flight and passenger name to use. It neither chooses a flight without the
required selection nor claims a booking. The supplied scorer's final-response check
does not count the clarification as a final answer, so the total stays89.6.
The full control instead emitted a model-failure clarification after quota rejection.
Equal scorer totals therefore do not imply equal useful responses.

The chained run retained result-binding authority and dependency checks, selected
the requested returned identifier, and reported success only after the mock result.
This is one passing exposed case, not full organizer compatibility or live bookings.

Compact-v2's successful interruption calls total7248 planning input tokens over the
scenario. The provider's rolling quota behavior permitted this particular attempt;
this is not a static guarantee of fitting every request sequence below7000 tokens.
Other users, timing, model outputs, retries and longer contexts can still exhaust quota.

Raw reports and hashes: [evidence bundle](evidence/samsung-compact-v2-2026-09-23/README.md).
Each report retains the actual source hash and dirty-worktree marker. The base commit
was `4b2908d` plus the now-recorded experimental source changes; source content stayed
unchanged across all three live runs. Tests were expanded separately during verification.

## Verification and remaining gates

Focused model/profile/documentation suites: **75 passed** in4.46s. Six new cases cover
typed/literal round trips, documentation provenance, dynamic schema restrictions and
explicit runtime selection without changing the default. A later fixture expansion
also covers delegated write-contract preservation and reconciliation instructions.

First full run: **1 failed,1091 passed,2 skipped,1 xfailed**, two warnings,102.22s.
The failure was the unmodified B-owned perception session-isolation timing test.
Three isolated runs passed in1.08/1.14/1.26s. It remains a reported observation,
not a defect claimed fixed by this profile. See
[Atishay follow-up](reviews/ATISHAY_SESSION_ISOLATION_FOLLOWUP_2026-09-23.md).
Repository Ruff passed. The final unchanged-source full rerun passed **1092 tests,
with2 skipped and1 xfailed**, two dependency warnings,85.48s. Both suite XMLs are
retained with the evidence bundle; a passing rerun does not close the earlier failure.

Keep the profile opt-in pending broader wording/tool coverage and the required repeated
official evaluation. The earlier unsupported hotel pricing qualifier is not addressed
by serialization and remains an open quality issue. No Atishay implementation, frontend,
workflow, release tag or submission changes are part of this experiment.

## Reproduce

With the existing declared provider configuration, set this in the test process only:

```powershell
$env:ACCESSFLOW_SAMSUNG_PROMPT_PROFILE = "compact-v2"
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_02_text_interrupt.json --output artifacts/samsung/new-v2-interruption.json
```

Use `full` for a control and `pub_03_text_chained_booking.json` for the second scenario.
Use new output filenames, retain every result and allow quota recovery between attempts.
Do not present the three different runs above as the official three repetitions of one case.
