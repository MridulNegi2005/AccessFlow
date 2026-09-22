# Unfamiliar-tool development evidence — 22 September 2026

Four live hosted Qwen attempts completed with supplied scorer totals of100.0.
This demonstrates successful schema-driven dispatch for these exposed cases;
it is not a claim of perfect answers, hidden-set performance or release readiness.

| Retained attempt | Tool and arguments | Final at scenario time | Provider outcomes, including warm-up |
|---|---|---|---|
| `pub_09_unseen_attempt1.json` | `weather_lookup(city="Denver")` |3313ms|3 successful|
| `gen_unseen_000_attempt1.json` | `rental_car_quote(pickup_city="Miami")` |3969ms|3 successful|
| `gen_unseen_001_attempt1.json` | `hotel_search(city="Boston", nights=2)` |4609ms|3 successful,1 cancelled|
| `gen_unseen_002_attempt1.json` | `rental_car_quote(pickup_city="Boston")` |3469ms|3 successful|

These are one public case and three generated development variants spanning two
additional tool names. The generated cases are not held out. No per-case retries
or selection of best-of-many runs occurred in this set. The hotel and last rental
runs overlapped local test activity, so their times are not isolated benchmarks.
The hotel's cancelled request followed partial speech and was superseded; no
provider failure was recorded. Provider token use for cancelled requests is unknown.

## Manual review found a scorer blind spot

The hotel result supplies `price_usd:189`, without a pricing period. The final
adds **"per night"**, which neither the runtime manifest, result nor loaded tool
documentation establishes. The scorer accepts a hotel name, ID or price token;
it does not reject this unsupported detail. Mridul should improve generic
result-grounding instructions and evaluate claims beyond the current scorer.
Do not special-case this hotel or convert189 into a total/per-night price.

The rental result explicitly supplies `daily_usd:58`; saying "$58 per day" is
supported. Weather output contains the valid degree symbol in the stored UTF-8
JSON. A garbled terminal rendering was initially suspected to be model output;
inspection of the actual stored code points ruled that out. No trace was edited.

## Runner and source provenance

`--scenario-path` now explicitly accepts an existing external development JSON
fixture. `--scenario` retains its constrained public filename behavior. Exactly
one is required. Reports label their origin `external-development` or
`public-development`; both remain single-run live diagnostics with mock tools.
Fixture contents and answer keys go only to the supplied evaluator, never the
participant constructor or model. Agent media access stays rooted at the kit.

The public run used clean `33a9851` before the runner extension; generated runs
used that base plus the runner/test diff in this checkpoint. Each JSON preserves
source provenance and the runner hash. The runner extension does not change the
agent implementation. `manifest.json` hashes the byte-identical report copies,
both full-suite XML files, generated fixtures and generator. Raw organizer code,
answer keys, fixtures and media are not copied into the repository.

Profile: Groq `qwen/qwen3.8-27b`, full prompt, temperature0, output cap950,
context-character cap32768, partial debounce1.0s, fast read retry enabled,
explicit `docs/TOOLS.md`. Official time scale1, tail6000ms, setup cap300s,
scenario cap120s. Profile changes were child-process scoped. Configured
credentials were checked absent before copying. No provider fallback was used.

## Reproduction

With the supplied kit installed, run its generator from the kit directory using
the project's Python environment. Choose a new absolute output directory:

```text
python -m harness.scenario_gen --template unseen_tool --n 3 --seed 20260922 --out <absolute-output-directory>
```

Configure the declared hosted profile/key, then from the project directory:

```powershell
uv run --offline --frozen python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit --tool-documentation docs/TOOLS.md --scenario-path <absolute-output-directory>/gen_unseen_000.json --output artifacts/samsung/new-generated-attempt.json
```

Use fresh output paths and account for provider quota between cases. External
fixtures are deliberately not passed through the public filename selector.

## Software validation and ownership

Seven runner tests pass. Ruff passes. First full suite:1failed/1046passed/1skip/
1xfail; final rerun:1047passed/1skip/1xfail. The demo failure also reproduced in
one of three isolated attempts, so the green rerun does not close it. See
`../../reviews/ATISHAY_WEBSOCKET_CORRELATION_FOLLOWUP_2026-09-22.md` for evidence,
the unproven synchronization hypothesis and the explicit coordination split.
Atishay owns B demo repair; Mridul owns A provenance/runner/integration work.
No B source/tests were changed. The existing frame xfail and native symlink skip
remain unresolved/unmeasured, not passing safety evidence.
