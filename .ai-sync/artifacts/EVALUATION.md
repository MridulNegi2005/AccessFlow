# Development scenario evaluation

Run from the repository root after `uv sync --frozen --extra dev`:

```powershell
uv run accessflow suite scenarios/dev --output-dir artifacts/development-suite
uv run accessflow metrics artifacts/development-suite/scenario-001.jsonl
```

The suite writes one JSONL trace per case and `report.json`. A failed criterion or
setup error makes the CLI exit with code 1. Invalid cases remain in the denominator.
Cases without `expectation` are unscored; the suite then leaves the aggregate pass rate
null. A successful exit with unscored cases is not evidence that every task passed.

## What the current four cases exercise

| Fixture | Expected effect |
|---|---|
| `text_correction.json` | One Wednesday 17:00 appointment after a date correction |
| `support_then_service.json` | Read fictional support notes, then one device appointment |
| `device_correction_during_write.json` | Cancel the pending Panel-A write; commit Panel-B only |
| `lost_response_reconcile.json` | Recover a committed write through status lookup; one effect |

These are Codex-authored development fixtures with scripted reasoning and mock external
tools. They are not held-out examples, real Samsung documentation or live model results.
The current CLI uses transcript pass-through and the final-flag baseline; raw WAV/PNG
perception and Atishay's timing policy are not integrated into this runner yet.

## Independent fixture authoring

Copy a development JSON as a format example, then author new wording, manifests and
criteria. The internal schema is `evaluation/scenarios.py`; it is not Samsung's kit.

- `id`: stable safe case name; `provenance`: author, source, development/held-out status.
- `events`: one session start followed by inputs sharing a session ID. Use explicit event
  IDs when referencing steps. The loader assigns stable IDs if omitted; the runner sends
  session end itself. Partial revisions replace hypotheses for the same utterance.
- `event_spacing_s`: synthetic input pacing, not observed speech duration.
- `completion_timeout_s`: wait after scheduled inputs. Input pacing plus this wait must
  fit within the internal 114-second budget, leaving time for shutdown.
- `environment`: explicit tool-name-to-capability bindings. Capabilities are `lookup`,
  `write`, and `status`; tool names and parameter schemas can be unfamiliar to the engine.
- `proposals` or `reasoning_steps`: deterministic fake-model scripts. A step names its
  input and optional preceding tool statuses. Later matching steps override earlier ones.
  `{"$operation_of": "tool_name"}` resolves an operation ID from the public call ledger
  for a scripted status query. It does not inspect the executor's private effects.
- `expectation`: confirmed final slots, exact committed effects, final basis and/or
  expected error codes. Expected effects omit only the manifest's idempotency parameter.
- `terminal_output`: optional final/error/clarify/acknowledge criterion. By default the
  runner waits for a final caused by the last input; an earlier final cannot end the case.

Each run creates fresh state, reasoner and tool environment. No teammate needs the other's
running service. For actual held-out evaluation, keep labels undisclosed until the first
scored run and record authorship; do not relabel these tuned development cases as held out.

## Mock execution and outcome checks

Lookup bindings filter supplied rows using configured identity fields. Write bindings
validate manifest arguments and maintain an operation ledger independently of the agent.
They support delays, pre-commit failure and lost responses after commit. A status binding
reads that ledger and returns `committed`, `no_effect` or `unknown`.

The outcome checker compares expected effects against that executor ledger, including exact
semantic arguments and effect count. A fluent final response or an emitted tool call cannot
substitute for a committed effect. Duplicate deliveries, pending writes and unknown outcomes
are distinguished. Cancellation after commit is not rollback.

Malformed scenarios remain recorded as errors. Started runs preserve output on timeout,
early agent exit, Python exceptions and cooperative shutdown timeout; exception messages
are omitted to avoid saving provider details. Cancellation-resistant native code cannot be
forcibly terminated by this in-process runner and requires a bounded external worker.

## Backend and evidence separation

```powershell
uv run accessflow suite scenarios/dev --backend ollama --output-dir artifacts/local-reasoning
uv run accessflow suite scenarios/dev --backend gemini --output-dir artifacts/hosted-reasoning
```

Configure the selected provider as described in `RUNNING.md`. These options replace
scripted reasoning only; tools remain mock and perception remains transcript pass-through.
There is no automatic paid or alternate-provider fallback. Scripts and expected answers
are not supplied to the real reasoner. Every case gets a fresh backend wrapper.

Trace metadata records backend, configuration, Python/platform, commit when available,
worktree dirtiness, Python source SHA-256 and scenario SHA-256. Timings use `perf_counter`.
Missing speech-end timestamps stay null; do not call input-receipt timing speech latency.
Output reports are ignored by Git. Preserve selected reviewed results with their source
commit/configuration under `docs/results/` for submission later.

Still outstanding: the 60-case multimodal set, teammate-authored held-out labels, real
model runs, timing baselines/ablation, memory measurements and official-kit adaptation.

For a separate gated-worker controller timing benchmark, see [RESPONSIVENESS.md](RESPONSIVENESS.md).
