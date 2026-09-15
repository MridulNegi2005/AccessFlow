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
