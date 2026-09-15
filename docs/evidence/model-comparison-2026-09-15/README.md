# Model comparison evidence bundle, 15 September 2026

This directory holds the raw traces behind the Groq-hosted rows of
`docs/results/MODEL_COMPARISON.md`. It exists so a clean clone of this
repository can inspect the cited evidence and regenerate the published table.
The raw originals stay in ignored `artifacts/`. This bundle contains copies.

See `manifest.json` for the full machine-readable record. This file explains
the rules in plain language.

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

Every run gets one label. The label decides whether a `backend_failure` counts
as a quality result or as an infrastructure result. The rule in the review was
"classify by specific evidence, not blanket exclusion," so each label below is
backed by a specific field in that run's trace, not by its scenario name.

| Label | Meaning | Count |
|---|---|---|
| `scored_pass` | Run completed; task oracle passed. | 43 |
| `infra_admission_failure` | HTTP 429 from Groq (rate limit or request-too-large) before any model output existed. | 11 |
| `scored_fail_generated_output` | HTTP 400, "Failed to validate JSON": the provider rejected the model's own output. A genuine failure, not infrastructure. | 1 |
| `infra_failure_unspecified` | `HTTPStatusError` with no captured status code or body, failing in 0.17 s with zero tokens recorded anywhere. Consistent with a connection failure before generation started. | 1 |
| `timeout_undetermined_cause` | Scenario-level timeout after one successful, fast model request and no further activity. The cause is not established by this trace alone, so it is reported as unresolved. | 1 |

`infra_admission_failure` and `infra_failure_unspecified` runs count toward
attempted-run reliability. They do not count toward oracle pass rates for
model quality, because the request never reached the model. The two other
failure labels (`scored_fail_generated_output`, `timeout_undetermined_cause`)
stay in the quality record, because the evidence does not clear the model of
responsibility for them.

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
They were **sanitised, not excluded**. Each is a genuine
`infra_admission_failure` (HTTP 429). The review asked to keep this kind of
failed-but-relevant run, not discard it. The organization id is replaced with
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
  collection). Their ordering falls back to file modification time, copied
  from the original `artifacts/` file onto its sanitised copy so the copy
  does not invent a false "just now" timestamp. This is still an unverified,
  best-effort ordering signal, not a recorded chronology, and the scoreboard
  output says so on every affected row. The remaining 4 runs
  (`r1-live/qwen-device.jsonl`, `r1-live/qwen-support.jsonl`,
  `r2-live/qwen-reconcile.jsonl`, `r3-live/device.jsonl`) do carry a recorded
  `run_id` and UTC start/end time and are ordered by that instead.
- **Declared hardware**: for these Groq-hosted runs, `declared_hardware` in
  the manifest describes the requesting client machine, not Groq's serving
  hardware, which the provider does not disclose.
