# Merged main verification

Application commit8c609d9 combines Mridul c9136eb and Atishay ed9d581 in the
requested order. Source stayed unchanged through all checks; only documentation
was added afterward. All attempts are retained; do not infer the first failure
was fixed because later attempts passed.

- Initial full suite:1failed/1187passed/2skipped/1xfail,65.46s.
- Isolated failure test:four consecutive passes, each in a fresh pytest process.
- Final full suite:1188passed/2skipped/1xfail,55.42s.
- Ruff clean; inline JS parses; offline mock development suite4/4.
- Existing symlink-related skips and conflicting-frame xfail remain. Two existing
  dependency deprecation warnings remain. No live model or visual QA was added.

Commands:

```powershell
uv run --offline --frozen --extra dev pytest -q --junitxml=artifacts/merged-main-2026-09-24.xml
uv run --offline --frozen --extra dev pytest tests/demo/test_app.py::test_websocket_vision_failure_recovers_to_multimodal_session -q
uv run --offline --frozen --extra dev pytest -q --junitxml=artifacts/merged-main-final-2026-09-24.xml
uv run --offline --frozen --extra dev ruff check .
uv run --offline --frozen --extra dev accessflow suite scenarios/dev --output-dir artifacts/merge-dev-2026-09-24
```

Reports must use new paths for new attempts. The inline script was extracted with
HTMLParser and supplied to node --check as UTF-8 bytes; this checks parsing, not
rendering or microphone behavior. Source identity was compared against both branch
heads for the backend and B-owned trees; .github/workflows/ci.yml stayed unchanged.

See ../../INTEGRATION_2026-09-24.md for the unresolved recovery race and ownership.
