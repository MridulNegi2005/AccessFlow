# Atishay acceptance audit — 26 September 2026

Status: **BLOCKED / PARTIAL, not complete**. This audit does not supersede or
erase the failure history in [the delivery report](ATISHAY_DELIVERY_RESULTS_2026-09-25.md).

## Current state

- Clean `atishay/perception` at `6eefd68bb3965bded4beb8b972cbbe4c8b558d78`,
  synchronized with its remote at audit start.
- `git fetch origin --prune` succeeded. Fetched main remains
  `5dd2a56ce7f063335fb2fcb0fbfe4f127640e9a6`; `git merge origin/main` reported
  `Already up to date`. No new shared implementation arrived.
- No reset, force-push, shared-source edit or model-memory retry was performed.

## Acceptance verdict

| Requirement | Evidence | Verdict / dependency |
| --- | --- | --- |
| Gate 1: all 26 behaviors | Existing case-by-case checklist plus fresh `.venv\Scripts\python.exe -m pytest tests/perception/test_confirmed_stop_semantics.py -q --runxfail`: **2 failed, 1 passed**, 2.75 s, exit 1. Bare Stop emitted no required output-stop; Stop speaking timed out waiting for the required acknowledgement. Explicit task cancellation passed. | FAIL. Shared D1 decisions/controller effects are absent. Browser playback alone cannot supply task authority. |
| Gate 1: ordered multi-image reasoning | Current `engine.py` still replaces `active_frame`, removes the previous observation and accepts image observations only for the active frame. `TurnDecision` still has only continue/complete/possible_correction/backchannel/stop. | BLOCKED at shared D4 registry/view and source guards. Browser thumbnails and owned per-image perception do not prove cross-image reasoning. |
| Gate 2: twelve actual-inference runs | Four fixed cases and twelve IDs exist in `GATE2_PREDECLARED_2026-09-25.json`. Fresh check: reasoning/vision environment configuration absent; Ollama absent from PATH and no loopback 11434 listener. | NOT RUN. Requires the approved configured reasoning/vision runtime, plus D4 for the two-image case. Native-ASR memory issue remains assigned to Mridul by the user; no retry here. |
| Gate 3: four physical-mic cases | No new human audio captured; no new device evidence. | NOT RUN. Must follow a working configured runtime and the user's capture agreement. Synthetic speech and Node capture tests cannot substitute. |
| Gate 4: regression and reproducibility | Last implementation check: 1388 passed, 6 skipped, 3 xfailed, 2 warnings; seven Node checks and Ruff passed. Not rerun wholesale for this documentation-only audit. | Standard regression passed; full gate still incomplete because installed-model rerun failed previously, real-mode launch/device behavior and official kit compatibility remain unverified. |

## Exact unblock sequence

1. **Mridul:** add the agreed D1 output-only-stop and hold/clarify decisions and
   controller effects. Keep task context/authorization for output-only stop;
   vague stop must hold new dispatch and clarify without cancelling the session.
   The executable reproducer is the command above. **Atishay afterward:** map
   the classifier to the agreed kinds and verify integrated playback/task cases.
2. **Mridul:** land D2/D3 pending-speech/finality/closure hooks and D4 bounded
   image registry with stable ordinal, receipt time, field-level source selection
   and write guards. **Atishay afterward:** bind authoritative metadata to the
   existing image UI and complete the owned conformance checks. Do not invent a
   separate frontend authority or renumber images by completion time.
3. **Runtime coordination:** make the already approved reasoning/vision provider
   available and resolve the native-ASR resource issue. No model switch or paid
   fallback is authorized. Then **Atishay** runs the twelve fixed development
   attempts, retaining every outcome and causal ID, before the four human-mic
   checks. These remain Atishay acceptance obligations, not completed work.
4. **Kit access:** provide the local participant-kit location for WALKTHROUGH,
   PROTOCOL, SCORING and SUBMISSION; earlier bounded searches did not find it.
   That is a local availability gap, not a claim that the organizer omitted it.

The same dependencies have persisted across the preceding pushed checkpoints.
The independent browser/perception fixes are preserved and tested. Further
browser-only changes would not establish these missing shared/runtime/device
requirements; resume integration when the dependency state changes.
