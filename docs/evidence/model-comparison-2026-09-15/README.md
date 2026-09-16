# Model comparison evidence bundle, 15 September 2026

This directory holds the raw traces behind the Groq-hosted rows of
`docs/results/MODEL_COMPARISON.md`. It exists so a clean clone of this
repository can inspect the cited evidence and regenerate the published table.
The raw originals stay in ignored `artifacts/`. This bundle contains copies.

See `manifest.json` for the full machine-readable record. This file explains
the rules in plain language. `scripts/evidence_bundle.py` is the code that
derives each run's eligibility label from its trace; the manifest's
`eligibility`/`eligibility_basis` fields are that code's output, not a
separate hand-typed judgment.

## What is in the bundle

The bundle holds 57 run traces (`traces/**/*.jsonl`). Each file is a copy of
one run under `artifacts/`, with one change: known-sensitive text is redacted.
No file under `artifacts/` was modified or deleted to build this bundle.

## Cohort selection rule

A run is in the bundle only if it meets all of these conditions:

1. The backend is one of the four Groq-hosted models named in the "Current
   recommendation" and "Known provider limits" sections of
   `MODEL_COMPARISON.md`:
   - `groq/qwen/qwen3.8-27b`
   - `groq/openai/gpt-oss-120b`
   - `groq/openai/gpt-oss-20b`
   - `groq/qwen/qwen3.6-27b`
2. The scenario is one of the six `live-dev-*` text fixtures that back the
   per-scenario matrix: `development-text-correction-01`,
   `device-correction-before-plan`, `lost-response-status-reconciliation`,
   `support-read-then-service`, `stale-read-after-correction`,
   `stale-read-after-device-correction`.
3. The run is not part of the dependency-invalidation ablation (the
   `disabled_components` marker is empty). Ablated runs are a different
   condition and belong to `ABLATION_2026-09-15.md`, not this table.

Two things are deliberately left out, with a stated reason:

- **Local models** (`ollama/*`, `nvidia/*`). They run on different hardware
  and are already documented separately in `LOCAL_MODEL_2026-09-13.md` and
  `INFERENCE_TUNING_2026-09-14.md`.
- **Audio and vision live-dev fixtures** (`live-dev-audio-correction-01`,
  `live-dev-frame-device-panel-01`). That evidence belongs to the audio/vision
  end-to-end slice, which this task must not touch.

This is a defined subset, not a cache of everything in `artifacts/`. It
matches every claim the model-comparison table actually makes about
Groq-hosted models. It does not attempt to package the full 240-run corpus.

## Eligibility classification

Every run gets exactly one label. `scripts/evidence_bundle.py` derives it from
that run's own trace content: `classify_eligibility()` reads
`completion_status`, `task_oracle`, and `reasoner_evidence.requests`, and
returns a label plus a one-line basis quoting the evidence. Nothing here is
hand-typed. Re-running the function against the trace on disk reproduces the
same label; `tests/engine/test_evidence_bundle.py` checks that it does.

Two denominators matter and must not collapse into one:

- **Attempted-run reliability**: every one of the 57 runs, whatever the
  outcome. This is what `Runs` and `Completed` count in the scoreboard.
- **Model-output quality**: only runs where the evidence does not show the
  request was blocked before the model had a chance to respond. This is what
  `Oracle passed (quality)` counts.

A run leaves the quality denominator only on positive evidence it never
reached the model. Absence of evidence is not evidence of absence: a failure
with no captured status code or body does not prove the model was never
invoked, so it stays inside the quality denominator, counted as a failure,
rather than being excused from it.

A 429 is positive evidence of admission control only when nothing else in the
same run shows the model was invoked. A run that also recorded a successful
request (`outcome: "success"`), anywhere in its request list, was invoked
regardless of where that 429 falls; it keeps `generation_then_infra_failure`
and stays counted. The same applies to a failed request whose body already
shows the provider generated and then rejected output
(`scored_fail_generated_output`): a later 429 does not erase that evidence
either.

| Label | Meaning | Count | In quality denominator |
|---|---|---|---|
| `scored_pass` | Run completed; task oracle passed. | 43 | yes |
| `scored_fail_generated_output` | HTTP 4xx (not 429) carrying a `failed_generation` body: the provider rejected the model's own generated output. A genuine failure, not infrastructure. | 1 | yes |
| `generation_then_infra_failure` | A request in this run already succeeded (the model generated output) before a later HTTP 429 stopped the run from completing. Partial progress, not an admission refusal. | 3 | yes |
| `timeout_undetermined_cause` | Scenario-level timeout after one successful, fast model request and no further activity. The cause is not established by this trace alone, so it is reported as unresolved, and counted as a failure rather than excused. | 1 | yes |
| `undetermined_failure` | `HTTPStatusError` with no captured status code or body, failing in 0.17 s with zero tokens recorded anywhere. This is consistent with a connection failure before generation started, but it does not prove one: zero recorded tokens can also mean missing telemetry. Earlier drafts of this bundle called this label `infra_failure_unspecified` and excluded it from quality; that overstated the evidence, so it now counts as a quality failure like the other two undetermined-cause rows. | 1 | yes |
| `infra_admission_failure` | HTTP 429 from Groq (rate limit or request-too-large), with no request anywhere in the same run showing the model was ever invoked. The only label with positive evidence the request never reached the model. | 8 | no |

Quality pass rate: **43/49** (`scored_pass` over every label except
`infra_admission_failure`). This is a lower rate than the earlier published
43/46: three runs previously counted as `infra_admission_failure` had already
recorded a successful request before their 429 and are now
`generation_then_infra_failure` instead (see M6 in
`docs/reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md`). Nothing about the models'
behaviour changed; the earlier rule was excusing three attempts that the
evidence does not support excusing. Counting them drops the rate from 93.5%
to 87.8%. This bundle has no `unscored` runs (a completed run with no oracle
verdict); if one exists elsewhere, it is excluded from the quality
denominator too, for the different reason that no verdict was ever recorded
to count.

## Sanitisation

The orchestrator reported 16 traces containing the Groq organization id in
`reasoner_evidence.requests[].error_detail` (raw provider error bodies from
before the diagnostics fix in commit `ec8904a`, "Normalise provider errors
instead of storing the response body"). An independent scan of this
repository, excluding `.git` and `.venv`, for the pattern
`org_[0-9a-zA-Z]{10,}` found the id in 13 files under `artifacts/`: 11
`*.jsonl` run traces and 2 `report.json` summaries, all carrying the same
single value. No API key or bearer token was found in any file considered for
this bundle.

All 11 contaminated `*.jsonl` runs fall inside this cohort's selection rule.
They were **sanitised, not excluded**. Each carries a genuine HTTP 429 body
from Groq: 8 are `infra_admission_failure` (no earlier request in that run
shows the model was invoked) and 3 are `generation_then_infra_failure` (a
request in that same run already succeeded before the 429). Both are the
review's target: a failed-but-relevant run, kept rather than discarded. The
organization id is replaced with
`[REDACTED_ORG_ID]` wherever it appears. The substitution checks every JSON
line of every copied file, not only the 11 known files. This is a second
check, in case manual review missed something. The 2 contaminated
`report.json` files are hand-written run summaries. They are not
`run_metadata` traces that the scoreboard reads. They were not copied into
this bundle. They were not changed in `artifacts/`.

Verify the bundle directly:

```
grep -rlE "org_[0-9a-zA-Z]{10,}" docs/evidence/model-comparison-2026-09-15/
```

No output means no match.

## Regenerating the table from this bundle only

```
python scripts/model_scoreboard.py --artifacts docs/evidence/model-comparison-2026-09-15/traces --write docs/results/MODEL_COMPARISON.md
```

This command makes no provider calls, needs no API key, and reads nothing
under a user's local `artifacts/`. It only reads the 57 files under
`traces/` in this directory. Run it from a clean clone to confirm the
Groq-hosted rows of the published table.

The full table in `MODEL_COMPARISON.md` also carries the local-model rows
(`ollama/*`, `nvidia/*`), which are not in this bundle. Regenerating against
`artifacts/` (the default `--artifacts` path) reproduces the full table,
including those rows, but only on a machine that still has that local
evidence.

The scoreboard reads `manifest.json` automatically (it looks one directory up
from whatever `--artifacts` path it is given) to recover each run's
`selected_time_utc`, frozen at bundle-build time. A committed trace file's own
mtime is reset to checkout time by `git clone`/`git checkout`, so the live
filesystem mtime cannot order these 53 runs correctly after a checkout; the
frozen value in the manifest survives it and is used instead, joined by the
trace file's content hash rather than its filename or path.

## Regenerating just the classification

```
python -c "from scripts.evidence_bundle import recompute_bundle_report; import json; print(json.dumps(recompute_bundle_report('docs/evidence/model-comparison-2026-09-15'), indent=2))"
```

This recomputes `eligibility`/`eligibility_basis` for all 57 traces straight
from their content, independent of `manifest.json`. `manifest.json`'s
per-run `eligibility` and `eligibility_basis` fields are this function's
output, copied in; they are not a separate, hand-maintained judgment call.

## What this does and does not prove

- **Reproducible**: the scoreboard table's numbers for these 57 runs, from
  this bundle, with no provider calls.
- **Not reproducible**: the original model responses. These are hosted-API
  calls. Replaying them means sending the request again, at current
  provider behaviour and quota, not reading a cached response.
- **Not fully explained by `source_sha256`**: that digest hashes only `*.py`
  files under `src/accessflow/`. It does not cover `scripts/`, the dependency
  lockfile or `pyproject.toml`, or environment/`.env` settings. Two runs with
  the same `source_sha256` are not guaranteed to have run the same resolved
  configuration; check `resolved_config` and `commit` per run in the manifest
  instead of assuming the digest alone is sufficient.
- **Ordering**: 53 of these 57 runs predate `run_id`/`run_started_at`/
  `run_ended_at` (those fields were added partway through this cohort's
  collection). Their ordering falls back to a timestamp, never to a bare file
  modification time read at scoreboard-run time: a committed file's mtime is
  reset to checkout time by `git clone`/`git checkout`, so it cannot carry
  chronology across a checkout at all, copied onto the sanitised file or not.
  Instead, `manifest.json` freezes each run's `selected_time_utc` (the mtime
  observed once, at bundle-build time) and the scoreboard reads that frozen
  value, joined to the trace file by content hash. This survives a checkout,
  but it is still the original developer's machine clock, not a verified run
  timestamp -- the scoreboard labels it `(bundle-frozen mtime, order
  unverified)` on every affected row and tags any `Latest` verdict built from
  one `[order unverified]`, rather than asserting a chronology the evidence
  does not support. Ties are broken by trace file path, deterministically.
  The remaining 4 runs (`r1-live/qwen-device.jsonl`,
  `r1-live/qwen-support.jsonl`, `r2-live/qwen-reconcile.jsonl`,
  `r3-live/device.jsonl`) do carry a recorded `run_id` and UTC start/end time,
  which always outranks both the frozen and the live mtime fallback.
- **Declared hardware**: for these Groq-hosted runs, `declared_hardware` in
  the manifest describes the requesting client machine, not Groq's serving
  hardware, which the provider does not disclose.
