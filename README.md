# AccessFlow

A conversational agent prototype for unfinished speech, corrections and safe mock actions.
Samsung PRISM Theme 5; Mridul + Atishay. **Bootstrap in progress, not an evaluated submission.**

## Start here

- Atishay and his AI: [ATISHAY_START_HERE.md](ATISHAY_START_HERE.md)
- Current verified status: [docs/STATUS.md](docs/STATUS.md)
- Agreed plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Interfaces and ownership: [docs/CONTRACT.md](docs/CONTRACT.md), [AGENTS.md](AGENTS.md)
- Daily notes: [docs/handoffs/](docs/handoffs/)

Python 3.11 and `uv` are required:

```powershell
uv sync --extra dev
uv run pytest tests/test_contract.py
uv run pytest -q
uv run accessflow replay scenarios/dev/text_correction.json
uv run accessflow metrics artifacts/replay.jsonl
uv run accessflow suite scenarios/dev --output-dir artifacts/development-suite
```

This is the canonical repository root. Organizer PDFs and prior research live outside
the repository in `../sources` and `../research`. Do not commit credentials, private
recordings or organizer materials without checking redistribution permission.

The internal protocol is v0.1, **not Samsung's unpublished wire schema**. Offline fakes
prove contracts and orchestration only. No live ASR, vision quality, official-kit score,
hardware latency or accessibility benefit is claimed by passing those tests.

The public repository is https://github.com/MridulNegi2005/AccessFlow. Registration, final
submission tag and submission are separate human steps. No API credentials are required
for contract tests.

## Development profiles

The default replay is **offline-fake**: scripted reasoning, transcript pass-through and
mock external effects. It proves no ASR/vision capability. Explicit `--backend ollama`
or `--backend gemini` exercises actual reasoning while external tools remain fake.
See [docs/RUNNING.md](docs/RUNNING.md) for setup and model limits.

The engine branch contains offline contract/safety/metrics tests, four scripted development
workflows and model HTTP adapters tested with mocked responses. The suite checks confirmed
slots and actual mock effects; see [docs/EVALUATION.md](docs/EVALUATION.md). Atishay's audio,
image, turn-timing and demo implementation is still open. GitHub Actions remains disabled;
run the development checks locally.
