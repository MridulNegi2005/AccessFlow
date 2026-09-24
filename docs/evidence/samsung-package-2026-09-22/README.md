# Package verification evidence — 22 September 2026

See [the package report](../../SAMSUNG_PACKAGE.md) for reproducible setup, exact
scope, startup failure and repair, dependencies, ownership and remaining gates.

The original smoke report fails on speech before a manifest. The fixed report
passes stages1-2 using the rebuilt package in a fresh environment. The public
report is the unchanged output of the supplied run_local.py on one no-tool case,
scoring100.0 with its final at703ms. It does not contain per-request model telemetry;
the separate smoke report records live backend configuration and warm-up metrics.

The two package manifests pin the exact76 packaged files before/after the runtime
fix. They record dirty sources based on7fae2b6; they do not assert that the base
commit already contained the assembler or startup fix. Raw organizer source,
fixtures, answers and media stay in the ignored local package, not this evidence
folder. The documented dependency installation used public PyPI after an offline
cache miss. No fresh-machine or Docker claim is made.

package-validation.xml records the earlier1065pass run. The final startup suite
records1070pass/1skip/1xfail, two warnings in55.27s. Existing skip, frame xfail and
reported intermittent B issues remain open. All copied files are byte-identical
to their local originals and verified in manifest.json. Configured keys were
checked absent. The generated package itself has not been submitted or published.
