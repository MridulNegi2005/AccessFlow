# Prompt for Atishay's agent — 24 September 2026

Copy the text below. The speaker is Atishay; Mridul is his teammate.

---

I am Atishay, working on AccessFlow with my teammate Mridul. We have merged his branch into main first and mine second. I want you to work on **my voice/perception/demo integration and testing**, respecting our existing file ownership. Mridul handles the engine, shared contracts, Samsung adapter, execution, evaluation harness, root dependencies and packaging. Do not do his implementation for him.

First inspect my actual checkout, branch, working tree and fetched origin/main. Preserve any uncommitted work. Integrate current main into my atishay/perception branch by an ordinary merge when safe; do not reset, force-push, rewrite shared history or push main. Read AGENTS.md, .ai-sync/handoff.md, .ai-sync/context.md, docs/STATUS.md and docs/handoffs/atishay.md. Treat historical status as historical and verify current code.

Read these current instructions before old design prompts:

1. docs/reviews/MERGED_READINESS_2026-09-24.md
2. docs/reviews/ATISHAY_VOICE_WORK_2026-09-24.md
3. docs/CONTRACT_PROPOSALS.md and the C24-1 through C24-5 coordination register in the readiness review.
4. The Samsung kit's WALKTHROUGH.md, docs/PROTOCOL.md, docs/SCORING.md and docs/SUBMISSION.md. Locate the kit on my machine; Mridul's copy is in the repository's parent directory under participant-kit/participant-kit.

**Priority change: stop frontend polish.** Preserve the design we already have. Do not spend time on more Stitch exports, variants, animations, static previews or cosmetic redesign. The previous Stitch-first design instruction is superseded for this phase. Fix interface behavior only where it is necessary for real voice capture, interruption, causal results, accessibility, errors and a usable demonstration.

Samsung imports a Python queue agent, not our browser. Automated tests include raw MP3 audio and PNG frames, not just text. About 30% audio and 20% visual are described for the hidden set, with a 1.5x multiplier. Base scoring is task completion 40%, interruption recovery 35%, latency 15%, safety/protocol 10%, plus transcript-quality grading. Typical fast acknowledgment/cancellation targets are around 800 ms, with scenario-specific rules. Official evaluation uses real time, three repetitions per scenario and the median; setup must finish within 300 seconds and scenarios within 120 seconds. The frontend is useful for us to test and demonstrate, but UI design is outside the core Theme 5 scope.

We use pretrained models. Do not start speech-model training, claim fine-tuning occurred, or assume the chosen Qwen reasoner itself provides ASR/vision. Real ASR, vision and reasoning must be identified independently. Do not feed organizer reference transcripts, captions, ground truth or scenario IDs to the agent. No paid/alternate backend fallback without an explicit decision.

My owned implementation is perception/, turn_policy/, demo/, their tests, feedback/presentation materials, and the assigned adapters/perception_worker.py. Mridul owns shared schemas, engine, Samsung protocol/runtime, the process parent and other A adapters, evaluation and lockfile/root configuration. Read his files for context, but propose examples/tests and coordinate instead of changing them. Never duplicate his authoritative state or tool scheduler in the browser.

Build on my existing work: generated media catalog, 18 generated-audio ASR measurements, VAD/activity experiments, worker lifecycle and vision flags, validation and frontend. Do not claim those assets do not exist. Also do not claim those component runs prove human speech quality, live vision or end-to-end task completion. The current primary voice button uploads after recording stops; it is not continuous audio streaming. The default demo still uses mock perception/reasoning and an empty tool manifest, so its previews do not prove Qwen booking behavior.

Work in this order:

1. Reproduce owned correlation and speech-policy gaps with deterministic gated tests. The demo must wait for the response caused by the intended input, not just the first final/error or any final after a matching observation. Keep assertions that combined image+speech reached the reasoner. Distinguish stop speaking, cancel the task and a normal device command such as stop the washing machine.
2. Check actual available ASR/vision models and run real component tests. Preserve revisions, uncertainty and timestamps. Current audio observations are always final and the ASR wrapper flattens output to text; propose the smallest additive contract needed for partial clips/uncertainty. Don't invent confidence or treat a silence gap as definitive completion.
3. Coordinate C24-1/2/3 with Mridul: MP3 admission/decoding/turn assembly ownership; clock/finality/stop-scope contract; common runtime, manifests and response identities. The suggested split is his official adapter/shared contract/controller and my ASR/timing/worker/demo integration. Earlier decoder ownership was undecided; record agreement rather than assume permission to edit his files. Keep doing independent owned tests/recordings while he implements his pieces.
4. Test physical microphone capture and actual transcription, then the agreed ongoing capture/interruption path while the agent speaks or tools run. Show corrected intent and exactly one confirmed mock effect through the common runtime. Separate upload-on-stop, manual button interruption and automatic speech-triggered barge-in in reports. Test echo/noise, denial, disconnect and cleanup. Existing speech callback tests do not prove audible playback.
5. Run actual vision on pixels, missing hints, ambiguity and replacement frames. Coordinate C24-4 with Mridul for context/conflict/write authority. He owns the reproduced pending-frame controller bug and the unfinished patch; do not fix his engine or weaken my tests to hide it.
6. Add a small varied team-recorded set with permission/provenance, and reuse existing generated cases honestly. Send media IDs, hashes, timestamps and labels to Mridul for independent task/effect evaluation (C24-5). Used held-out cases are exposed, not new unseen evidence.
7. With his configured Samsung package, exercise pub_05_audio_asr_ambiguity, pub_06_audio_disfluency and pub_07_visual_port_lookup from raw media at time-scale 1. Coordinate the full three-repetition evaluation and provider quota. Keep official harness/scoring unchanged, preserve every failure, and never pass canned transcripts off as real model output.

The detailed B24-1 through B24-6 acceptance cases and commands are in my work document. Run the owned suite, Node speech-lifecycle check, Ruff and full combined suite for completed integration slices. Fix owned failures with evidence; send Mridul a concrete reproduction for failures in his lane. Do not hide a flaky test by increasing sleeps or rerunning until green.

For each slice, report: reproduction, owned files changed, exact commands/results, actual backend/model and hardware, timings, provenance, limitations and the next independent task. Update my handoff and feedback records. Shared decisions must explicitly say that **both Atishay and Mridul need to coordinate**, with a file split and event example. Make small commits on my branch. Never add assistant/model names, coauthor trailers or attribution signoffs to new authored content/commit metadata; retain existing history. Track required AI disclosure factually without adding such signoffs. Do not submit forms, create the final release tag, activate workflows, publish private recordings, or make real bookings/payments.

My next milestone is working, measured voice correction and interruption with real perception and our actual configured agent. A finished-looking frontend is not completion of my work.
