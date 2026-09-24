# Merge/readiness evidence — 24 September 2026

Application code reviewed: `e7c95f576c5ba4713d27df9976301e0f451d0b07`.
Documentation added afterwards does not change the application under test.

- `full-suite.xml`: 1,197 passed, 2 skipped, 1 xfailed, 74.22 s. One complete run.
- `pending-frame-reproduction.xml`: four failing audit probes against that unchanged
  controller, 3.64 s. Separate from the passing standard suite; this is defect evidence.
- `pending_frame_probe.py.txt`: exact existing unfinished regression fixture recovered
  from the preserved local work, exported as review evidence. No repair applied.
- `probe-collection-error.xml`: first probe launch failed to import `test_safety` because
  it was moved outside tests/engine. This is a launch error, not product evidence.
- `offline-suite-report.json`: four scripted-reasoner/mock-tool development cases passed.
- `checks.json`: exact source, other checks and direct three-phrase semantic-stop probe.
- `manifest.json`: SHA-256 of the retained evidence bytes.

Reproduce the standard tests from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
node tests/demo/speech_lifecycle_check.cjs
.venv\Scripts\python.exe -m accessflow.cli suite scenarios/dev --output-dir artifacts/fresh-merge-audit
```

Reproduce the pending-frame defect without applying the unfinished repair. Use an
unused output filename/directory, copy the saved fixture there with a `.py` suffix,
then run from the repository root:

```powershell
Copy-Item docs/evidence/merge-readiness-2026-09-24/pending_frame_probe.py.txt artifacts/pending_frame_probe.py
.venv\Scripts\python.exe -m pytest artifacts/pending_frame_probe.py -q -o "pythonpath=. tests/engine"
```

Expected at the reviewed commit: four failures. Inspect the test and helper before
using these against a newer controller. No secrets, real bookings, real provider
calls, microphone sessions or vision inferences were used. JavaScript syntax parsing
used Node `--check` with the single inline script via UTF-8 stdin; the speech lifecycle
regression uses controlled fake browser objects, not physical audio output.
