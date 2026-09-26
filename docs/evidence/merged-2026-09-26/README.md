# Merged verification evidence - 26 September 2026

Implementation merge ac187ba; Python 3.11.15 Windows. Reports are actual outputs.
Full suite: 1388 passed, 6 skipped, 3 xfailed, 77.87s.
Installed ASR: 4 passed, 28.20s; real base.en CPU INT8, generated audio, mock reasoning.
Unmasked D1: 2 failed, 1 passed. This intentionally reveals existing expected failures.
Offline suite: 4/4; fakes. Seven Node checks passed. Ruff and merge diff-check passed.

Commands from repository root:

```powershell
python -m pytest -q
python -m pytest tests/perception/test_confirmed_stop_semantics.py --runxfail -q
$env:ACCESSFLOW_TEST_WHISPER_MODEL_PATH = (Resolve-Path models/faster-whisper-base.en).Path
python -m pytest tests/perception/test_live_worker_agent.py tests/demo/test_app.py::test_websocket_configured_adapter_with_installed_asr_and_mock_reasoner tests/demo/test_app.py::test_websocket_reconnect_with_installed_asr_starts_fresh_session -q
Remove-Item Env:ACCESSFLOW_TEST_WHISPER_MODEL_PATH
ruff check .
python -m accessflow.cli suite scenarios/dev
```

Node commands/exits are in checks.json. The four model skips were run separately;
two native-symlink skips remain environment-limited. The three xfails are two D1
stop behaviours plus historical conflicting-frame acceptance. No real hosted
reasoning, live vision, physical microphone, Docker or official score is certified.
See ../../reviews/MERGED_REVIEW_2026-09-26.md for scope and ownership.
