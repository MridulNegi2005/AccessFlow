# Evaluation guide

AccessFlow targets Full-Duplex-Bench v3 inside LiveKit. The older queue adapter supports development and offline regression testing; the updated Samsung Theme 5 participant guide controls the submission evaluation.

## Evaluation scope

Round 1 is 60% benchmark, 20% working extension and 20% documentation/architecture/video. Only the organizer benchmark rerun counts toward the official score. Strict pass rate breaks ties. Shortlisted teams demonstrate the interrupted agent live and answer design questions.

Automatic evaluation uses 100 real human audio recordings: 79 unique scenarios, 12 speakers and 12 mock tools across four domains. It measures tool selection, arguments, strict pass rate and latency. It is not text-only. A browser interface supports live microphone checks and the extension demonstration; visual polish does not replace voice/tool correctness.

The extension demonstrates an in-car destination change using simulated per-session route state. It is not real vehicle control or a mapping service. Its tool manifests are separate from the benchmark tools.

No foundation-model training is required. Public checkpoints, hosted APIs and custom LiveKit agents are allowed. Benchmark training, memorized scenario answers and cross-session conversational caches are prohibited.

## Model roles

| Component | Purpose | Declared profile |
| --- | --- | --- |
| Agent speech recognition | Transcribe live input | Groq `whisper-large-v3` |
| Agent reasoning | Interpret intent and choose tools | LiveKit Inference `openai/gpt-5.6-luna` |
| Agent speech output | Speak responses | LiveKit Deepgram Aura-2 |
| Reference ASR | Transcribe input/output for timing and grading | GPU NeMo `nvidia/parakeet-tdt-0.6b-v2` |
| Reference judge | Grade semantics and substantive-response timing | Unchanged public scripts call OpenAI `gpt-4o` |

The judge is independent of the agent. Its API key is unnecessary for listening, planning, tools or speech output. Samsung's guide requires a pinned judge for the organizer rerun and does not explicitly require teams to purchase OpenAI credit. Using a different judge produces a separately labelled diagnostic, not an equivalent reference or official score.

## Interpret evidence correctly

- Contract/state-machine tests establish controlled software behavior.
- Dependency installation, transport imports and GPU warm-up establish environment readiness.
- LiveKit room activity establishes sessions/media activity, not task success.
- Human-observed microphone checks establish manual acceptance for the observed interaction; numerical timing or post-close safety claims require retained traces.
- Result JSON and response audio establish recorded inference outcomes when coverage/provenance are validated.
- Judge audits expose failed or malformed grading requests; they do not prove judge accuracy.
- Only the organizer rerun establishes Samsung's official score.

No complete official aggregate score is claimed here. Consult the dated sanitized evidence files under `docs/evidence` for recorded checks and their limits. Historical evidence is not live runtime status.

## Runtime and repeatability

The released originals contain 78.632 minutes of audio, with recordings approximately 36.36–59.16 seconds long. The reference streams in paced chunks and processes recordings sequentially. Room setup, silence and response ASR add overhead. GPU acceleration does not eliminate real-time conversation duration.

Kaggle prints stage starts/ends while child output is redirected to `reproduce.log`; a long-running stage does not imply a hang. Inspect terminal manifests and result coverage. For faster development, test focused regressions and small isolated audio subsets, clearly labelled with their actual count. They do not replace the full benchmark.

Preserve inference manifests, result JSON, response WAVs, source/reference pins, configuration and failure counts. Saved outputs can be graded without a live agent, GPU or NeMo. Changed agent behavior needs fresh audio inference; grading old outputs cannot validate a newer implementation.

See [complete reproduction and retained-output scoring](FDB_REPRODUCTION.md), [Kaggle setup](KAGGLE_FDB.md), and the [LiveKit adapter](../src/accessflow/perception/fdb_v3/README.md).

## Sources

- Organizer `Theme05_Participant_Guide_UPDATED_FBD.docx`, supplied in the participant kit: benchmark/LiveKit/extension, deliverables, weighting, organizer rerun, model permissions and benchmark-training restrictions.
- [Pinned FDB-v3 reference](https://github.com/DanielLin94144/Full-Duplex-Bench/tree/3e799c45a045256f47d5f1c9cda90157e2d2ec9e/v3): paced audio in `livekit_inference.py`; released iteration in `run_tool_benchmark_all_released.py`; Parakeet ASR in `run_tool_benchmark.py`; reference judging in `evaluate_tool_calls.py`, `evaluate_pass_rate.py` and `analyze_tool_latency.py`.
- Repository `.env.fdb.example` and `scripts/kaggle_fdb.py`: provider selectors, source pins, separate environments and logging.
