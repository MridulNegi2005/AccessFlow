# Workstream A evidence and remaining work

13 September 2026. The ongoing goal covers Mridul's workstream only. Atishay's perception,
turn policy, UI, feedback and presentation ownership remains intact. Automatic CI is disabled.

## This slice

The offline safety suite and Ruff pass; exact current counts are in handoffs/mridul.md. Coverage includes:

- delayed perception after interruption and from superseded utterances;
- input origin IDs, detached policy/reasoner state and manifest copies;
- removal of superseded provisional slots and restoration of earlier confirmed values;
- frame-specific tentative state, cancellation recovery without repeating user instructions;
- operation IDs available through the public view, reconciliation and bounded safe retry;
- intentional new requests following failure receiving new operation IDs;
- session reset, deadline before start and partial-request coalescing;
- recorded input/output/executor/cancellation events, timeout traces and honest causal metrics;
- late committed effects after failure/cancellation and inconsistent response-status reporting;
- gated-worker responsiveness probes, raw timestamps and failure-aware p95 targets.

Tests are synthetic software evidence, not the 60 independently authored scenarios or a
claim about actual speech recognition. Four development workflows use mock tools and
scripted reasoning: date correction, support lookup then booking, device correction during
a pending write, and lost-response reconciliation. All four pass explicit confirmed-slot
and executor-effect criteria. They are development fixtures, not held-out cases.

## Requirements still needing work/evidence

| Requirement | Evidence now | Still required |
|---|---|---|
| Dynamic planning | Manifest validation, generic dispatch, provider HTTP tests | Real reasoning on unfamiliar schemas and held-out wording |
| Correct local corrections | Provisional rollback and source/race tests | More multi-slot/in-flight permutations and end-to-end model behavior |
| Action ledger | Duplicate handling, unknown-write block, reconciliation, safe retry tests and generic mock workflows | Broader conflicting-result/cancellation measurements |
| Responsiveness | Async workers, final bypass, causal traces and four-condition gated-worker benchmark | Reviewed measured run; real-model/resource-load, playback and speech latency |
| Evaluation | Typed traces, failure evidence, explicit missing values, task criteria against actual mock effects, four-case suite, source/scenario hashes | Full corpus, baselines/ablation, modality reports and held-out/live runs |
| Session isolation | Reused-agent reset and detached view tests | Provider/cache lifecycle tests under concurrent independent sessions |
| Local/hosted reasoning | Adapter code and mocked HTTP tests | No local Ollama service or configured Gemini key found; actual model runs pending |
| Packaging | Prior remote Docker build passed; missing-git runtime fix locally regression-tested | Corrected image execution on Docker-capable environment; no automatic CI restart |
| Official adapter | Explicit unimplemented marker, internal adapter | Organizer kit and public scenarios; don't invent wire compatibility |
| Submission | Repo, plan, setup docs, AI-use log | Human registration/template checks, artifacts, disclosure review and final tag/submission |

Known limits: the controller conservatively cancels pending writes on new input until
intent resolves. This can over-cancel for backchannels; Atishay's policy integration and
evaluation must quantify/refine it. Source provenance is tied to the plan trigger, not
fully grounded per-field attribution. No accessibility benefit or live-model score is claimed.

## Next independent A tasks

1. Preserve measured controller results, then evaluate real reasoning and resource-load behavior.
2. Expand independently authored cases using the mock environment and outcome checks.
3. Implement baseline/ablation comparisons without changing the shared inference/tools across variants.
4. Configure and measure a real reasoning backend; integrate B only after its components arrive.
