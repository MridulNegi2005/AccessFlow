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
```

This is the canonical repository root. Organizer PDFs and prior research live outside
the repository in `../sources` and `../research`. Do not commit credentials, private
recordings or organizer materials without checking redistribution permission.

The internal protocol is v0.1, **not Samsung's unpublished wire schema**. Offline fakes
prove contracts and orchestration only. No live ASR, vision quality, official-kit score,
hardware latency or accessibility benefit is claimed by passing those tests.

Registration, hosted Git remote creation, publishing, final tag and submission are not
performed by the bootstrap. No API credentials are required for contract tests.
