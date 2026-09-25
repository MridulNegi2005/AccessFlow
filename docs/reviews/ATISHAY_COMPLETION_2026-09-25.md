# Atishay completion handoff - 25 September 2026

## Read first

- `AGENTS.md`, `.ai-sync/handoff.md`, `docs/STATUS.md`.
- `docs/reviews/MERGED_READINESS_2026-09-25.md` (current review, reproductions and owners).
- `docs/CONFIGURED_RUNTIME_2026-09-24.md` and
  `docs/MEDIA_COMPLETION_COORDINATION_2026-09-24.md` (A's runtime now merged).
- `docs/SAMSUNG_AUDIO_ADMISSION_2026-09-24.md` and `docs/CONTRACT_PROPOSALS.md`.
- Original kit's protocol/scoring/submission documents on your machine. The kit is
  available on Mridul's machine at `Samsung GenAI/participant-kit/participant-kit`;
  absence from your local download directory is not an organizer-wide blocker.

Main now includes Mridul `81699c9` followed by Atishay `469e590`; tested code merge
is `dcd9756`. Pull before continuing. Do not overwrite dirty local work or force-push.
Use `git fetch origin --prune`, inspect `git status`, update local main with
`git switch main` / `git pull --ff-only origin main`, then merge `origin/main`
into your own `atishay/perception` branch. Preserve both histories if conflicts occur.

## What your changes successfully delivered

- Better multi-source final/clarification correlation and stale-error rejection.
- Microphone permission/disconnect recovery checks.
- Raw, immutable, source-correlated ASR diagnostics with honest uncalibrated labels.
- Correct separation of booking/device commands from explicit task cancellation.
- Timing replay based on the newest final revision, and real installed-ASR worker
  tests that also pass on the merged Python 3.11 tree.

The merged suite is 1368 passed, 4 skipped, 1 expected failure. Two ASR skips were
run separately: 2 passed. Do not claim "all voice work complete": the following
are open, and your own latest notes acknowledge most of them.

## B25-1: fix the new pre-observation error regression first

Reproduce from repo root:

```powershell
python docs/evidence/merged-2026-09-25/probe_error_transport.py
node docs/evidence/merged-2026-09-25/probe_browser.cjs
```

The actual WebSocket sends the server-generated causal ID only when perception
succeeds. An ASR failure has no preceding final observation. Your new error filter
therefore does not recognize the failed request and hides its error for 90 seconds.

**Owned repair:** establish event identity at input acceptance, before invoking
perception. A bounded server acknowledgment may map current task/source/revision
to the generated event ID; alternatively propose an explicit client-ID contract.
Choose one and test the ordering. The browser must retain current accepted IDs
even when decoding fails, and reject previous-task/stale-revision errors. Do not
allow all error events through merely to make the reproduction pass. Show a safe
message for `backend_failure` and other defined codes rather than raw exceptions.

**Acceptance tests:** valid WAV with injected ASR exception/empty transcript;
valid PNG with provider exception; failed input before any observation; error while
other media succeeds; late failure from old task; duplicate failure; reconnect;
recovery with a subsequent good input. Assert no generic 90-second wait, controls
recover, and no stale failure terminates the new task. Retain raw reproduction
outputs and add permanent tests in your owned directories.

## B25-2: finish stop classification and output playback

Run `python docs/evidence/merged-2026-09-25/probe_stop.py`.
Current results: "Stop" and "Cancel" invoke planning; "Stop speaking" invokes
planning without an output-stop signal; "Cancel this task" stops correctly.
The browser projection also ignores `stop_output=True` on controller output.

**Both Mridul and Atishay must coordinate** on the shared decision/action meaning.
You own the classifier and playback; Mridul owns shared contracts/controller logic.
Agree bare-stop behavior explicitly. Keep ordinary "Stop the washing machine" and
"Cancel this booking" as requests, and avoid acting on partial stop hypotheses.
Wire playback cancellation to authoritative output-stop events as well as local
buttons. Preserve the current task for output-only stop; never claim a committed
effect was rolled back because speech playback stopped.

**Acceptance tests:** stop during TTS, stop during a slow read, task cancel during
a mock pending write, late TTS callbacks after cancellation, stop followed by a
correction, ordinary device cancellation, partial "cancel...", repeated stop,
old-session stop event. Use gates to control execution rather than arbitrary sleeps.

## C25-1/2: minimal real voice path, not more frontend design

The page still uses a default mock reasoner / separate optional Ollama route,
FinalFlagPolicy and fake tools. Its current human-mic evidence is a recorded WAV
plus local ASR plus mock echo. It does not test the Qwen submission runtime.

Mridul's configured factory and Samsung MP3 bridge are now on main. Read their
docs and call the shared runtime instead of creating a second planner. You own
WebSocket/capture/playback; Mridul supplies additive callback/configuration seams
if needed. Keep tests independently runnable with an explicit fake-agent mode.

**Both must coordinate** on source/revision, capture-to-session clock mapping,
pending speech, acoustic activity and finality. Raw ASR word probabilities and
WAV-relative timestamps are not calibrated confidence or global turn endpoints.
The process-worker diagnostic transport still needs an agreed schema if it is
required; retaining metadata in a direct LocalPerception sink alone does not wire it.
Do not block the whole delivery on a diagnostic dashboard or confidence calibration.

Implement the smallest agreed live capture path that can interrupt pending output,
retain a pause without a premature write, and send a superseding correction. The
current Finish-and-upload interaction cannot demonstrate speech-triggered barge-in.
No redesign is needed. Keep microphone opt-in and request human testing only when
the implemented behavior is ready to test.

## C25-3: actual image completion and frame acceptance semantics

Your machine's missing Ollama/kit was an environment gap. Mridul has a verified
portable installation and documented package setup; coordinate the supported
profile. Run actual image inference and produce an image-grounded final within
official timing. Do not solve missed evaluation tails by changing the evaluator.
You own provider/worker efficiency; Mridul owns deployment/adapter deadlines.

The known conflicting-frames xfail still times out waiting for both old/new frames,
while the current engine replaces the old frame. **Both must agree** replacement
versus simultaneous conflicting evidence semantics. Then you update the owned
acceptance test; Mridul changes the controller only if the agreed contract requires
it. The present timeout is not proof of an executed unsafe write.

## Evidence to return

For each slice: before reproduction, files changed, exact commands/results,
backend and fixture provenance, limitations and a commit SHA. Run relevant Python
and Node regressions and one full suite after integration. Real-model, generated
audio, human-mic, fake reasoning and mock effects must remain distinguishable.

For the final voice check, record with consent or use anonymized written results:
pause then continuation, Tuesday to Wednesday at five, interruption while response
or mock tool is pending, no speech/noise, permission denied, disconnect/reconnect,
and late old ASR. Record substantive completion and extra wait separately from ack.
No need to publish personal recordings or perform real external actions.

## Copy-paste prompt (Atishay speaking)

I am Atishay. Mridul has merged both our branches into main, his first and mine
second. Start by checking for uncommitted work, fetching origin, pulling main
safely and merging origin/main into my atishay/perception branch. Do not reset or
force-push anything.

Read AGENTS.md, .ai-sync/handoff.md, docs/STATUS.md,
docs/reviews/ATISHAY_COMPLETION_2026-09-25.md, and
docs/reviews/MERGED_READINESS_2026-09-25.md. Also read the configured-runtime,
media-coordination and Samsung-audio-admission docs referenced there.

My priority is submission-complete working code, not frontend styling or model
accuracy tuning. Fix my pre-observation error correlation regression first, then
my playback/stop handling and minimal real voice integration. Reproduce findings
with the supplied probes and add owned regression tests. Do not claim the mock
echo proves a real-agent voice task. Use the shared configured runtime Mridul has
now merged; do not rebuild his planner or controller in my UI.

Work only in my perception, turn-policy, demo, assigned perception worker and test
areas. Mridul owns the shared contracts, engine, adapters other than my assigned
worker, packaging and evaluation infrastructure. Wherever the review says both
must coordinate, write the smallest concrete contract example and expected
behavior for Mridul; continue independent owned work while awaiting the decision.
Do not silently modify his files. Keep explicit fake mode for independent tests.

Verify real installed ASR, actual vision and microphone interruption through the
common agent, plus errors/timeouts/reconnect and stale results. Keep human versus
generated audio, real versus fake inference and mock effects clearly labeled.
Read the official kit: evaluation is not text-only, and a polished page does not
replace the queue entry, raw audio/image handling and interruption protocol.
Report exact commands, before/after results, backend, commit and remaining gaps.
Do not create a final release tag, submit forms, or claim all issues are closed
without the corresponding evidence.
