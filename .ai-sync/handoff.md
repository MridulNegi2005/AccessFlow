# Active Handoff

## Merged readiness and ownership handoff — 24 September 2026

Merged Mridul 0c12ba0 into main first (c564754), then Atishay 8083ebf (e7c95f5).
Three documentation conflicts resolved with both work histories and newer design status
retained; no application source conflict or repair. B implementation matches his fetched
branch. Standard suite1197pass/2skip/1xfail in74.22s; Ruff, inline JS, Node speech lifecycle
and offline4/4 pass. Separate gated audit probes reproduce four pending-frame controller
failures; do not call the merged agent defect-free or multimodal-ready.

Read docs/reviews/MERGED_READINESS_2026-09-24.md, ATISHAY_VOICE_WORK_2026-09-24.md
and ATISHAY_AGENT_PROMPT_2026-09-24.md. They separate A/B work, actual Samsung criteria,
C24-1..5 coordination and real media acceptance tests. Frontend polish/Stitch exports are
deferred. Historical 18 generated-audio ASR measurements are acknowledged; the newest UI
uploads on stop, but streaming/barge-in and a common real runtime remain open.

Unfinished pending-frame engine/test work was saved in stash object
feb6af1643ee7ad11ca6d2cf8473dcde1183fd36 before merging; excluded from main. Restore on
Mridul's branch after this documentation checkpoint. Finish/review/test it separately.
The last explicit pause stopped that implementation; the current request authorizes this
merge, review and handoff. No implementation fix or new live evaluation in this slice.
Next A: pending-frame correctness and configured Samsung media runtime; next B: owned
correlation/timing, real ASR/vision/microphone tests. Both coordinate shared contracts.
No release tag, submission, workflow activation, model downloads or external messages.

## Atishay ASR evidence checkpoint — 2026-09-24

On `atishay/perception`, B added an opt-in direct-model ASR probe in owned
perception code. Actual local Faster Whisper base.en CPU INT8 runs on three
generated WAVs retained segment/word offsets and raw decoder estimates;
`docs/feedback/ASR_MEASUREMENTS.md` has provenance, hashes and timings. This
does not feed the agent and is not a physical microphone, human-speech,
calibrated-confidence or official Samsung result. Owned tests: 376 passed,
1 retained xfailed; full suite: 1208 passed, 2 skipped, 1 retained xfailed;
Ruff clean. The shared Observation still lacks uncertainty and timing fields.
Both teammates must settle C24-1/2 clip/utterance timing, clock mapping,
revision/finality, uncertainty and output-stop effects before integration.
Mridul's runtime factory remains unmerged into this checkout; C24-3/4/5 and
the original participant kit are still open. See B handoff for exact next
steps; no A-owned source or configuration changed.

## Current checkpoint — 2026-09-24

Branch `atishay/perception`; the last verified pushed baseline before this continuation was `508d29d`. The approved voice-first shell is implemented in owned `demo/index.html`; the current delta and behavior are documented in `docs/design/IMPLEMENTATION_REPORT_2026-09-24.md`. The old task-dock specification is marked superseded, not erased. See Git for the moving branch HEAD.

Verification: `.venv/Scripts/python.exe -m pytest -q` → 812 passed, 1 existing xfailed, 2 dependency warnings; owned demo → 127 passed, 1 xfailed. Repository Ruff, `git diff --check` and inline JavaScript parsing pass. Real local Edge checks at 1536×1024, 1440×900, 1280×720, 768×1024 and 390×844 reported no horizontal overflow. The in-app browser inspected the new photo and meeting previews and confirmed the mobile meeting card no longer collides. The photo enlarge button was reproduced broken and then verified working, including at 390×844; a long live `demo/mock` answer now retains its complete content as body copy rather than an oversized heading. A controlled Node.js regression proves stale browser-TTS callbacks are ignored after replacement/cancel, but audible speech remains unverified. A PNG fixture showed conditional send and remove behavior. Browser screenshots in `artifacts/accessflow-*.png` predate these latest checks; current screenshots were inspected in the task but not saved as Stitch assets.

No engine, shared contracts, adapters, root config/lockfile or `docs/STATUS.md` were changed. Implementation commit `f0ca543` was pushed to `origin/atishay/perception` and verified; no deployment or Stitch publication occurred. Physical microphone permission, live ASR/endpointing/barge-in, speech-synthesis playback and screen-reader combinations remain unverified.

Stitch prompts 1–5 were run in project `12923345623703202409`. The project is accessible in the in-app browser and the two anchor frames were inspected, but they remain 1280×1033 and 1280×1025. The two approved PNGs and full `DESIGN.md` were not attached, and no native export could be verified after two ZIP attempts. Exact manual export steps are in `docs/design/stitch/README.md`; local browser screenshots and the newly generated illustrative sample photo are not represented as Stitch assets. The demo now has read-only dog-photo (`/?preview=photo` or `1`) and corrected-meeting (`/?preview=meeting`) compositions, not live action evidence. Atishay and Mridul still need to coordinate shared transcript/action identity, causal frame/answer correlation and speech timing/interruption semantics.

This work did not modify `docs/STATUS.md` because `AGENTS.md` assigns that file to Mridul.


## Retained Mridul integration history

## Explicit package read mode — 24 September 2026

Reproduced/fixed an inherited environment changing package read-answer behavior
without profile conflict. Builder now explicitly selects prompt/read modes and the
entry validates/freezes both before environment mutation. Defaults remain full/prose;
compact-v2/evidence is selectable,not silently promoted to release configuration.

Focused87passed; Ruff clean. Full1failed/1194passed/2skipped/1xfail in59.38s: the same
merged demo vision-recovery ordering failure recurred; unchanged B/controller code,
no rerun-to-green. A controller readiness review/gated reproduction is next; do not
claim this media race closed. No B source/test changes in this slice.

Generated candidate package passed isolated import/hash/contract checks and one
live Samsung booking100 (one search,one mock write,final6375ms). Reused the verified
Python3.11 environment/21pins; not a new clean install or repeated score. Evidence:
docs/evidence/package-profile-2026-09-24/README.md; usage docs/SAMSUNG_PACKAGE.md.
Goal active. Continue A-owned pending-media diagnosis/runtime work. MP3 bridge
ownership still awaits user answer. Push own branch only; main stays at merged89f5407.

## Combined branch checkpoint — 24 September 2026

Merged Mridul c9136eb into main first (a40cffd), then Atishay ed9d581 (8c609d9).
Only .ai-sync/handoff.md conflicted; both histories retained. No application conflict
or source repair. B-owned source/tests remain identical to Atishay's branch.

Final combined suite1188pass/2skip/1xfail in55.42s; Ruff clean,JS syntax passed,
offline dev4/4. Initial suite had1 failure in vision-failure recovery (image context
absent from first audio final); four isolated repeats and final suite passed with
unchanged source. This is an open timing/correlation issue,not fixed or established
as a merge regression. Both full reports and repeats retained. See
 docs/INTEGRATION_2026-09-24.md and docs/evidence/merge-main-2026-09-24/README.md.

Push verified merged main; fast-forward Mridul's branch for continued owned work.
Do not update Atishay's branch or reinterpret old branch-specific evidence as new
combined-tree live verification. Workflow unchanged/manual-only; no deployment/tag.
Goal active. Next A work remains runtime/profile configuration, coordinating the
pending MP3 ownership decision and the documented multimodal ordering follow-up.

## Isolated package validation and media follow-up — 23 September 2026

Built a clean cd53bc2 base package (78 files), installed all21 pinned dependencies
into a new Python3.11.15 environment from cached wheels, verified hashes/import
location under Python -I and passed dependency consistency. Samsung validation and
contract smoke returned no errors; one no-tool text run scored100 with final735ms.
This is the same Windows host, full/prose profile; not a clean machine, Docker,
repeated score or media validation. Docker command is unavailable in PATH.
Evidence: docs/evidence/samsung-clean-install-2026-09-23/README.md.

Source inspection confirmed the worker already accepts vision flags: old rejection
notes are stale. Samsung's factory still configures no real ASR/vision; MP3 events
remain rejected, and vision via the process worker requires an installed ASR path.
Read docs/SAMSUNG_MEDIA_NEXT_2026-09-23.md for the exact A tasks and B seams.
User ownership question for the MP3 bridge remains pending; do not infer approval.
Continue independent runtime/profile work; do not fabricate model paths or edit B.
Goal active. No application source changed since the verified confirmation slice;
no repeated full suite is claimed for these evidence/docs-only changes.

## Readable confirmation checkpoint — 23 September 2026

Confirmed writes and reconciled committed effects now provide bounded literal text
while preserving raw evidence/call/operation IDs. Mock-only runtimes explicitly say
"mock action" from trusted authorization metadata, never from model/result guesses.
Unknown, cancelled, failed and invalidated outcomes keep existing gates. Unsupported
or oversized details produce an explicit summary omission without a second action.
No B source/tests changed; cards/playback remain B-owned coordination work.

Final full suite: 1186 passed / 2 skipped / 1 xfailed in 64.47s; focused 23 passed;
Ruff clean. Final-source live Samsung booking: 100, all 3 provider calls successful,
one read/one mock write, final at 6407ms (5500ms after last text-turn input). This is
one development attempt, not repeated official or voice-usability evidence.
Both intermediate and final traces/suites retained with hashes. Read
CONFIRMATION_TEXT_2026-09-23.md and evidence/confirmation-text-2026-09-23/README.md.

Next A: repeated Samsung/profile evidence and final profile selection, A-side media
integration with B, clean-install/platform/Docker verification and submission assembly.
Compact/evidence defaults remain opt-in. Goal active; completed checkpoint pushed
using configured identity, no workflow changes, release tag, submission or real effects.

## Six-case public text screen — 23 September 2026

Screened all six public text cases once on frozen7086d6e implementation with
compact-v2 and evidence read answers. Five scored100; interruption89.6. All18
provider requests succeeded,29112 reported input tokens including six warm-ups.
These are exposed development attempts, not an official aggregate or three-run median.

The interruption trace confirms Boston cancellation875ms after the signal, followed
by New York search and a request for missing flight/passenger details. No booking
was invented. The chained case made exactly one confirmed mock booking. Substantive
text-turn response delays ranged718–5953ms; filler latency is a different metric.

Added a sequential screen driver with failure retention, fresh output paths,
explicit model configuration and source-drift detection. Corrected summary extraction
for official clarification/cancellation trace names; all original raw reports and
the first driver remain retained. Final focused reporting tests26pass, Ruff clean.
No application source or B source/tests changed. Existing1144pass/2skip/1xfail is
previous engine evidence, not a newly run full suite for this reporting-only slice.

Read docs/TEXT_PROFILE_SCREEN_2026-09-23.md. Defaults remain full/prose. Next A work:
make confirmed-action replies readable for voice while preserving committed/unknown/
cancelled outcome gates and raw provenance; then broader/repeated official evidence.
A read-only review identified both direct-commit and reconciliation final paths;
no implementation from that review has been made yet. B display/speech adoption
requires coordination, not teammate-file edits. Goal active; push completed checkpoint.

## Evidence-selected read-answer checkpoint — 23 September 2026

Added an opt-in evidence-selection final-answer path for current successful reads.
The controller renders actual fields and rejects stale/failed/write sources,
oversized selections and mixed answer/state/action proposals. The default remains
prose; full remains the default prompt profile. No B implementation/tests changed.

The compact-v2 baseline again invented a hotel billing period despite scorer100.
Final-source evidence mode returned the actual name/price without that qualifier,
with scorer100 and a final at4937ms. Two final-source synthetic model probes also
preserved explicit billing units, physical units, false and zero. These are exposed
single development attempts, not a hidden-set result, repeated reliability score or
proof of source truth/completeness. Free-form clarifications remain unverified.

Final1144passed/2skipped/1xfail in65.71s; Ruff clean. Fifty-two new test cases cover
source admission, bounded rendering, model restrictions, controller enforcement,
legacy compatibility and unfinished-speech rejection. Read-only review found an
answer/state-mutation gap; it was fixed before final validation. Both full-suite
reports and every live iteration are retained with byte hashes and source provenance.

Read docs/READ_ANSWER_EXPERIMENT_2026-09-23.md and its evidence bundle. Both teammates
must coordinate browser/card/voice adoption: A owns validated results, B owns display
and speech. No one should duplicate the other's authority or presentation code.

Next A work: broader profile/read-answer evaluation and relevance/completeness checks,
then remaining official repeatability, packaging/platform and integration gates.
Overall goal remains active. Push this completed checkpoint with configured identity;
no attribution trailers, workflow changes, release tag, submission or real effects.

## Compact-v2 experiment checkpoint — 23 September 2026

Added explicit compact-v2 input presentation: typed protocol-default elision and
model-facing audit-metadata removal, with literal evidence/full-schema enforcement
preserved. Full remains the default, including the submission-package profile.

Live Qwen interruption pair: both scorer89.6, but v2 completed all model calls and
returned a useful selection clarification; full's final call hit provider quota.
Initial input tokens2057 versus3008 (31.6% fewer for the combined profile). One v2
chained-booking attempt scored100.0 with a confirmed mock action at6500ms. These are
single exposed development attempts, not repeated evaluation or a general quota fix.

Final1092passed/2skipped/1xfail in85.48s; Ruff clean. First full run had one B-owned
session-isolation test failure, followed by three isolated passes and the green full
rerun. Both suite XMLs and all live reports are retained with exact-byte hashes.
Atishay's remote includes newer worker fixes not merged here; the follow-up makes
that source distinction explicit. No B implementation/tests changed.

Read docs/COMPACT_INPUT_PROFILE_2026-09-23.md and the linked evidence bundle.
B follow-up: docs/reviews/ATISHAY_SESSION_ISOLATION_FOLLOWUP_2026-09-23.md.
Corpus scoped review was completed in4b2908d with explicit platform/deployment limits.

Next A work: broader/repeated profile evaluation and evidence-grounded read answers.
The unsupported hotel price qualifier remains open. Coordinate newer B work before
shared media/timing validation; Docker/platform and human submission gates remain.
Overall goal active after explicit resume. Completed checkpoints are pushed with
configured identity, no attribution trailers, workflow change, release or submission.

## Resumed A-side corpus review — 23 September 2026

The user explicitly resumed Mridul's implementation work after the design handoff.
The goal is active again; earlier pause instructions below are historical.

Completed the scoped corpus boundary review and repaired the actual read-byte cap,
normalized resolution errors and invalid read-budget configuration. The review does
not claim adversarial-installation or native junction certification. Atishay's newly
pushed frontend remains on his own branch and was not merged or edited in this slice.

Validation: 1086 passed / 2 skipped / 1 xfailed, two dependency warnings, 89.55s;
repository Ruff clean. Focused corpus/authority suite:116 passed/1 skipped. New tests
first reproduced11 failures/5 passes/1 skip against original source. Both final skips
are native Windows symlink permission limits; the existing conflicting-frame xfail
remains open. No live model evidence from this slice.

Review: docs/reviews/CORPUS_BOUNDARY_REVIEW_2026-09-23.md.
Key files: src/accessflow/corpus.py and owned corpus tests, plus review/status docs.
Next: measured prompt/input-token reduction and evidence-grounded answers, then
broader official evaluation. Shared media/timing and platform/submission gates remain.
Continue completed-checkpoint pushes on mridul/engine with configured identity and
no attribution trailers. No teammate implementation, workflow, release or submission changes.

## Frontend design handoff — 23 September 2026

Current task: prepare the approved voice-first frontend design and independent
implementation instructions for Atishay. This documentation task is complete;
Mridul's implementation/evaluation goal remains paused at the previous checkpoint.

Key files: root DESIGN.md; docs/design/README.md, FRONTEND_HANDOFF.md,
ATISHAY_AGENT_PROMPT.md, STITCH_PROMPTS.md; two approved reference PNGs and their
SHA-256 manifest. Shared specification copies are under .ai-sync/artifacts/.
Atishay owns implementation. Both teammates must coordinate any shared event,
provenance, timing or action-outcome seam identified in the handoff.

Validation: seven Markdown files checked, thirteen relative links resolved,
two reference hashes verified, no broken fences/links found. No application tests,
model evaluations, frontend changes or perception/controller changes were made.
The existing browser captures WAV then uploads on stop; the approved continuous
voice experience remains implementation work, not a claimed existing capability.

Next: give Atishay docs/design/ATISHAY_AGENT_PROMPT.md in his own checkout.
User-selected route: Atishay follows STITCH_PROMPTS.md first, saves accepted exports,
then implements his frontend. This supersedes the earlier direct-first recommendation.
No Stitch project was generated or published. No workflow/release/submission change.
Use configured Git identity without assistant attribution or coauthor trailers.

## User-requested pause checkpoint — 22 September 2026

The user requested a pause after this checkpoint is pushed. Implementation and
model evaluation have stopped. The incomplete read-only corpus review worker was
interrupted; no completed findings or test results are claimed from it. No new
compact/token-budget profile was implemented. No matching corpus-review Python/uv
process was found in the final process check.

Latest implemented code:9a3eb84 on mridul/engine. Main holds the earlier combined
merge438b91b. Final software validation remains1070passed/1skip/1xfail and Ruff clean;
this checkpoint only adds documentation, so those checks were not repeated.
The package passed official import/setup and one public text scenario, not the
full repeated official procedure or multimodal certification.

Read docs/WORK_SUMMARY_2026-09-22.md for the consolidated work and remaining tasks.
Corpus review remains open at
`docs/reviews/CORPUS_BOUNDARY_REVIEW_STATUS_2026-09-22.md`.
Atishay's ownership and his existing timing/correlation follow-ups remain unchanged.

After pushing this documentation checkpoint, set the active goal to paused.
Do not continue coding, testing, provider calls or worker tasks until the user
explicitly resumes. No release tag, submission or workflow change. Use configured
Git identity without coauthor trailers or attribution signoffs.

## Package/startup checkpoint — 22 September 2026

Added a local Samsung package assembler, declared Groq model profile, portal-secret
mapping, pinned requirements and exact file manifests. Generated packages remain
ignored local artifacts. A fresh Python3.11.15 environment installed21 pins from
public PyPI; the initial offline attempt failed on missing cache entries.

Official import passed, but the first contract smoke crashed because Samsung sends
speech before a manifest. Fixed A runtime with bounded early-input buffering
(32events/64KiB); no controller input or action precedes the real manifest. Unknown
inputs/tool results remain rejected and cancellation/overflow are explicit.
The rebuilt package passes official import/setup checks and one public no-tool
case100.0, final703ms. This is not the full three-repetition evaluation or media proof.

Final1070passed/1skip/1xfail, two warnings,55.27s; focused36passed; Ruff clean.
Twenty-three new tests across packaging and startup. No B implementation/tests
changed. Evidence and exact reproduction: docs/SAMSUNG_PACKAGE.md and
`docs/evidence/samsung-package-2026-09-22/`. Package label AccessFlow is provisional
until the registered team spelling is confirmed for final submission.

Two prompt-only grounding changes both failed to remove the unsupported hotel
pricing period and were reverted. Both attempts are retained in
`docs/evidence/samsung-grounding-2026-09-22/`; the production model prompts are
unchanged. Grounded claims and provider quota remain A work. Both teammates must
coordinate media/vision/timing; Atishay retains B ownership. Existing B follow-ups,
frame xfail, Docker/Linux verification and final submission gates remain open.

Completed verified changes are pushed to mridul/engine under configured Git identity,
without coauthor trailers or signoffs. No workflow, release tag or submission action.
Overall goal remains active; this checkpoint supersedes historical status below.

## Unfamiliar-tool checkpoint — 22 September 2026

The diagnostic runner accepts explicit external development fixtures while retaining
public filename restrictions and evaluator/participant separation. Four live hosted
attempts scored100.0: weather, two rental variants and hotel. These exposed examples
span three tool names; they are not a hidden-set score or repeated-run median.
Manual review found an unsupported "per night" claim in the hotel answer despite
its full score. Generic answer grounding is the next A-owned quality task.

Seven runner tests pass; Ruff clean. First full suite1failed/1046passed/1skip/1xfail;
final rerun1047passed/1skip/1xfail (60.69s). A different B demo test failed in the
first full run and one of three isolated reruns. It may accept an image-only final
before the follow-up question is answered; the causal interleaving is not proven.
Report: docs/reviews/ATISHAY_WEBSOCKET_CORRELATION_FOLLOWUP_2026-09-22.md.
Atishay owns B synchronization/demo changes; Mridul owns A output provenance and
integration, with explicit coordination if a shared-contract defect is found.
No B source, tests or handoff changed. Prior frame timeout/xfail remain open.

Four unchanged traces, suite XML and hashes are retained in
`docs/evidence/samsung-unseen-2026-09-22/`. The generated fixture seed is20260922;
raw organizer fixtures/answers are excluded. Full prompt remains default.
Completed tested changes are pushed to mridul/engine with configured Git identity.
No coauthor trailers, signoffs, workflow changes, release or submission.
Overall goal remains active; this checkpoint supersedes historical status below.

## Request-final checkpoint — 22 September 2026

Resolved historical writes no longer silence unrelated informational follow-ups.
Informational finals close their request internally while preserving the demo's
`listening` status. Current and unresolved effects still require tool evidence.
A first proposal that establishes write intent cannot substitute a prose success
claim for dispatch; incomplete waiting-for-input and read-only paths remain valid.

Final suite: **1044 passed, 1 skipped, 1 xfailed**, two dependency warnings,
54.82 seconds. Six new regression cases and a revised historical silence test;
focused78 passed. Ruff and diff checks clean. Intermediate regressions in exposed
status, promised-image waiting and a read-only fixture were corrected in A code;
no B tests were changed. Full history: `docs/INFORMATIONAL_FOLLOWUPS_2026-09-22.md`.

Live Samsung no-tool case: **100.0**, zero tool calls, final at735ms and both model
requests successful. This public run preceded the additional first-plan write
claim guard and does not exercise it; source provenance is retained in
`docs/evidence/samsung-informational-2026-09-22/README.md`. Follow-up/guard evidence
is deterministic mock integration, not a live multi-turn claim.

Next A work: unseen-tool public evaluation, compact-profile selection quality and
input quota, then packaging/remaining boundary review. Full prompt stays default.
Media, timing and frame semantics still need Atishay coordination. Known skip,
frame xfail and separately reported intermittent B timing issue remain open.
No B implementation changes, subagents, workflow changes, submission or release tag.
Completed tested commits are pushed to mridul/engine using configured Git identity,
without coauthor trailers or assistant-name signoffs. Overall goal remains active.
This checkpoint supersedes historical status below.

## Compact profile checkpoint — 22 September 2026

Added explicit `compact-v1` prompt presentation with condensed guidance, generated
schema annotation removal and bounded size/hash telemetry. Full schema enforcement
and session/tool evidence are preserved. Default remains `full`.

Validation: **1038 passed, 1 skipped, 1 xfailed**, two dependency warnings,
64.86 seconds. Nine new tests; focused model/validation suite83 passed; Ruff clean.
Live compact interruption score84.3: initial plan validation failed, one retry was
superseded, corrected search succeeded, final request hit input quota. Lower initial
input tokens (2321 versus previous3004) did not establish better reliability. This
is an opt-in experiment, not a default upgrade or a closed quota issue. Evidence:
`docs/evidence/samsung-compact-2026-09-22/README.md`.

Samsung's kit explicitly allows hosted APIs and open/local models, with no published
Theme5 parameter ceiling found. The observed7000 ITPM cap is Groq's quota. Model,
runtime and submission rules are in `docs/SAMSUNG_MODEL_RULES_2026-09-22.md`.
Atishay's intermittent frame issue remains separately documented; no B source edited.

Next: improve compact binding selection and broaden live cases; inspect the inherited
follow-up-answer suppression after writes. Keep the full profile until experiments
justify adopting another. User authorized continuing pushes of completed tested
commits on mridul/engine. Use configured Git identities; no co-author trailers or
assistant-name sign-offs in new commits/documents. Previously completed work through
a21067b has been pushed. No release tag, submission or workflow changes.
Overall goal remains active. This supersedes historical status below.

## Correction-response checkpoint — 22 September 2026

Implemented accepted user-correction speech with current state, Samsung repeated
filler suppression and bounded honest failure clarification. Finished possible
corrections now bypass the partial debounce; partial speech still waits. No change
to B perception/policy semantics, write permission or actual tool-effect reporting.
Details: `docs/CORRECTION_FEEDBACK_2026-09-22.md`.

Final suite: **1029 passed, 1 skipped, 1 xfailed**, two dependency warnings in
53.64 seconds. Eight new tests; Ruff clean. Prior feedback-only full run also
passed (1027 tests). Existing skip/xfail and separate intermittent B timing issue
remain open. No B source, tests or handoff edits; no subagents used.

Live public interruption attempts: **65.3 -> 84.3 -> 89.6**. The latest trace
passes corrected-city acknowledgment, current-state, cancellation, latency and
safety checks; the final useful answer is still missing because the third planning
request exceeds provider input quota. All failures are retained in
`docs/evidence/samsung-interruption-2026-09-22/README.md`. This is exposed incremental
development, not repeated reliability, a completion percentage or certification.

Next A work: reduce repeated model-input overhead without changing enforcement,
then retest correction completion and broaden public text coverage. Also inspect
the documented inherited follow-up-answer suppression after a completed write.
B media/endpoint/frame work needs coordination. Changes remain local; no push,
workflow dispatch, release tag or submission. Overall goal remains active.
This checkpoint supersedes historical current-state descriptions below.

## Read-retry checkpoint — 22 September 2026

Implemented a bounded fast retry for current transient read failures. It preserves
arguments, dependency revisions and operation identity, uses a new physical call
ID with retry lineage, and shares the existing two-attempt budget with model retries.
Current write bindings follow only this controller-issued replacement; stale
contracts and failed payloads cannot gain authority. No automatic write retry.
Base Agent remains opt-in; Samsung's default factory enables it (flag 0 disables).

Final full suite: **1021 passed, 1 skipped, 1 xfailed**, two dependency warnings,
71.79 seconds. New retry tests: 25 passed; Ruff clean; fake dev 4/4. The previous
full run failed one B-owned stale-frame timing test; three isolated reruns and the
final full run passed on unchanged B files. The failure remains documented for
Atishay in `docs/reviews/ATISHAY_TIMING_FOLLOWUP_2026-09-22.md`. The native symlink
skip and existing conflicting-frame xfail are not passing safety evidence.

Live Samsung pub_08: fast retry **100.0**, matched configuration control **81.5**.
Error-to-retry emission: 15 ms versus 922 ms. Fast mode returned a grounded final
at 5734 ms; the control's final model call hit HTTP 429. Same source/configuration
apart from retry flag, but provider quota/timing are not controlled. This pair
supports reduced round trips and token demand, not repeated reliability or a pure
latency ablation. Reports, provenance and hashes are retained in
`docs/evidence/samsung-retry-2026-09-22/README.md`.

Next A work: broader public text interruption/unfamiliar-tool/no-tool cases and
repeat measurements under declared quota conditions. B media/endpoint/frame
semantics need Atishay coordination; no B source, tests or handoff edited. Docker,
remaining security review and submission work stay open. Changes remain local on
mridul/engine; no push, workflow dispatch, release tag or submission. No subagents
used for this slice. Overall user goal stays active.

This checkpoint supersedes the historical current-state descriptions below.

Last updated by: Codex. Current task: A-side Samsung text evaluation.
In progress: broader public cases after completed transient-read retry slice.
Key files modified: contracts, controller, Samsung runtime/runner, retry tests and evidence.

## Current A-side checkpoint — 22 September 2026

**996 passed, 1 skipped, 1 xfailed**, two dependency deprecation warnings, in
82.99 seconds. Ruff passed; offline-fake development scenarios 4/4. Commands:
`uv run --offline --frozen --extra dev pytest -q`,
`uv run --offline --frozen --extra dev ruff check .`,
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.
The skip is native Windows symlink creation without the required privilege;
mocked resolved-escape tests pass. The existing conflicting-frame xfail remains
unresolved. Neither is counted as a passing safety test.

Implemented explicit spoken result bindings, fixed argument mappings and source
revision checks. A scoped review reproduced and closed an image-induced contract
removal bypass and acceptance of success-labelled evidence carrying an error.
Malformed Pydantic/JSON/schema outputs now get one bounded same-input retry with
sanitized shape feedback; non-fresh retries cannot gain spoken write authority.
Optional tool documentation is explicitly loaded below kit/docs, hashed and kept
separate from observations/results/permissions. Verbatim return examples are
selected with line/hash provenance to reduce repeated input tokens.

One live Qwen Samsung chained-booking attempt completed: **100.0/100**, one search,
one booking, confirmed final at 6250 ms, normal tail unchanged. Earlier new attempts
failed validation (38.5) and hit input quota (15.4); all reports are retained in
`docs/evidence/samsung-binding-2026-09-22/README.md`. These are individual exposed
public development runs, not medians, an ablation or release certification.
The successful explicit profile uses a 32768-character hosted cap, output cap950,
1.0-second speculative partial debounce and docs/TOOLS.md. Defaults/local limits
were not silently changed. The provider reported a 7000 input-token/minute quota;
the successful run used 3013+3615 planning input tokens, so headroom remains tight.

Next A-side work: bounded transient-read retry to save a model roundtrip and final
answer time; then additional public interruption/unseen/no-tool cases and repeated
measurements under declared quota conditions. MP3/vision/timing/frame coordination
still requires Atishay; no B-owned implementation or handoff changed. Docker,
unrelated file-boundary security review and submission materials remain outstanding.
Current work stays local on mridul/engine. No push, workflow dispatch, release tag
or submission. User's latest steering: no more Astra subagents; Luna only if needed.
This checkpoint supersedes current-state wording in historical sections below.

Last updated by: Codex. Current task: merged-code validation and Samsung diagnostics.
In progress: delegated-result binding and retry latency.
Key files: diagnostic runner, runner tests, evidence reports and A-side documentation.

## Current validation checkpoint â€” 22 September 2026

Fresh rerun: **863 passed, 1 xfailed**, two dependency deprecation warnings
(63.64 seconds); Ruff passed; offline-fake development suite **4/4**.
Commands: `uv run --offline --frozen --extra dev pytest -q`,
`uv run --offline --frozen --extra dev ruff check .`, and
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.
The merged-main baseline previously measured 842 passed / 1 xfailed; the current
local Mridul branch additionally includes adapter, recovery and runner tests.
The conflicting-frame expected failure remains unresolved, not a passing safety test.

Three recorded live Qwen public text attempts: simple search **100.0**, chained
booking **56.9**, failed-read recovery **81.5**. These are individual development
scores, not task completion percentages or final benchmark results. Booking was
blocked by tool-derived argument authority; recovery succeeded but final inference
missed the normal tail window. Full evidence and provenance:
`docs/evidence/samsung-text-2026-09-22/README.md`.

Next A-side work: implement and test the proposed delegated-result binding in
`docs/DELEGATED_RESULT_BINDING.md`, then optimize bounded read recovery timing.
That spec is not implemented or certified. Coordinate MP3/vision/timing with
Atishay; no B-owned implementation changed. No new dependencies. Current work
remains local on `mridul/engine`; no release, submission or workflow dispatch.
This checkpoint supersedes current-state claims in historical sections below.

## Read-failure recovery checkpoint â€” 22 September 2026

Latest Workstream A validation: **859 passed, 1 xfailed**, with two dependency
deprecation warnings; Ruff passed; offline-fake development scenarios **4/4**.
Commands: `uv run --offline --frozen --extra dev pytest -q` (68.11 seconds),
`uv run --offline --frozen --extra dev ruff check .`, and
`uv run --offline --frozen --extra dev python -m accessflow.cli suite scenarios/dev`.

Fixed a reproduced silence after failed read-only tools: the reasoner now gets
sanitized `tool_failures` separately from usable results, and can use the existing
one-retry allowance or explain the failure. Four new tests cover recovery,
repeated failure, the retry cap, and refusal to create write permission.
The first implementation broke three corpus invariants; separation of failures
restored all three original tests without weakening their assertions.

No Atishay-owned files changed. No live model, public Samsung score or full
security audit was run. The existing conflicting-frame xfail remains unresolved.
Next: legitimate tool-derived argument grounding and real Samsung configuration;
media/endpoint work remains coordinated with Atishay. Current work is local on
`mridul/engine`; main remains the earlier verified merge.


Last updated by: Codex. Current task: Samsung integration, Workstream A.
In progress: partial queue adapter; remaining work is listed below.
Key files modified: samsung.py, samsung_protocol.py, adapter tests and documentation.

## Samsung boundary checkpoint â€” 22 September 2026

This checkpoint supersedes older statements that the official adapter is entirely
unimplemented. Development is on `mridul/engine`, based on merged main `438b91b`.
The new queue adapter is partial; it is not full official-kit compatibility.

- Full suite: **855 passed, 1 xfailed**, two dependency deprecation warnings.
  `uv run --offline --frozen --extra dev pytest -q` (95.19 seconds).
- New adapter tests: **13 passed**. Ruff and diff checks passed.
- Supplied Samsung validator accepted all five output kinds using synthetic data.
  No public scenario scores or live inference were run in this slice.
- Added in-process runtime, translated manifests/text/corrections/results/actions,
  tail-window handling, uncertain-write status, and media-failure invalidation.
- Default entry point is text-only. MP3 assembly and real vision configuration
  are not complete. Failed media is explicit and invalidates pending writes.
- No Atishay-owned files changed. No workflow enabled, release tagged or submission made.

Next: reconcile legitimate tool-derived arguments with authority guards; verify
read-error recovery and frame-as-context behavior, then run recorded official
scenarios after real configuration. Coordinate media/C1â€“C4 seams with Atishay.
See `docs/SAMSUNG_ADAPTER.md` for configuration, limits and ownership.


Last updated by: Codex. Current task: branch integration completed.
In progress: none in this session; official adapter remains next.
Key files modified: integration note and status/handoff/AI-use records.

## Current integration checkpoint â€” 22 September 2026

This dated checkpoint supersedes older current-state, branch and kit-availability
claims below; those sections are historical records, not fresh verification.
Mridul merged first (`5c84976`), then Atishay (`a0c36c5`), without conflicts.
The other AI's pending engine/test changes were preserved in `93afd57`.

- Combined suite: **842 passed, 1 xfailed**, with two dependency deprecation warnings.
  Command: `uv run --offline --frozen --extra dev pytest -q`.
- Ruff: passed (`uv run --offline --frozen --extra dev ruff check .`).
- Offline-fake development suite: **4/4 passed** (`python -m accessflow.cli suite scenarios/dev`).
- The retained conflicting-frame xfail is not proof of safe conflict handling.
- Both branch tips are ancestors of main. No implementation added by this merge session.
- Samsung kit is now available outside the repository. Its README says Theme 5;
  the enclosing ZIP name says Theme02. Official adapter is still unimplemented.
- No live inference, official evaluation, Docker test or fresh security audit was run.
  Prior issue-closure statements are not independently certified by these tests.
- Workflow remains manual-only; no workflow enabled or dispatched.

Next: implement Mridul's official queue adapter, coordinating MP3/timing/frame
interfaces with Atishay. Details and ownership: docs/INTEGRATION_2026-09-22.md.

## Imported Atishay checkpoint — 2026-09-23

Last updated by Codex on branch atishay/perception at HEAD 967e39d. The AccessFlow frontend redesign is implemented in the owned demo paths and documented in demo/FRONTEND_REDESIGN_SPEC.md and artifacts/FRONTEND_REDESIGN.md.

Verification: full repository suite 810 passed, 1 existing xfailed, 2 dependency warnings; repository Ruff passed; inline browser JavaScript parsed; git diff --check passed. No deployment or push occurred.

Visual browser QA is complete at 1440×1024, 834×1194, and 390×844 using an isolated local Edge profile. Empty and mock text-response states were inspected at all three sizes; a generated PNG upload, focusable full-image preview, and document-width behavior were checked. A long response headline overflow and a cramped mobile header were found and fixed. Remaining limits: microphone permission, live ASR/vision quality, and non-mock reasoning were not certified. See `demo/FRONTEND_REDESIGN_SPEC.md` and `demo/FRONTEND_REDESIGN_PREVIEW.png` for the canonical record and desktop capture.

Mixed-media inputs are sent as sequential existing events. The page hides earlier finals while a Run action is in flight and displays the result correlated to the final submitted source via a final-only demo observation notice. This is presentation coalescing, not a transaction or shared-contract change.

The current task did not modify docs/STATUS.md because AGENTS.md assigns that file to Mridul; its last measured project snapshot is older than this frontend work.

## Historical handoff snapshot — 2026-09-16 (superseded)

> Last updated by: Claude Code
> Timestamp: 2026-09-18
> Branch: `mridul/engine`, three commits ahead of `main`. Current status, measured by the
> orchestrator on 18 September 2026 at commit `ef58557`: full suite 818 passed, 1 xfailed,
> 0 failed. Ruff clean. Offline dev suite 4 passed, 0 failed, oracle pass rate 1.0. The
> 19 `tests/demo/` failures recorded on 16 September are closed; Workstream B repaired
> them. Earlier figures of 384, 411, 543, 635, 769 and 799 are historical. Do not quote
> any number in this header as current except the ones on these lines. See
> `docs/STATUS.md` "Current status" for the full sourced fact list.
> Pushed to `origin/mridul/engine` at `2f91d6a` on 16 September 2026 without a security
> review. Mridul waived the review for that push. That range added a file access boundary
> in `src/accessflow/corpus.py`: an allowlist, a document name check and a resolved-path
> containment check. Corpus work has continued since that push, through commit `71b1bb5`
> (dispatch, I/O bounding and discovery fixes). None of `corpus.py`, at either commit, has
> had a security review. Whether the range through `71b1bb5` has been pushed is not recorded
> here. Run the security review before any push and before the submission tag.

> Before starting: read `docs/STATUS.md` "Still required" and update it before you finish.

## Review findings status

The Codex review (`docs/reviews/CLAUDE_REVIEW_2026-09-15.md`, audited baseline `92ead42`)
recorded its twelve findings, R1 to R12, as closed on 15 September. The later
`docs/reviews/MRIDUL_REAUDIT_2026-09-15.md` re-examined the codebase against that claim and
found several R-items still partial or open, re-numbered A1 through A9.
`docs/reviews/REAUDIT_RESOLUTION_2026-09-16.md` recorded evidence against that list. A second
audit, `docs/reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md`, then re-examined the repaired tree
and reassessed several A-numbers, adding its own findings M1 through M7. **The second audit
is the correct, current statement for anything it reassessed. Do not cite the resolution
record's verdict where the second audit narrowed or reopened it, and do not repeat "all
twelve findings closed."**

| ID | Finding | Current position |
|---|---|---|
| A1 | Clarify-then-image deadlock (was part of R2/R3/R11) | **Addressed**, confirmed by the second audit. See "Open work" below for what `SessionView` actually carries. |
| A2 | Vision options rejected by the perception worker (was R11) | **Open, blocked on Workstream B.** See "Cautions". |
| A3 | Audio task-effect oracle (was part of R11) | **Partial.** The relabeled smoke check is fine; the new clarification fixture had its own defect, tracked as M1 and fixed at commit `7b0d373`. |
| A4 | Evidence eligibility (was part of R4/R8) | **Partial, then fixed.** The 57-run cohort matched policy, but a success-then-429 sequence was misclassified: M6, fixed at commit `86655f0`. See `docs/STATUS.md` for the corrected 43-of-49 figure. |
| A5 | Portable evidence ordering (was part of R8) | **Addressed.** |
| A6 | Profile verification (was R7) | **Addressed.** |
| A7 | Contradictory current documents (was R12) | **Reopened by the second audit as M7**, because this file and `docs/STATUS.md` still disagreed after the first repair. **M7 is fixed by this update.** |
| A8a-c | Test command, malformed JSONL, relative inventory path | **Addressed.** |
| A9 | Corpus integration, scenario independence, baseline timing, release gates | **Partial.** `src/accessflow/corpus.py` has a real consumer now (M2, M3, M5 fixed at commit `71b1bb5`); action-trust and read-then-write boundaries were also fixed (M4, commit `6caa889`). It has never had a security review. Scenario independence, baseline timing and release gates remain open; see "Open work" below. |

Full evidence for the A-numbered findings is in `docs/reviews/MRIDUL_REAUDIT_2026-09-15.md`
and its reassessment in `docs/reviews/MRIDUL_SECOND_REAUDIT_2026-09-16.md`. Full evidence for
the M-numbered findings, including the unresolved `corpus.py` security-boundary items no
commit above closes, is in the second audit. This table is a pointer, not a substitute for
reading either document.

## Open work

1. **Vision is blocked on Workstream B (finding A2).** The vision adapter, CLI options,
   fixture and scenario are committed. The perception worker needs one additive parameter to
   pass a provider to `LocalPerception`. `AGENTS.md` places `src/accessflow/adapters/` in
   Workstream A, but Mridul deliberately assigned this one file,
   `src/accessflow/adapters/perception_worker.py`, to Atishay on 15 September, overriding the
   directory rule for that file only. The request is in `docs/CONTRACT_PROPOSALS.md`. The
   path was measured once with a temporary local edit that is now reverted; the result
   document, `docs/results/VISION_E2E_2026-09-15.md`, is marked blocked and not reproducible
   from this checkout.
2. **Corpus is 17 files, 10 distinct tool sets, 2 audio, 1 visual.** See
   `docs/SCENARIO_INVENTORY.md`, which is generated from the files and lists which files
   repeat the same underlying workflow. `src/accessflow/corpus.py` now has a real consumer
   (`src/accessflow/engine.py` wires manifest dispatch, allowlist enforcement and bounded
   `CorpusStore` reads), fixed at commit `71b1bb5` (findings M2, M3, M5). Retrieval stays
   lexical only, with no semantic ranking, citation, size limit or installed document
   directory; see `docs/reviews/REAUDIT_RESOLUTION_2026-09-16.md`, "Scope limit of the corpus
   implementation". **`corpus.py` has never had a security review; that code is on the
   remote unreviewed.**
3. Docker execution on a Docker-capable host. Official kit adapter. Submission assembly.
   Docker is not installed on this machine, so this cannot be checked here at all.
4. Run a security review over `src/accessflow/corpus.py`. It has never been reviewed.

**Resolved, removed from this list:** the clarify-then-image deadlock (previously item 2
here). A spoken write request, a clarifying question, then the answering image now completes.
The stall was gated on `speech_write_requested` and `latest_complete`; that field no longer
exists. The controller session object now carries `write_intent_retained` and
`clarification_outstanding` as its own attributes (`src/accessflow/engine.py`) â€” these are
**not** `SessionView` fields. `SessionView` (`src/accessflow/contracts.py`) exposes only
`write_pending`, which the controller sets from `write_intent_retained` inside `_view()`;
`clarification_outstanding` does not reach the view at all. The former strict-xfail
reproduction is a passing acceptance test in `tests/engine/test_component_integration.py`
(`tests/engine/test_known_defects.py` is now empty by design; see its module docstring). This
is finding A1 in the re-audit.

**Also resolved, removed from this list:** the four held-out planner probes (previously item
3 here). They ran once, on 16 September 2026, and passed 4 of 4 on `groq/qwen/qwen3.8-27b`;
see `docs/STATUS.md` "Current status". They are now spent: development data, not unseen
evidence. Do not run them again expecting a fresh, unseen measurement.

## Cautions

- **Perception worker ownership is resolved, not a blanket Workstream B rule.** `AGENTS.md`
  places `src/accessflow/adapters/` in Workstream A. `src/accessflow/adapters/perception_worker.py`
  is the one deliberate exception: Mridul assigned its vision-provider wiring to Atishay on
  15 September, overriding the directory rule for that file only. See the ownership note in
  `docs/CONTRACT_PROPOSALS.md`. Everything else under `src/accessflow/perception/`,
  `src/accessflow/turn_policy/`, `demo/`, `tests/perception/` and `tests/demo/` remains
  Atishay's untouched territory; raise a proposal in `docs/CONTRACT_PROPOSALS.md` before
  editing any of it, including the worker file.
- Subagents have twice left `find /` scans running for half an hour. Sweep for stray
  `find.exe` and `bash.exe` after every agent finishes.
- Regenerate `MODEL_COMPARISON.md` and `SCENARIO_INVENTORY.md` with their scripts. Do not
  hand-edit below the generated marker, and do not rewrite line endings by hand.
- Answer model questions from `docs/results/MODEL_COMPARISON.md`, never from memory.

## Current Task

Workstream A. Model selection and local inference speed are finished and documented.
The ablation is done and returned a negative result. Multimodal evidence is the next work.

## Completed this session (dated 14-15 September 2026, historical)

- **Backends.** Groq and NVIDIA NIM added behind a shared OpenAI-compatible branch keyed by
  env prefix. Ollama and Gemini unchanged. Selection stays explicit with no automatic fallback.
- **Model question answered.** `qwen/qwen3.8-27b` is the primary: 6/6 across every
  `live_dev` fixture on 15 September at 0.83 s to 0.99 s per request, with no HTTP error.
  It requires `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`; without it Groq refuses every request at
  admission because the adapter sends no `max_tokens`. `openai/gpt-oss-120b` is the fallback
  and needs no cap. Read `docs/results/MODEL_COMPARISON.md` for any model question and
  regenerate it with `scripts/model_scoreboard.py`. Never quote model scores from memory.
- **Write-continuation constraint.** While a requested write is outstanding the planner sends
  a `complete_requested_write` step and types `response` as null, so prose is not a valid
  answer. `qwen3:4b` went from never passing `support-read-then-service` to 4/4 overall.
  Additive `SessionView.write_pending`, defaulted false, so every existing reasoner and fake
  stays valid. See `docs/results/CONTINUATION_2026-09-14.md`.
- **Local inference tuned.** Generation 7.9 to 38.1 tok/s, mean request 25.2 s to 8.6 s,
  scenario runtimes 16-59 s to 4-17 s against a 120 s cap. Start the server with
  `-FlashAttention 1 -KvCacheType q8_0`. See `docs/results/INFERENCE_TUNING_2026-09-14.md`.
- **Diagnostics.** Failed requests now record the HTTP status code and bounded provider error
  text. `--request-timeout` and `--inference-timeout` replace a hard-coded 25 s deadline.
- **Ablation complete, negative result.** `--disable dependency_invalidation` makes
  `_invalidate_dependencies` a no-op and emits `ablation_skipped_invalidation`. Twelve Groq
  runs across two new live fixtures: control 3/3 and ablated 3/3 on both, with identical
  committed effects. The mechanism is correct and observable, but it changes no task outcome
  for a strong model. Do not claim that wrong effects appear without it. See
  `docs/results/ABLATION_2026-09-15.md`.
- **Two live fixtures added.** `stale_read_after_correction` and
  `stale_read_after_device_correction` place a correction after a read returns, with no write
  in flight, so `_cancel_writes` cannot hide the mechanism under test.
- **`Scenario.event_gaps_s` added.** One uniform `event_spacing_s` caps at 5 seconds and
  cannot place a correction after a tool result when a local plan takes 12 to 14 seconds.
- Registration is complete.

## In Progress

- **Held-out probes are done, not in progress.** They ran once, on 16 September 2026, and
  passed 4 of 4; see "Open work" above and `docs/STATUS.md` "Current status". They were the
  only unseen data available and are now spent development data. Do not run them again and
  call the result unseen.
- **Scenario corpus is 17 files, 10 distinct tool sets** (2 audio, 1 visual, 15 transcript).
  See `docs/SCENARIO_INVENTORY.md` for the full breakdown. The plan calls for 30 text, 18
  audio, 12 visual, split 40 development and 20 held out; the corpus is well short of that on
  every axis.

## Next Steps

1. **Multimodal end to end.** Audio and visual are 50 percent of the hidden set at a 1.5
   multiplier and have thin evidence: 2 audio files over one recording, 1 visual file that
   cannot run through the process adapter (finding A2). Largest unclaimed score.
2. **Fix the local write-intent defect.** `qwen3:4b` never sets `write_requested`, so the
   write-continuation constraint never starts locally. See "Known Defects" below. This is a
   local-model planning gap, separate from the clarify-then-image deadlock (A1), which is
   fixed. It blocks every local multi-step result.
3. ~~Run the four held-out probes once, after the engine stops changing.~~ Done: they ran
   once on 16 September 2026 and passed 4 of 4. They are spent; do not run them again.
4. Verify Docker container execution on a Docker-capable host. Not possible on this machine:
   Docker is not installed here.
5. Official kit adapter once the organizer publishes the schema. Do not invent wire compatibility.
6. Submission assembly: deck, video of five minutes or less, AI disclosure, release tag
   `PRISM_GENAI_HACKATHON_Y2026`. Do not create the tag during ordinary development.
7. Run a security review over `src/accessflow/corpus.py`. It has never been reviewed, and
   corpus work landed again at commit `71b1bb5` after the unreviewed push at `2f91d6a`.

## Known Defects and Cautions

- **Local-model write-intent gap (open, distinct from the fixed A1 clarify-then-image
  deadlock).** The write-continuation constraint gates on the model's own `write_requested`
  flag. `qwen3:4b` proposes the read again on every turn and never sets the flag, so the
  safeguard never starts. The controller ignores the duplicate call and emits nothing, so the
  turn stalls silently until the scenario deadline. A stall with no diagnostic is the second
  half of this defect. This has not been re-verified against the current engine fields
  (`write_intent_retained`, `clarification_outstanding`) in this update; treat its current
  status as unverified rather than assume it still reproduces unchanged.
- **Pin `ACCESSFLOW_OLLAMA_NUM_GPU=37` for `qwen3:4b` on the GTX 1650.** Automatic fitting is
  not dependable. Ollama holds a 1024 MiB free-memory reserve and drops to 29/37 layers when
  full offload does not clear it. The 14 September auto-fit result cleared the reserve by
  17 MiB. Do not put the pin in `.env`; it is correct for exactly one model. See the
  15 September correction in `docs/results/INFERENCE_TUNING_2026-09-14.md`.
- **Three earlier results were infrastructure defects, not model failures.** A stale `num_gpu`
  pin, a hard-coded 25 s deadline, and an unsuppressed reasoning think block each produced
  scores that read as planning failures. Any older trace showing `backend_failure` is
  unmeasured rather than wrong. Record the offload line and think setting beside every local score.
- **Free-tier limits are per model and differ by dimension.** Groq throttles `qwen3.8-27b` on
  input tokens at 7000 per minute and `qwen3.6-27b` on output tokens at 1000 per minute. Pace
  one scenario per 55 to 95 seconds.
- **Network access is not guaranteed.** The Theme 5 guide never states that the evaluation
  environment has outbound network. Keep the local backend working; a hosted-only submission
  scores zero if the harness is sandboxed.
- **Secrets.** `.env` holds Groq and NVIDIA keys and is gitignored; no key is in any tracked
  file. The NVIDIA key was pasted into a chat transcript and should be rotated.
- **CI stays disabled.** Do not enable or dispatch the workflow.
- **No B-owned files were changed.** Atishay `871c8cf` is merged unmodified; his WebRTC VAD
  keeps `webrtcvad` as a lazy optional import, so no lockfile change was needed.
- **Append-only logs now use a union merge driver.** `.ai-sync/context.md` and
  `docs/AI_USE_LOG.md` concatenate both sides automatically. Never add a rewritten-in-place
  file such as `docs/STATUS.md` to that list.
- `main` and `mridul/engine` both sit at `ad04bca` and are pushed. Security review was run
  over the whole range before pushing and returned clean. Branch `mridul/engine` has since
  advanced locally past `fd53aca`; the push/security-review state above is not re-verified as
  part of this update and should be re-checked before the next push.

## Key Files Modified

- `src/accessflow/adapters/models.py` â€” backends, error detail, think flag, continuation rule
- `src/accessflow/contracts.py` â€” additive `SessionView.write_pending`
- `src/accessflow/engine.py` â€” sets `write_pending` on the view; also owns
  `write_intent_retained` and `clarification_outstanding` (finding A1 fix)
- `src/accessflow/cli.py` â€” deadline flags, `groq` and `nvidia` choices, `vision_provider_requested`
- `src/accessflow/evaluation/replay.py` â€” deadline plumbing
- `scripts/start-local-ollama.ps1` â€” `-FlashAttention`, `-KvCacheType`, `-ContextLength`
- `tests/engine/test_models.py` â€” backend, think, continuation and diagnostics coverage
- `tests/engine/test_component_integration.py` â€” the clarify-then-image acceptance test
  (finding A1); `tests/engine/test_known_defects.py` is now empty by design
- `.env.example` â€” Groq, NVIDIA, think and layer-placement guidance
- `src/accessflow/evaluation/scenarios.py` â€” `event_gaps_s` per-pair pacing
- `scenarios/live_dev/stale_read_after_correction.json`, `stale_read_after_device_correction.json`
- `docs/results/` â€” HOSTED_MODEL, LOCAL_REPEAT, MODEL_SWEEP, CONTINUATION, INFERENCE_TUNING, ABLATION
- `docs/handoffs/mridul.md`, `.ai-sync/context.md`

## Historical: Workstream B handoff log

Merged from `atishay/perception` on 16 September 2026. These entries are dated history.
The header at the top of this file is the current state.

## 2026-09-14 - Codex Atishay multimodal end-to-end evidence

- **Task:** Complete the next Workstream B priority for multimodal coverage.
- **Changes:** Added the served demo/recorder-worklet.js path, focused route coverage and one
  Agent-level test for a validated WAV plus PNG sharing a context through injected local ASR/vision.
- **Status:** Full suite 81 passed; demo 22 passed; perception 43 passed; fresh Chrome CDP smoke
  passed synthetic microphone, text, WAV, PNG plus paired transcript, clean console and layout checks.
- **Limits:** Physical microphone, pixel inspection, live ASR/vision quality and non-mock reasoning
  remain unverified. No engine or contract files were changed.

## 2026-09-14 - Codex Atishay image-only controller gap

- **Task:** Make the remaining image-only multimodal gap explicit.
- **Changes:** Added a strict expected-failure demo example and an additive proposal for an
  informational evidence basis; no engine or contract files changed.
- **Status:** Full suite 81 passed, 1 strict xfailed; demo 22 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The expected failure remains until the engine owner implements and reviews the
  additive proposal. Live ASR/vision, physical capture and pixel inspection remain unverified.

## 2026-09-14 - Codex Atishay live local audio plus injected vision

- **Task:** Strengthen multimodal end-to-end evidence with the cached local ASR model.
- **Changes:** Ran synthetic_speech.wav through Faster Whisper base.en CPU INT8, paired the result
  with a validated PNG and injected vision provider in one Agent context, and recorded the run in
  docs/feedback/MULTIMODAL_E2E.md.
- **Status:** Both observations reached one context and produced an informational final in 3.222
  seconds. Vision was injected because Ollama is unavailable.
- **Limits:** This does not certify live multimodal model quality or non-mock reasoning.

## 2026-09-14 - Codex Atishay multimodal ordering coverage

- **Task:** Broaden multimodal end-to-end coverage across arrival orderings.
- **Changes:** The Agent-context test now covers audio-to-image and image-to-audio sequences.
- **Status:** Full suite 82 passed, 1 strict xfailed; demo 23 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only controller gap remains the intentional strict xfail pending the additive
  engine proposal.

## 2026-09-14 - Codex Atishay multimodal revision and frame retention

- **Task:** Cover revised speech hypotheses while retaining image evidence.
- **Changes:** Added one demo Agent test for audio revision 0 followed by revision 1 and a frame.
- **Status:** Full suite 83 passed, 1 strict xfailed; demo 24 passed, 1 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only controller gap remains the intentional strict xfail.

## 2026-09-14 - Codex Atishay browser local-ASR multimodal run

- **Task:** Connect local ASR evidence to the real browser transport.
- **Changes:** Chrome uploaded synthetic_speech.wav with the cached Faster Whisper backend, then
  uploaded a PNG and follow-up text in the same WebSocket session.
- **Status:** Local audio acknowledgment and transcript-bearing final passed; both media statuses,
  clean console and no overflow were observed.
- **Limits:** Image/text remained demo/mock; live vision quality, physical capture and non-mock
  reasoning remain unverified.

## 2026-09-14 - Codex Atishay changed-frame integration gap

- **Task:** Expose active-frame replacement for multimodal scenarios.
- **Changes:** Added a strict expected-failure demo example for frame 2 replacing frame 1 in the
  reasoner context; no engine-owned files changed.
- **Status:** Full suite 83 passed, 2 strict xfailed; demo 24 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only response and changed-frame behavior await engine integration.

## 2026-09-14 - Codex Atishay visible multimodal reasoner context

- **Task:** Make the browser demo response expose all retained modalities.
- **Changes:** DemoReasoner now includes prior observations; Chrome confirmed audio, image and text
  context in the visible final.
- **Status:** Full suite 84 passed, 2 strict xfailed; demo 25 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The response remains mock and informational; live vision and non-mock reasoning remain
  unverified.

## 2026-09-14 - Codex Atishay combined WebSocket context regression

- **Task:** Protect the browser-observed multimodal final with an automated route test.
- **Changes:** Added WAV, PNG and follow-up transcript coverage through one TestClient WebSocket,
  including source IDs and retained modality assertions.
- **Status:** Full suite 85 passed, 2 strict xfailed; demo 26 passed, 2 strict xfailed; perception
  43 passed; Ruff and git diff --check clean.
- **Limits:** The image-only response and changed-frame behavior remain intentional xfails pending
  engine integration.

## 2026-09-14 - Codex Atishay in-flight frame stale-result coverage

**Task:** Cover a changed-device-frame race while the first vision result is still in flight.

**Changes:** Added an owned async Agent regression with a delayed frame 1 perception result. Frame 2
arrives and reaches the reasoner first; after frame 1 is released, its stale result is rejected and
never appears in a frame-bearing reasoner view.

**Status:** Focused regression passed. Expected suite counts after this change are 94 passed, 3 strict
xfailed; demo suite 35 passed, 3 strict xfailed; perception suite 43 passed.

**Notes:** This covers stale-result handling with a perception seam and makes no live vision quality
claim. No engine, contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay structural PNG validation

**Task:** Ensure malformed image payloads cannot reach the multimodal vision backend.

**Changes:** Hardened the owned PNG validator to check chunk boundaries, CRCs, legal IHDR metadata,
IDAT presence and terminal IEND structure. The demo now uses the same validator and removes rejected
materializations. Migrated image tests to real small PNG fixtures and added valid metadata, truncated,
bad-CRC and WebSocket recovery coverage.

**Status:** Full suite 98 passed, 3 strict xfailed; demo suite 36 passed, 3 strict xfailed; perception
suite 46 passed; Ruff and git diff --check clean.

**Notes:** Validation is structural and does not decode pixels or claim image understanding. No engine,
contract, lockfile or dependency manifest changes were made.

## 2026-09-14 - Codex Atishay configured vision WebSocket wiring

**Task:** Exercise the configured Ollama vision path through the actual demo WebSocket route.

**Changes:** Added an owned route regression that sets the vision environment configuration, runs a
loopback HTTP protocol service, uploads a real PNG, waits for the image observation, and submits a
follow-up transcript. The final contains both the service result and the spoken question.

**Status:** Full suite 99 passed, 3 strict xfailed; demo suite 37 passed, 3 strict xfailed; perception
suite 46 passed; Ruff, compilation and git diff --check clean.

**Notes:** The loopback service is a deterministic protocol stub and does not provide live vision quality
evidence. No engine, contract, lockfile or dependency manifest changes were made.


2026-09-14: Multimodal boundary follow-up committed locally on atishay/perception: failed WAV materializations are cleaned up and injected ASR receives an accurate backend label. Validation: 101 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Combined configured multimodal route regression added on atishay/perception. Validation: 102 passed, 3 strict xfailed; no protected files changed.

2026-09-14: ASR failure multimodal recovery regression added on atishay/perception. Validation: 103 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Fresh mixed runtime route evidence captured: cached Faster Whisper CPU INT8 plus loopback OllamaVisionProvider, 1.326 seconds, combined context retained. No protected files changed.

2026-09-14: PNG IDAT integrity regression added on atishay/perception. Validation: 104 passed, 3 strict xfailed; no protected files changed.
2026-09-14: Speech cue modality guard committed locally on atishay/perception. Image observations return continue with uncertainty 1.0 before speech cue matching. Full suite: 105 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Demo input parser now rejects non-object messages and payloads with ValueError handled as demo/input errors; WebSocket recovery regression passes. Full suite: 107 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Backend label fallback now reports local/unknown-audio for unidentified injected audio instead of Faster Whisper; focused and full validation passed. Full suite: 108 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Vision provider now rejects non-object JSON roots with RuntimeError invalid JSON shape; focused and full validation passed. Full suite: 110 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Configured Ollama route regression now covers malformed list JSON and same-session transcript recovery. Full suite: 111 passed, 3 strict xfailed; no protected files changed.

2026-09-14: Ollama vision timeout regression added on atishay/perception; timeout now has explicit stable failure evidence. Full suite: 112 passed, 3 strict xfailed; no protected files changed.

2026-09-14: WebSocket session reset regression added: new connection does not inherit multimodal observations from the prior connection. Full suite: 113 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Added pre-decode encoded upload limit derived from the 8 MiB raw-media budget; oversized PNG regression passes. Full suite: 114 passed, 3 strict xfailed; no protected files changed.

2026-09-15: Configured OllamaVisionProvider timeout regression now covers WebSocket backend_failure and same-session transcript recovery. Full suite: 115 passed, 3 strict xfailed; no protected files changed.

2026-09-24: Demo-only answer correlation now carries Observation.event_id to the
browser and accepts final/clarify only for the latest request's matching
caused_by_event_id. Early finals are buffered through serialized media sends;
late/unattributed finals are ignored. Owned browser/WebSocket regressions pass.
Focused demo: 128 passed, 1 existing xfailed; full suite: 813 passed,
1 existing xfailed, 2 warnings. Real local demo/mock text request rendered and
390px mobile had no horizontal overflow. Native Stitch export and same-state
reference QA remain blocked; no engine/contracts/config change. Atishay and
Mridul need to coordinate authoritative action identity/outcome and speech timing.

2026-09-24: Atishay merged updated main (`749fe23`) into `atishay/perception`
at `f84bea7`, preserving prior owned edits and identical untracked review notes
in a named backup stash. Current owned voice slice narrows task-stop to final
task-cancel phrases; partial cancel and output-only stop no longer cancel the
task, while device stop remains a complete request. The output-only typed action
still needs joint C24-2 agreement. The configured demo reasoner test now checks
the spoken question's causal final and distinct combined evidence. Before-fix
policy reproduction: four failures; owned tests: 371 passed/1 xfailed; full:
1203 passed/2 skipped/1 xfailed. Actual generated WAV through installed local
ASR produced text but flattened segment timing/finality in the public observation.
Physical mic permission remained prompt, so no real capture was verified; live
vision, Qwen/mock effect and official media evaluation remain open. Kit files
were not found at the documented location. C24-1 through C24-5 examples, splits
and exact limits are in `docs/feedback/VOICE_PERCEPTION_CHECKPOINT_2026-09-24.md`.
No Mridul-owned source/config, release, direct-main push or deployment action.

2026-09-24: Atishay-owned browser microphone permission-wait repair. A new
deterministic regression first observed two simultaneous getUserMedia requests;
the demo now shows waiting/not-recording, blocks duplicates, restores controls
after denial and stops late-granted tracks after task/disconnect/restart/exit
invalidation. Live page confirmed the waiting state, not physical capture.
Owned demo/perception 372 passed, 1 xfailed; Ruff and diff check clean. Details
in docs/feedback/VOICE_PERCEPTION_CHECKPOINT_2026-09-24.md. No shared engine,
contracts, Samsung adapter or submission change.

2026-09-24: Browser capture teardown now discards active microphone resources
on WebSocket close, session restart and unload without uploading abandoned
audio. Owned Node regression covers track/context/port cleanup and idempotency.
No physical disconnect or human ASR evidence is claimed.

The owned disconnect harness also reproduced late WAV staging after the socket
closed during AudioContext shutdown; a stop-path guard now drops that capture.

Final B capture-slice checks: owned373pass/1xfail; full1205pass/2skip/1xfail,
2 dependency warnings; Ruff and browser-script parse clean. Actual mic
permission and human speech remain unverified.

Read-only A update: origin/mridul/engine@81699c9 contains MP3 turn admission
and the configured factory, still unmerged into this B checkout. Its reported
23.688s real public-frame observation missed the visual tail. B documented an
optional, unimplemented vision generation-cap experiment and joint file split
in the voice/perception feedback checkpoint. Local vision service unavailable;
no B real-pixel result, A file edit or implicit contract acceptance.
