# Read-answer experiment evidence — 23 September 2026

This is an opt-in experiment, not a new production default or proof of universal
factual grounding. External actions are mocks. All reports are retained, including
intermediate implementations; no failed attempt is replaced by a later success.

## Protocol and interpretation

Hosted Groq `qwen/qwen3.8-27b`, JSON mode off, 950 output-token cap, 32,768 context
characters, compact-v2, partial debounce 1.0s and fast-read retry enabled. Hotel
runs use the same exposed generated development fixture `gen_unseen_001.json`
from seed20260922, supplied to Samsung's harness at time scale1/tail6000ms with
explicit tool documentation. Setup/scenario caps remain300/120 seconds.

The pre-change baseline is commit1a20938. Other reports record that base commit
plus dirty-source SHA256; their implementations differ as described below. These
are sequential development iterations, not matched repeated trials or a median.

- `baseline.json`: pre-change compact-v2, original prose path. Scorer100.0 but
  explicitly invents “$189 per night.” Planning input2122/2458 tokens.
- `evidence-attempt1.json`: first evidence selector; scorer100.0, no invented period.
  Planning input2130/2794. Repeated full field paths made the answer less readable.
  This version still permitted state updates on answer proposals; subsequently fixed.
- `synthetic-probes.json`: two exposed developer-authored direct-model probes,
  both passed. Explicit billing period, physical unit, false stock and zero fee
  survived rendering. Planning input1569/1575. This precedes the final answer-only
  state guard and is not final-source certification.
- `evidence-final.json`: answer-only schema/controller guards enabled; scorer100.0,
  no invented period, final4891ms. Planning input2126/2798. This precedes the final
  refinement suppressing invalid-answer clarifications during unfinished speech.

Each hotel attempt used two successful planning calls, one successful warm-up and
one cancelled speculative request. Cancelled-request token accounting is absent;
reported totals do not prove a permanent quota guarantee. The baseline and
experimental score being identical illustrates the scorer's factual-checking limit.

- `evidence-release-candidate.json`: final-source hotel run after the partial-speech
  refinement; scorer100.0, final4937ms, successful planning input2131/2793 tokens.
  It selects the actual record and outputs `Price usd: 189` without any billing
  period. The source hash is74880bbf4732929e7d2a2d955dc4063bfc6620e01668f685e00bd6fe10ca1bd4.
- `synthetic-final.json`: both developer-authored direct-model probes pass on that
  same final source, preserving an explicit billing period, physical unit, false
  stock and zero fee. These are reruns of exposed probes, never held-out results.

The final hotel's successful planning inputs total4924 versus4580 in the baseline
(7.5% more); it removes no inference roundtrip and adds no verifier roundtrip. Small
latency differences between individual runs are not evidence of a speed benefit.

## Validation and exact-source follow-up

First full suite:1143passed/2skipped/1xfail,64.65s, two existing dependency warnings.
The partial-speech refinement then added a regression test and prompted a new full
run:1144passed/2skipped/1xfail,65.71s, the same two dependency warnings.
Both suite reports are retained. Ruff is clean. Native Windows symlink privileges cause the
two skips; the existing conflicting-frame xfail remains. No B source/tests changed.

The synthetic script is `scripts/run_read_answer_probe.py`. It passes only user
questions, ordinary tool manifests and synthetic session results to the model;
expected strings stay local. It executes no tools, loads no credentials itself,
checks supplied units/literals, and records non-answer/failure cases. It is neither
a Samsung scenario nor an end-to-end conversation benchmark.

Current reproduction (credentials and explicit model configuration already set):

```powershell
uv run --offline --frozen python -m scripts.run_read_answer_probe --backend groq --profile compact-v2 --output artifacts/new-read-probe.json
```

Do not tune against these labels and later describe them as held out. The next
unexposed checks must assess relevance/completeness and other workflows, not merely
repeat this keyword assertion. The controller cannot invent new qualifiers in the
selected-field final, but the model can omit important fields or ask an ungrounded
clarification. Both limitations must remain visible in any results summary.

`manifest.json` provides byte hashes. Raw reports are copied without changing their
content. Source hashes establish which iteration ran; the suite XML alone is not a
live-model result. No organizer fixture/answer keys are republished.
