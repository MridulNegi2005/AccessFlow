# Resolution record for the follow-up audit

Date: 16 September 2026
Answers: [MRIDUL_REAUDIT_2026-09-15.md](MRIDUL_REAUDIT_2026-09-15.md), baseline `30ed402`
Range: `30ed402..3354085` on `mridul/engine`

The audit asks that its findings keep their record instead of being overwritten. This file
adds evidence against each finding. It does not change the audit text.

## How to read the state column

- **Fixed**: the defect is reproduced, repaired and covered by a test.
- **Partial**: part of the finding is repaired and a named part is not.
- **Blocked**: the work is understood and assigned elsewhere.
- **Unmeasured here**: this machine cannot run the check at all.

## Measured state of the repaired tree

Measured at `3354085`:

- `uv run --offline --frozen --extra dev pytest -q` reports 411 passed, 0 xfailed.
- `uv run --offline --frozen --extra dev ruff check .` reports all checks passed.
- `uv run --offline --frozen accessflow suite scenarios/dev` reports 4 passed of 4.
- A clean export of `3354085` into an empty directory, then `uv sync --frozen --extra dev
  --offline`, reports 410 passed and 1 skipped. The skip was a test that read the ignored
  `artifacts/` directory. It now reads the committed evidence bundle instead.

No live model, ASR or vision inference ran during this repair work. Every number above comes
from offline execution.

## Finding by finding

| ID | State | Evidence |
|---|---|---|
| A1 clarification/image write intent | Fixed | `3e9f0dd`. `write_intent_retained` and `clarification_outstanding` replace one overloaded flag. Nine acceptance cases covered in `tests/engine/test_component_integration.py`. |
| A2 worker rejects vision options | Blocked | Ownership resolved in `docs/CONTRACT_PROPOSALS.md`. Mridul assigned the worker change to Atishay on 15 September. Workstream A finished its own side in `fdf4796`. |
| A3 audio task-effect oracle | Fixed | `fbd0d40`. The fixture is relabelled an ASR smoke check; a second fixture over the same recording scores write safety. Seven acceptance cases in `tests/engine/test_task_oracle.py`. |
| A4 evidence eligibility | Fixed | `fd53aca`. Per-run labels derived from trace content. Quality is 43 of 46. |
| A5 portable ordering | Fixed | `fd53aca`. Scrambling every file mtime in a copy of the bundle leaves the report byte-identical. |
| A6 profile verification | Fixed | `d917e19`. Row selection, endpoint export and per-profile commands repaired. Older traces report their unverified fields instead of failing. |
| A7 contradictory documents | Fixed | `f64c824` and `18721a5`. One authoritative status section per document, sourced to commands. |
| A8a canonical test command | Fixed | `bf441c0`. Both `pytest` and `python -m pytest` collect. |
| A8b malformed JSONL | Fixed | `ae7cd46`. Output over 245 recorded runs is byte-identical. |
| A8c relative inventory path | Fixed | `ae7cd46`. |
| A9 corpus | Partial | `aeca50b` closes the named defect. Retrieval is lexical and minimal. See below. |
| A9 remaining scope | Open | See below. |

## What is still open, and why

1. **A2, the vision path.** Assigned to Atishay by decision, not by directory rule. Until the
   worker accepts the options, no vision scenario runs through the process adapter.
2. **Scenario independence.** The corpus is 17 files over 10 distinct tool sets. Both audio
   files read the same recording, so audio coverage is one recording measured twice. More
   audio evidence needs more recordings. Recordings are Workstream B media fixtures. Files
   must not be generated to raise a count.
3. **Matched-timing baseline.** The audio path receives a whole file and a final transcript.
   It cannot measure whether the controller reduces premature responses. This needs end-of-
   speech latency beside wrong-action rate, under matched timing. That is a design change.
4. **Held-out probes.** Run once on 16 September 2026, after the contract stopped changing.
   All four passed on `groq/qwen/qwen3.8-27b`; the clarification probe committed zero
   effects. This is the first unseen-data evidence in the project. It is also the last from
   this set: the probes are now development data. Four text cases are a narrow sample and
   there is no unseen audio or visual case. Traces are in the ignored `artifacts/heldout/`
   directory and a clean clone does not carry them.
5. **Docker execution.** Unmeasured here. `docker` is not installed on this machine, so the
   container gate cannot be exercised at all. This is not a pass and not a failure.
6. **Official kit adapter.** Blocked on the organizer. Compatibility must not be claimed from
   the internal contract.
7. **Submission materials.** The deck, the recording, the disclosure and the tag are untouched.

## Scope limit of the corpus implementation

`Start.corpus` has a consumer and a security boundary. It does not have semantic ranking,
multi-passage citation, document size limits, or a real installed document directory wired
into the process and demonstration adapters. Those remain unimplemented by intent.

## Addendum: resolution of the second audit's M-series findings

The rows above answer
[MRIDUL_REAUDIT_2026-09-15.md](MRIDUL_REAUDIT_2026-09-15.md) as claimed at `3354085`. A
second audit, [MRIDUL_SECOND_REAUDIT_2026-09-16.md](MRIDUL_SECOND_REAUDIT_2026-09-16.md),
reviewed the repaired tree at `919ed27`, reassessed several rows above, and recorded seven
new findings, M1 through M7. This addendum records their resolution without changing the
table or the measured state above; those stay as they were at `3354085`.

Measured at `71b1bb5`, on branch `main`:

- `uv run --offline --frozen --extra dev pytest tests/engine tests/perception
  tests/test_contract.py -q` reports 543 passed.
- `uv run --offline --frozen --extra dev pytest -q` reports 635 passed, 19 failed,
  1 xfailed. All 19 failures are in `tests/demo/`, owned by Workstream B, and are tracked in
  `docs/INTEGRATION_NOTE_2026-09-16.md`. Three are `XPASS(strict)`: engine gaps that these
  repairs closed.
- `uv run --offline --frozen accessflow suite scenarios/dev` reports 4 passed, 0 failed.
- `uv run --offline --frozen --extra dev ruff check .` reports all checks passed.
- The evidence bundle's quality denominator is 43 of 49, not 43 of 46. A 429 no longer
  excuses a run whose model already generated output; three runs moved into the
  denominator. 57 attempted runs total.
- The four held-out planner probes ran once, on 16 September 2026, and passed 4 of 4 on
  `groq/qwen/qwen3.8-27b`. They are spent: development data now, not unseen evidence.

| ID | State | Evidence |
|---|---|---|
| M1 clarification fixture times out / rejects correct clarification | Fixed | `7b0d373`. |
| M2, M3, M5 corpus dispatch, unbounded I/O, external manifest-name collision | Fixed | `71b1bb5`. |
| M4 retrieved text can create write authority under the mock policy | Fixed | `6caa889`. |
| M6 success-then-429 misclassified as no-output | Fixed | `86655f0`. Evidence bundle is now 43 of 49. |
| M7 resolution record and current documents disagree | Fixed | This task. `docs/STATUS.md` and `.ai-sync/handoff.md` now carry one current snapshot each, sourced to commit `71b1bb5`, and no longer say the held-out probes have never run or that `Start.corpus` has zero consumers. Both documents now state the actual `SessionView` interface: it exposes `write_pending`; `write_intent_retained` and `clarification_outstanding` are controller-only attributes on the engine's session object, not view fields. |

Still open, named by owner and reason:

- A2 / B0, vision worker wiring — assigned to Atishay by Mridul's decision.
- The 19 `tests/demo/` failures — Atishay's.
- Matched-timing baseline and end-of-speech latency — needs Atishay's calibrated signal.
- Wrong-action-rate metric — not implemented.
- Security review over `corpus.py` — never run. That code, including the `71b1bb5` corpus
  work, is on the remote unreviewed.
- Official kit adapter — blocked on the organizer.
- Docker — not installed on this machine; the container gate is unmeasured, not passing.
- Submission materials: deck, video, AI disclosure, tag — untouched.

`corpus.py`'s file-access security assessment in the second audit (traversal/allowlist
boundary, resource limits, root-integrity assumptions, the untested symlink case and the
trailing-newline filename edge) is a separate, still-open item from M2/M3/M5. Fixing
dispatch, I/O bounding and discovery does not by itself constitute the security review that
item calls for.
