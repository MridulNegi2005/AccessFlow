# Prompt for Atishay to give his Codex

I am Atishay, working on AccessFlow with Mridul. We have merged our branches, and a fresh audit was made on 17 September 2026 against `main` at `476a7b5`.

Read `docs/reviews/ATISHAY_MERGED_AUDIT_2026-09-17.md`, the current repository instructions and my handoff. Also read the coordination section in `docs/reviews/MRIDUL_MERGED_AUDIT_2026-09-17.md`. Inspect my current branch first; do not overwrite newer work just because the audit describes an older checkout.

Work only on my portion: perception, turn policy, demo, their tests, media/provenance and my handoff. The explicitly assigned exception `src/accessflow/adapters/perception_worker.py` is also mine. Mridul owns the controller, shared contracts, other adapters, corpus, evaluation harness, engine tests and root configuration/lockfile. Do not implement his fixes or silently modify his files.

Start by reproducing the native-work timeout/close issue with a gated transcriber. Fix the real concurrency/lifecycle bound, not only the canceled asyncio wrapper. Complete the assigned vision-worker wiring against the agreed provider/options and preserve audio-only behavior. These can be developed with deterministic doubles without waiting for Mridul's service or API quota.

C1, C2, C3 and C4 explicitly require **Mridul and me to coordinate**: frame replacement/conflict semantics, speech timing and stop scope, the shared configured agent path, and media-to-task evaluation. For each, give me a concise proposal with an example event trace, the decision needed from Mridul, and the exact file split. Continue independent work while that decision is pending. Once agreed, implement only my side.

Do not fix the frame-conflict xfail by merely removing its marker: it currently times out before its safety assertion and lacks a clear authorization setup. Do not duplicate Mridul's planner/controller logic in the demo. Do not fabricate live evidence, present uploaded whole-file ASR as live endpointing, or reuse consumed cases as unseen evaluation.

For each slice, report the reproduced failure, owned files changed, test commands/results, evidence mode and remaining limitations. Run my owned tests and the merged suite after integration. Keep changes reviewable. Do not push, enable CI, submit or create a release tag unless I separately ask you to.
