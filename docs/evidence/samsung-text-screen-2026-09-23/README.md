# Public text screen evidence — 23 September 2026

See [results, configuration, interpretation and reproduction](../../TEXT_PROFILE_SCREEN_2026-09-23.md).

All six raw `pub_*.json` reports share engine commit7086d6e and the source hash in
`manifest.json`. Each is one exposed public development attempt, using mock tools.
No aggregate or three-run median is claimed. No organizer fixture or answer key is
republished.

`driver-executed.py.txt`, `plan.json`, `attempt-*.json` and `summary.json` retain the
first driver's exact output. Its summary omitted clarification/cancellation fields;
raw child reports did not. `reviewed-summary-final.json` is the corrected extraction
and names the exact final summarizer hash. `driver-final.py.txt` preserves that
version; it matches the committed script. The earlier reviewed summary is also
retained with its own version hash. Nothing overwrote an earlier attempt.

Three focused test XMLs record reporting validation as the wrapper was hardened.
The release XML is26passed; the application source did not change during screening.
Known earlier application skips/xfail remain, not reclassified by reporting tests.

`manifest.json` hashes every retained report, test XML and driver snapshot. Configured
credential values were checked absent before copying; bytes are preserved through
Git checkout attributes. Interpret provider usage, substantive response latency and
scorer points separately, as explained in the main report.
