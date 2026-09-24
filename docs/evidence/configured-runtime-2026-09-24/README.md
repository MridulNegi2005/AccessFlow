# Configured runtime verification - 24 September 2026

All inference is fake. The child-process case exercises actual subprocess transport,
Samsung queue translation, the controller and reasoner schema validation, not model quality.

- first.xml: 51 passed before the expanded integration/profile/deadline tests.
- integration.xml: 1 failed, 61 passed. The new test used frame_ref instead of the
  official image_ref field. Corrected the test input; no protocol behavior weakened.
- focused.xml: final 62 passed in 1.95 seconds across test_configured_agent,
  test_samsung_package and test_samsung_runtime.
- full.xml: final 1243 passed, 2 skipped, 1 expected failure in 59.13 seconds.
- Repository Ruff passed. No B source or tests changed.

Commands: `.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/configured-agent-full-2026-09-24.xml`
and `.venv/Scripts/python.exe -m ruff check .`.
Focused run used the three named modules under tests/engine/ with pytest -q.

XML hashes cover exact retained bytes. Source hashes normalize CRLF to LF so Git
checkout settings do not alter their meaning. Source belongs to this report's commit;
the parent is e601c712700686da0a6dd09260c8b7941631173a. No live media/provider score,
clean install or Docker result is implied. Native package/MP3 work remains open.
