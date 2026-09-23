# Corpus boundary review status — 22 September 2026

Update, 23 September: the user resumed implementation. The completed scoped review,
repairs, reproductions and retained platform limitations are in
[CORPUS_BOUNDARY_REVIEW_2026-09-23.md](CORPUS_BOUNDARY_REVIEW_2026-09-23.md).
The original pause record below is historical, not the current review status.

Owner: Mridul. **Incomplete; no security closure claimed.**

A bounded read-only review was started after the package checkpoint. The user then
requested a pause at the next pushed checkpoint. The review worker was stopped
before a completed, accepted findings report was available. No reviewer findings
or test counts are claimed from that incomplete work; no source/test files were
changed in this checkpoint.

## Direct source observations

The inspected `src/accessflow/corpus.py` includes plain-filename validation,
Windows reserved-device-name rejection, per-session allowlist checks, resolved
path containment, file existence/size checks and normalized OS error codes.
It decodes UTF-8 with replacement and performs lexical retrieval on the resulting
text. Source inspection is evidence of implementation, not proof of every
boundary's behavior under race conditions or platform-specific filesystem rules.

`CorpusStore` explicitly assumes a trusted, immutable installation root and
contents. Its documentation states that hardlinks planted inside the root are
outside this assumption. Do not label that documented limitation as a newly
discovered session-controlled escape without a reproduction under the actual
supported threat model.

## Resume checklist

1. Review the actual corpus configuration/callers and establish which inputs are
   installer-controlled, session-controlled and model-controlled.
2. Run relevant existing tests and retain exact commands/results.
3. Verify traversal, reserved names, allowlists, resolved symlink/junction escape,
   file growth/size bounds, decoding behavior and sanitized error handling.
4. Distinguish defenses that depend on immutable installation from per-request
   guarantees. Test any required stronger invariant before proposing a repair.
5. Confirm retrieved prose cannot rewrite user permission or bypass current
   argument/source checks. Keep content authority distinct from filesystem access.
6. Record concrete findings with reproductions and file references; explicitly
   retain platform limitations and unverified checks.

This record is a pause handoff, not a passed audit. No additional review or code
work should run until the user explicitly resumes the goal.
