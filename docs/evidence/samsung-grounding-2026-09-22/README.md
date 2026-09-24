# Result-grounding experiments — 22 September 2026

**Both instruction variants failed. Neither was retained in production.** The
model still described an unqualified hotel `price_usd:189` as "$189 per night".
Samsung's supplied scorer gave both attempts100.0, because it checks result
keywords rather than this unsupported qualifier. This remains an A-owned quality
issue. Atishay's code was not changed or needed for these text experiments.

## Attempts and exact instruction additions

Base: `7fae2b6`, full hosted Groq Qwen `qwen/qwen3.8-27b`, generated development
fixture `gen_unseen_001.json` from seed20260922. Same profile as the preceding
unfamiliar-tool evidence:950 output tokens,32768 context characters,1.0s partial
debounce, fast retry, explicit tool documentation, official time scale1/tail6000ms.

Attempt1 added the following to the full system instruction:

```text
Summarize only facts supported by current successful results and interface definitions.
Preserve explicit units and qualifiers. Never infer a billing period, total, availability
or guarantee from a bare value or the user's requested duration. If a material qualifier
is missing, state that it is unspecified or clarify; do not silently supply it.
```

Its final still says "Harbor Inn at $189 per night", at4734ms. Planning input
tokens3162 and3502; three successful provider requests including warm-up, one
cancelled speculative request. No reported provider failures.

Attempt2 retained those lines and added:

```text
For example, amount_usd=120 supports "$120" with an unspecified basis, not "$120 per
month" or "$120 total". hourly_usd=30 explicitly supports "$30 per hour".
```

The same unsupported final phrase remained, at5015ms. Planning input tokens3211
and3536; three successful provider requests including warm-up, one cancelled
speculative request. No reported provider failures. Token accounting for cancelled
requests is unavailable. These sequential development experiments are not a
controlled ablation, repeated reliability measurement or a hidden-set result.

Equivalent condensed text was added to `compact-v1` but never live-tested. All
additions to both profiles were then removed; the source files match the base
commit. The experiment increases per-request overhead without demonstrated benefit.

## Validation and decision

Focused model/profile/informational tests:63 passed. A full run started against
attempt1 returned1047passed/1skip/1xfail,61.29s, two warnings. Attempt2's instruction
edit happened while that run was finishing, so this XML is not exact-final-source
certification. No tests prove these prompts prevent unsupported qualifiers.
Production has reverted to the already-validated base, not either experiment.

Byte-identical reports, original validation XML and hashes are retained here.
Configured credential values were checked absent before copying. No generated
fixture, organizer answers or source was republished. The prior baseline report is
in `../samsung-unseen-2026-09-22/gen_unseen_001_attempt1.json`.

Next A work: design evidence-linked claims or a separate answer verification path
with explicit missing-qualifier handling, and evaluate both unsupported and
explicitly supplied units. Avoid blanket unit removal, rewriting this particular
hotel answer, or treating a token-match score as factual certification. Any extra
model verification call must be measured against the observed quota and latency.
Submission-package import/setup validation is the next immediate engineering task.
