# Experimental compact planner profile — 22 September 2026

Status: opt-in experiment, not the default and not a verified performance improvement.
`ACCESSFLOW_SAMSUNG_PROMPT_PROFILE=compact-v1` selects condensed instructions and an
annotation-free presentation of the generated output schema. Default `full` retains
the previous instructions and schema presentation. No provider or model is switched.

## What changed and what stayed enforced

The compact profile removes generated schema annotations only at recognized schema
positions: titles, descriptions, defaults, examples and comments. Property names
and literal const/enum data are preserved, including names such as `description`
and `title`. Manifest descriptions, user observations, session state, tool results
and documentation evidence are unchanged. The original full schema is still used
for local validation, regardless of what the provider enforces. No accepted-plan
or controller authority check is relaxed.

The condensed instruction block is a separately versioned presentation of planner
guidance. Its semantic quality requires model evaluation; equal schema enforcement
does not prove equal understanding. No truncation or missing evidence is used to
force a request under the context cap.

Static no-manifest measurement: instruction plus schema characters fall from
8436 (4503+3933) to 4921 (2704+2217), about 42%. This excludes session/manifest data
and is not a token count. The live initial request used 2321 input tokens versus
3004 in the previous full-profile interruption attempt, approximately 23% less.

## Retained failure: pub_02_compact_prompt_attempt1.json

Supplied scorer total **84.3**, task fraction **0.609**. The corrected New York
search completed, with recovery, latency and safety fractions 1.0. The early city
acknowledgment and final useful response were absent.

The initial plan failed validation at
`write_contracts[0].delegated_arguments[<key>].match_slots`. The diagnostic records
a constraint category but does not retain the rejected value; do not infer the
exact bad value from that path alone. The bounded retry was then superseded by
the user's interruption. The corrected request produced a valid search. The final
planning request hit HTTP 429: observed ITPM limit 7000, used 6555, requested 2920.

Five provider requests including warm-up: two succeeded, two failed, one cancelled.
Cancelled requests may already have consumed provider quota. No Boston call was
dispatched, so the later New York value was an initial accepted slot rather than
a change to an existing accepted slot; the correction acknowledgment path did not
fire. This is another case for future feedback coverage, not evidence of a wrong
state or an unsafe obsolete call.

This single exposed development run is not a matched statistical comparison, a
completion percentage, a quota fix, or a reason to adopt the compact profile by
default. The full-profile latest interruption attempt scored 89.6; that report
remains in `../samsung-interruption-2026-09-22/`.

## Reproduce and inspect

Use the existing declared Groq Qwen configuration, output cap 950, context-character
cap 32768, partial debounce 1.0 seconds and fast read retry enabled. Add:

```powershell
$env:ACCESSFLOW_SAMSUNG_PROMPT_PROFILE = "compact-v1"
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario pub_02_text_interrupt.json --output artifacts/samsung/new-compact-attempt.json
```

Official time scale 1, unchanged tail 6000 ms and wall cap 120 seconds. Use a fresh
output filename and allow quota recovery. Environment settings were scoped to
the test child process; `.env` was not modified. No paid or alternate-model fallback.

The report records actual prompt profile, bounded per-plan input character counts,
instruction and presented/enforced-schema hashes, model telemetry, source/runner/kit
provenance and official trace. Measurements are initiation records, not proof that
every request reached the provider. The list holds at most 128 latest plans and
excludes warm-up. No instruction or session content is copied into those measurements.
The report itself separately retains the existing controlled public trace and plans.

`manifest.json` records the report's verified hash; the copy is byte-identical to
the local original and configured key values were scanned absent. Organizer source,
raw scenario files and media are not copied.

## Validation and next work

Full suite: **1038 passed, 1 skipped, 1 xfailed**, 2 dependency warnings in
64.86 seconds. Nine new profile tests; the focused model/validation suite passed
83 tests. Initial test setup used invalid manifest fixtures (corrected); a legacy
no-content telemetry check caught a metadata-key naming collision (renamed). No
existing tests were weakened. Ruff and diff checks pass. The prior Windows privilege
skip, frame xfail and intermittent B timing issue remain open.

Next: improve binding-selection instructions and evaluate multiple scenarios before
adopting any compact profile. Investigate retained redundant input with explicit
schema/provenance guarantees, not silent omission. Separately fix informational
follow-up suppression after a prior completed write. No B implementation changes.
