# Kaggle GPU evaluation

The private Kaggle runner prepares separate agent/scorer environments and can run AccessFlow against all released FDB-v3 audio. Installation or a green notebook badge is not a benchmark score.

## Launch

1. Import `notebooks/AccessFlow_FDB_Kaggle.ipynb` into a private Kaggle notebook. Enable Internet and select a CUDA GPU.
2. In Add-ons > Secrets attach `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` and `ACCESSFLOW_GROQ_API_KEY`. Attach `OPENAI_API_KEY` for full reference judging. Never put key values in notebook code or output. Verify attachments after every notebook version update.
3. Set `ACCESSFLOW_KAGGLE_MODE` in the notebook configuration to the intended mode and run it:

| Mode | Behavior |
| --- | --- |
| `prepare` | Default: install environments, load GPU ASR, verify/extract corpus; no agent benchmark |
| `run` | Real inference; no semantic/latency grade or judge key required |
| `reproduce` | Real inference plus unchanged reference grading; judge access required |

4. Inspect `accessflow-fdb/evidence/kaggle-status.json`, setup logs and the supervised run's `manifest.json`.
5. Download evidence before ending the notebook session: original manifest, result JSON/audio, runtime logs, hardware/configuration, dependency freeze and judge audit. Keep raw audio and keys private; publish only reviewed summaries.

## Pinned profile

- Runner: `scripts/kaggle_fdb.py`, embedded in the notebook.
- Agent source selected by the runner: `1030321a0dcbafcf97db5fbbad86423b57ba35b5`.
- Reference: `3e799c45a045256f47d5f1c9cda90157e2d2ec9e`.
- Agent: frozen Python 3.11 FDB extra; Groq Whisper Large v3, LiveKit Inference `openai/gpt-5.6-luna`, Deepgram Aura-2 speech output.
- Scorer candidate: Python 3.10, Torch/Torchaudio 2.6.0 with CUDA 12.4, NeMo 2.4.0, separate `livekit-api==1.2.1` distribution.
- Reference ASR: `nvidia/parakeet-tdt-0.6b-v2`.
- Reference semantic/latency judge: OpenAI `gpt-4o`, independent of agent planning.

The candidate profile has passed installation, official transport import and GPU ASR warm-up. This does not prove benchmark correctness, container compatibility or clean-host reproduction. The resolved scorer freeze is not a hash-locked install. Later repository changes do not change the source pin inside an existing notebook run.

Samsung's guide requires one pinned judge for its organizer rerun; it does not explicitly require a participant purchase of OpenAI credit. Unchanged public reference grading needs working OpenAI API access. An alternative judge must be described as a separate diagnostic.

## Progress and failure interpretation

The full corpus contains approximately 78.6 minutes of audio. Input is streamed in real time and sequentially; room setup, silence, output conversion and ASR add overhead. The wrapper prints only stage starts/ends and redirects child logs to `reproduce.log`, so a running stage can remain visible for over an hour. LiveKit rooms demonstrate activity, not saved-result or pass counts.

Do not restart an active run merely to improve console logging. Inspect terminal artifacts and supervised status. An upstream process can catch client failures and still exit zero; the supervisor rejects an all-failure batch and missing/malformed coverage.

The [retained-output procedure](FDB_REPRODUCTION.md#score-a-retained-kaggle-run-without-repeating-audio-inference) restores checksum-verified outputs and grades them without repeating real-time inference or requiring GPU/NeMo. A new agent version requires new inference. For repairs, use focused regression tests and an isolated development audio subset before another complete run; the full supervisor still requires all 100 originals.

See [reproduction instructions](FDB_REPRODUCTION.md) and [evaluation scope](EVALUATION_QUICK_GUIDE.md). Provider credentials remain outside Git, and official benchmark answers never enter the agent.
