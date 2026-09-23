# Compact-v2 evidence — 23 September 2026

Interpretation and reproduction: [profile report](../../COMPACT_INPUT_PROFILE_2026-09-23.md).

These files are byte-identical copies of local output, with SHA-256/lengths in
`manifest.json`. Configured credential values were checked absent before copying.
No organizer source, raw scenario files, model weights or private recordings are included.

| Artifact | Result |
|---|---|
| pub_02_compact_v2_2026-09-23_attempt1.json | Scorer89.6; all planning calls succeeded; useful correction/selection clarification |
| pub_02_full_2026-09-23_control1.json | Scorer89.6; third planning call rejected by provider quota |
| pub_03_compact_v2_2026-09-23_attempt1.json | Scorer100.0; one grounded mock booking; confirmed final6500ms |
| suite-first.xml | 1failed/1091passed/2skipped/1xfail; B session-isolation observation |
| suite-rerun.xml | 1092passed/2skipped/1xfail on unchanged source |

Three separate live development attempts are not three repetitions of each scenario.
The current default remains full. Provider timing/quota and model output can vary;
no broad completion percentage, latency improvement or submission readiness is claimed.

The first suite overlapped briefly with a hosted diagnostic process. The final rerun
did not overlap a provider attempt. Causality for the B timing observation is unproven;
read the separate [follow-up](../../reviews/ATISHAY_SESSION_ISOLATION_FOLLOWUP_2026-09-23.md).
Source hashes recorded by all three live reports match; reports correctly mark the
experimental source as dirty relative to the base commit `4b2908d`.
