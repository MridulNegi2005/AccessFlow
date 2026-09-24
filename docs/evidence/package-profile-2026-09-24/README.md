# Explicit package profile verification — 24 September 2026

Base89f5407 with the accompanying builder/entry/test changes. Generated package
manifest records actual input hashes and source_dirty=true. No B/application
implementation changed in this slice; the package wrapper now freezes read mode.

Reproduction first failed2 checks / passed18: inherited evidence mode was not
rejected, and the builder had no explicit candidate profile selector. Final
package/runtime/read-answer checks87passed; Ruff clean. Seven regressions added.

Full suite:1failed /1194passed /2skipped /1xfail in59.38s. The failure is the same
vision-recovery mixed-media test reported during branch integration. It remains
open; no passing retry is substituted for this result. It uses unchanged demo and
controller source, not the modified package builder or entry wrapper. Root cause
and corrective responsibility still need the controller-level gated reproduction.

A generated compact-v2/evidence package was run with Python -I using the previously
verified isolated Python3.11 venv and identical21 dependency pins. This is not a new
clean installation. All78 packaged file hashes passed. Samsung package validation
and contract smoke had no errors. One chained-booking attempt scored100; exactly
one search and one mock write, final6375ms, explicit mock confirmation. Total8.218s
including validation/setup. Official scorer22ms latency is an early acknowledgment,
not the final response delay. No repeated official or audio/image quality claim.

Raw trace, exact verifier (rename .py.txt to .py to run), actual runtime profile,
package manifest and all suite XMLs are retained. The verifier receives a secret
through the environment only; credential literals were checked before publication.
Organizer kit assets stay in ignored artifacts, not this evidence folder.

Reproduce focused verification:

```powershell
uv run --offline --frozen --extra dev pytest tests/engine/test_samsung_package.py tests/engine/test_samsung_runtime.py tests/engine/test_read_answer.py -q
uv run --offline --frozen --extra dev ruff check .
```

Build command and mode semantics: ../../SAMSUNG_PACKAGE.md. Default full/prose
remains unchanged. Current wrapper requires a newly generated profile; existing
self-contained older packages have their own unchanged wrapper.
