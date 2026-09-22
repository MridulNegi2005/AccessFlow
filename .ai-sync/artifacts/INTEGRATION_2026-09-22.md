# Branch integration and Samsung kit intake — 22 September 2026

## Merge record

User requested Mridul first, then Atishay. Both merges applied without conflicts.

1. Preserved the pre-existing uncommitted changes to `engine.py` and
   `test_argument_authority.py` in `93afd57`. These were the other AI's changes;
   Codex inspected and checkpointed them, rather than authoring them in this session.
2. Merged `mridul/engine` into `main`: `5c84976`.
3. Merged fetched `origin/atishay/perception` (`3f8f895`) into `main`: `a0c36c5`.

No branches were rebased or force-pushed. No new implementation was added during
integration. Existing source changes and both workstreams' documentation were retained.

Before merging, Mridul's full suite passed: **833 passed, 1 xfailed**; Ruff passed.
Post-merge verification: **842 passed, 1 xfailed**, Ruff passed, and the
offline-fake development suite passed **4/4**. Two dependency deprecation
warnings were emitted. Exact commands are in the current handoff/status header.
These are software checks, not official-kit scores or a security certification.

## What kit we received

Local kit root: `../participant-kit/participant-kit/`, relative to this repository.
The enclosing ZIP is named `Theme02_Input_Kit.zip`, but the extracted README's
first heading is **Theme 5: Interruptible Agents**. Its protocol and Python
validator describe the Theme 5 queue-based interruptible agent. The ZIP name
alone does not establish that the inner material is for Theme 2. We have not
verified organizer intent behind this naming inconsistency.

Sources inspected: kit `README.md`, `docs/PROTOCOL.md`, `docs/SUBMISSION.md`,
`submission.yaml`, and `harness/protocol.py`. No scenario ground truth was used
to design an agent. The kit is outside Git and has not been copied or published.

## Next work: Mridul

1. Implement a dedicated official adapter; `adapters/internal.py` currently has
   a placeholder that still says the official kit is unavailable. Keep the
   internal contract and translate at the boundary.
2. Export a Python class constructed as `(in_queue, out_queue)`, with async
   `setup()` and `run()`. The evaluator imports it in-process and runs it on
   the harness event loop. Keep initialization trivial, cold loading in setup,
   and inference off the event loop. Clean up owned tasks when run is canceled.
3. Convert `{timestamp_ms, event_type, payload}` events, dynamic tool manifests,
   and official success/error tool results into internal types. Tool calls must
   go to the harness, not the demonstration executor. Preserve call IDs.
4. Accumulate text fragments within a turn and emit replacing internal transcript
   revisions. Do not confuse official additive chunks with internal replacement
   hypotheses. Preserve interruption text as new correction evidence.
5. Translate actions to `filler_speech`, `tool_call`, `cancel_tool`,
   `clarification_request`, and `final_response`. Put a plain-value slot snapshot
   at the top level of every final response. Internal error actions need a
   deliberate handling policy; they are not a recognized official action kind.
6. Map virtual milliseconds consistently; do not equate accelerated replay time
   with wall time. `scenario_end` leaves a tail window (default 6000 virtual ms)
   for pending work, so it must not immediately cancel all outstanding calls.
7. Add protocol conformance and shutdown tests before live evaluations. Validate
   outgoing actions with the supplied validator; do not read scenario answer
   keys or author annotations from the agent. Run public evaluation at time
   scale 1 and record backend, configuration, commit and traces.
8. Build submission layout/configuration with an importable entry point and
   reproducible dependencies. Preserve the current chosen model configuration;
   do not introduce a new provider merely because the kit examples name one.

## Coordinate with Atishay before media integration

**Both Mridul and Atishay must agree on these seams. Neither implements the
other person's components.** Mridul owns the official queue adapter, contracts,
clock translation and evaluation; Atishay owns perception and its assigned
worker, turn policy and browser demonstration.

- Official audio is MP3 clips, including multiple clips in a turn. Agree whether
  decoding/assembly lives behind Atishay's perception interface or in an A-owned
  media adapter. Agree timestamps, source IDs, end-of-turn semantics, size limits
  and cancellation before changing either side. Do not silently feed MP3 into a
  WAV-only validation route or substitute a handwritten transcript.
- Official frames are raw PNG references used as context. Preserve source IDs
  and agreed replacement/conflict semantics; existing conflicting-frame xfail
  remains a specification/test issue requiring both owners.
- Agree speech completion versus stop-speaking versus cancel-task behavior.
  Official interruption text must reach the planner, rather than being dropped
  as a mere transport signal. Existing C1–C4 coordination remains relevant.
- The official outer agent must be in-process. An internal perception worker is
  a separate architectural choice; check packaging/runtime constraints before
  relying on it. Do not treat its JSONL transport as the official wire protocol.

No official scenario, live model, Docker, or submission readiness claim follows
from this merge. Registration, final publishing/submission and release tagging
remain separate actions.
