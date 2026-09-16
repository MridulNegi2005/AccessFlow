# Workstream A integration checkpoint — 13 September 2026

## Sources and scope

Combined Mridul c92a7da with Atishay d61d4dc in the isolated
`mridul/integration-d61d4dc` branch. The initial combined tree passed 137 tests.
All follow-up implementation changes are A-owned. Perception, turn policy, browser demo,
B tests and B handoff/provenance remain byte-identical to d61d4dc.
Atishay's README checkpoint narrative is preserved in WORKSTREAM_B_CHECKPOINTS.md.

## Reproduced problems and changes

Four new composition tests failed before the A controller fix: completed explicit
corrections could not resolve or clarify, injected raw-audio corrections stayed blocked,
and an image-only informational request produced no final. The controller now uses a
fresh semantic completion proposal to resolve final corrections, allows clarification
while unresolved and distinguishes informational image readiness from speech authorization.
Partials and image-only write proposals remain blocked.

Two additional regressions reproduced a model proposal that asks for clarification while
requesting a write. Writes now remain blocked in that proposal; a final correction stays
unresolved. All existing authorization, dependency and stale-result checks still apply.

The second review reproduced two cross-source gaps: an image plan could resolve unrelated
unfinished speech, or inherit readiness from an informational utterance. Correction
resolution now requires its speech source. Spoken write intent is tracked separately
from turn readiness and expires on new speech, interruption or a new request after commit.
Images can fill details for an existing spoken write request; they cannot invent that
request or reuse completed authorization. The independent authorization provider remains
required. Positive multimodal completion and completed-request nonreuse are tested too.

Replay and suite accept replaceable perception and policy components, creating fresh
instances per case. The CLI exposes `--components local` independently of the reasoning
backend. Traces identify component configuration and observed perception backend labels.
Missing raw-audio configuration fails rather than supplying a canned transcript.
No public schema or B implementation changed to force integration.

## Verification

- Python 3.11: `uv run pytest -q` — 151 passed, three dependency deprecation warnings.
- `uv run ruff check .` — passed.
- `uv run accessflow suite scenarios/dev --output-dir artifacts/integration-fake` — 4/4.
- `uv run accessflow suite scenarios/dev --components local --output-dir artifacts/integration-local` — 4/4.
- `uv build --out-dir artifacts/dist` — source distribution and wheel built.
- Isolated installed-wheel `--components local` suite — 4/4; imported module verified in site-packages.
- WAV/PNG routing tests use a synthetic tone/test pixel and injected provider callbacks.
  They are not speech-recognition or image-understanding quality evidence.
- Existing B tests are included in the total; no live ASR, vision or reasoning was run.
- These are developer-authored cases, not held-out or official-kit scores.

## Next Workstream A work

1. Bound native inference worker lifetime and concurrency. B's `asyncio.to_thread`
   keeps the dispatcher responsive, but cancellation does not stop the native call;
   Python shutdown can still wait for it. No real-media 120-second guarantee yet.
2. Configure and measure actual reasoning and a replaceable vision provider; keep explicit
   backend attribution. The CLI currently has no configured vision provider.
3. Complete broader scenarios, baseline/ablation comparisons and teammate-authored
   held-out evaluation. Four passing text fixtures do not substitute for the planned set.
4. Verify corrected Docker execution and warm-up on the declared supported machine.
   Official adapter remains dependent on the organizer's wire schema.

## Integration observations for Atishay

These are review items; B files were not edited:

- `demo/index.html` starts a new utterance and revision zero on each send. Sending a
  partial then its final must reuse the utterance ID and increase revision, as required
  by CONTRACT.md. Otherwise the browser does not exercise hypothesis replacement.
- `demo/app.py` queues session_end then immediately cancels its agent task. Use a bounded
  graceful wait before force cancellation when connecting real workers.
- PCM activity is currently a standalone helper; LocalPerception/HeuristicTurnPolicy
  do not consume activity timing. This checkpoint is not adaptive VAD/timing evidence.

GitHub workflow 357005144 remains disabled and YAML manual-only. No CI dispatched,
release tag, submission or participant contact occurred.

## New teammate input detected before publication

Atishay advanced to 2a4372a during this integration. This checkpoint deliberately merges
and tests d61d4dc only. The newer commits add a PCM replacement, timing summary and
illustrative speech fixture; his handoff reports Faster Whisper CPU INT8 measurements.
Those newer code changes and measurements are not part of this tested checkpoint and
must be reviewed next; do not treat this report's older B limitations as a fresh audit
of 2a4372a. The demo revision issue was reported against d61d4dc.

## Follow-up: checkpoint 2a4372a integrated

Merged the newer checkpoint without changing B-owned implementation. Combined tests:
159 passed; Ruff passed. The former audioop warning is gone; two test-client dependency
warnings remain. Both checked-in WAV hashes and durations match B's provenance report.
The generated speech ASR timing remains a teammate-reported measurement, not independently
reproduced here. The demo now waits up to one second for graceful agent shutdown; browser
utterance revision handling and real browser media input remain B work. Timing summaries
remain an offline helper; B's additive timing-contract proposal is preserved for review.
Next A work: the bounded subprocess perception adapter and runner lifecycle integration.
