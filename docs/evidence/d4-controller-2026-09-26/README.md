# D4 controller and package checks — 26 September 2026

These are development checks on Windows Python 3.11, not a submission or a
Docker/Linux result. The recorded native package was generated from clean source
commit `7cf33d94b92b4911df8e0fc8963081480ba65168` with `source_dirty=false`.
Its manifest SHA-256 was
`94fcaad9629de79351bfa75d8f4b0855380f98f2a26367f46ad054439a892516`.
The package itself lives under ignored `artifacts/` and includes organizer
materials and model weights; it is not published here.

| File | Result |
| --- | --- |
| `candidate-startup-timeout.json` | First 98-file candidate: hash/pin/import checks passed, but local service startup timed out before setup. |
| `candidate-setup-failure.json` | Second attempt: service ready, setup raised `RuntimeError` after 6.11 s. |
| `candidate-setup-success.json` | Third attempt: installed ASR, local vision and hosted reasoner setup succeeded in 65.28 s. |
| `clean-package-setup-success.json` | Exact clean-commit package: 98 file hashes and 37 installed pins verified; organizer import accepted; local service ready in 9.22 s and full setup succeeded in 56.39 s. |
| `pub03-old-context.json` | Normal-speed public text scenario under the old repository 14K default: 38.5/100; context-bound `ValueError` before later provider requests. |
| `pub03-expanded-context-quota.json` | Diagnostic 65K cap: 56.9/100; search completed, then HTTP 429 prevented the write/final. The committed hosted default is now 32K, as in the package. |

The JSON reports were checked against the locally configured Groq credential
before copying; none contains that value. They still reflect public development
scenario data and local runtime identity. Do not infer stable setup, passing
booking accuracy, successful real-image tasks or hidden-set performance from
these reports. `docs/reviews/CONTROLLER_D4_HANDOFF_2026-09-26.md` records the
test boundaries and B-owned integration work.
