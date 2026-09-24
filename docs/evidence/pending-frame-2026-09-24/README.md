# Pending-frame guard evidence — 24 September 2026

Final source starts from `749fe23` plus the three owned files hashed in manifest.json.
Raw pytest reports retain exact bytes. No real model, microphone or official-score run.

| Report | Result / meaning |
|---|---|
| expanded-baseline | 5 failed, 8 passed against the unfinished patch; drove failure/readiness fixes |
| expanded-fixed | 13 passed after those changes |
| focused | 1 failed, 16 passed; overly strict no-output assertion found a legitimate read-evidence acknowledgment |
| focused-final | 17 passed after asserting no final/write while allowing that acknowledgment |
| integration | 1 failed, 991 passed, 2 skipped, 1 xfailed; old partial-image rollback fixture needed the completed-image/partial-speech setup |
| focused-release | 25 passed across pending-frame and source ownership; includes timeout and shutdown additions |
| full | 1,216 passed, 2 skipped, 1 xfailed, 71.49 seconds; final application source |

Ruff and git diff whitespace checks passed. B-owned source and tests have no diff.
Two dependency deprecation warnings remain. Skips/xfail are not claimed as passes.
The separate original-main four-failure reproduction is retained in
`../merge-readiness-2026-09-24/`.

Reproduce from repository root:

```powershell
uv run --frozen --extra dev python -m pytest tests/engine/test_pending_frame.py tests/engine/test_source_ownership.py -q
uv run --frozen --extra dev python -m pytest -q
uv run --frozen --extra dev python -m ruff check .
```

The final suite ran on the existing Python 3.11 Windows environment. It does not
certify Docker, actual ASR/vision, browser microphone behavior or submission readiness.
