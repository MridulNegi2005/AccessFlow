# Merge verification evidence - 25 September 2026

Tested implementation: `dcd9756`, Mridul then Atishay merged into main.
Python 3.11.15 on Windows. Subsequent review commit adds documentation/probes only.

- `full.xml`: 1368 passed, 4 skipped, 1 xfailed, 82.13 seconds.
- `live-asr.xml`: opt-in installed Faster Whisper base.en CPU INT8, 2 passed,
  9.99 seconds. Generated fixture; Agent leg uses deterministic mock reasoning.
- `known-xfail-unmasked.xml`: deliberately reran the retained conflicting-frame
  case with `--runxfail`; failed at the conflict-seen wait. Not a new suite failure
  or evidence of an executed unsafe write.
- `offline-suite.json`: four developer scenarios, all passed with offline fakes.
- `checks.json`: actual commands, exits/stdout/stderr for probes, Ruff and four
  browser checks; tested SHA, Python version, raw local-checkout runtime hashes.
  Runtime hashes reflect Windows working-tree bytes, not normalized Git blobs.

Reproduce from repository root using the installed development environment:

```powershell
python -m pytest -q
$env:ACCESSFLOW_TEST_WHISPER_MODEL_PATH = (Resolve-Path models/faster-whisper-base.en).Path
python -m pytest tests/perception/test_live_worker_agent.py -q
Remove-Item Env:ACCESSFLOW_TEST_WHISPER_MODEL_PATH
ruff check .
node tests/demo/answer_correlation_check.cjs
node tests/demo/speech_lifecycle_check.cjs
node tests/demo/microphone_pending_check.cjs
node tests/demo/microphone_disconnect_check.cjs
python -m accessflow.cli suite scenarios/dev
python docs/evidence/merged-2026-09-25/probe_error_transport.py
node docs/evidence/merged-2026-09-25/probe_browser.cjs
python docs/evidence/merged-2026-09-25/probe_stop.py
```

The audit probes assert the **observed problematic behavior** so that they are
reproducible. They are not acceptance tests for the desired fixed implementation;
they should stop passing once the corresponding repair is made. The transport
probe uses the actual in-process WebSocket route and an injected ASR exception.
The browser probe extracts the real `show()` into a Node VM with synthetic events.
The stop probe uses the actual controller/policy with fake perception and a
scripted informational planner. None is a physical-microphone or live-model score.

The installed-ASR tests were the two opt-in skips from the full run. The other two
skips require native symlink support not available in this environment. The xfail
remains unresolved. No source tests were weakened to obtain these results.

No fresh hosted-model evaluation, live vision, package rebuild or Docker run is
represented by this evidence. See the dated review for remaining delivery gates.
