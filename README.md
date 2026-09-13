# AccessFlow

A conversational agent prototype for unfinished speech, corrections and safe mock actions.
Samsung PRISM Theme 5; Mridul + Atishay. **Bootstrap in progress, not an evaluated submission.**

## Start here

- Atishay and his AI: [ATISHAY_START_HERE.md](ATISHAY_START_HERE.md)
- Current verified status: [docs/STATUS.md](docs/STATUS.md)
- Agreed plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Interfaces and ownership: [docs/CONTRACT.md](docs/CONTRACT.md), [AGENTS.md](AGENTS.md)
- Daily notes: [docs/handoffs/](docs/handoffs/)

## Current progress

### Checkpoint 1 - 13 September 2026: perception foundation

Atishay's Workstream B has started on `atishay/perception`.

- Added `LocalPerception` for transcript pass-through and raw PCM WAV validation.
- Preserved utterance IDs, revisions, source event IDs and speech timestamps.
- Added an injected ASR seam for deterministic tests and a lazy Faster Whisper CPU INT8
  path that requires an already-installed local model.
- Kept blocking WAV and transcription work off the event loop with `asyncio.to_thread`.
- Image input is explicitly refused until a real replaceable vision provider is supplied;
  no canned caption is treated as perception.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest -q  -> 21 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/perception tests/perception
                                             -> All checks passed
```

The tests prove contract and adapter behavior only. No live ASR, vision quality, hosted
backend result or hardware latency is claimed yet. Next: turn timing policies, partial
transcript cases, a replaceable vision adapter and the minimal fake-agent demo.

## Checkpoint 2 - 13 September 2026: turn policy baseline

Added the first synchronous `HeuristicTurnPolicy` under Atishay's owned workstream.

- Final speech completes only when the observation is marked final; partial speech always continues.
- Explicit markers such as "actually" and "I mean" become `possible_correction` decisions.
- Repeated words remain ordinary speech unless a correction marker is present.
- Short acknowledgments such as "mm-hmm" become `backchannel` decisions.
- Older revisions cannot complete a turn when a newer observation is already present.
- The policy is deterministic, synchronous and model-free, so it does not block the dispatcher.

Evidence from this checkpoint:

```text
uv run --python 3.12 --extra dev pytest tests/perception -q  -> 13 passed
uv run --python 3.12 --extra dev ruff check src/accessflow/turn_policy tests/perception
                                                               -> All checks passed
```

The current contract has no timer or silence event, so this baseline does not claim acoustic
pause detection. Next: a replaceable PNG vision adapter with frame identity and evidence
metadata, followed by the minimal fake-agent demo.
Python 3.11 and `uv` are required:

```powershell
uv sync --extra dev
uv run pytest tests/test_contract.py
```

This is the canonical repository root. Organizer PDFs and prior research live outside
the repository in `../sources` and `../research`. Do not commit credentials, private
recordings or organizer materials without checking redistribution permission.

The internal protocol is v0.1, **not Samsung's unpublished wire schema**. Offline fakes
prove contracts and orchestration only. No live ASR, vision quality, official-kit score,
hardware latency or accessibility benefit is claimed by passing those tests.

The shared GitHub remote is being set up at the user's request. Registration, final
submission tag and submission are separate human steps. No API credentials are required
for contract tests.
