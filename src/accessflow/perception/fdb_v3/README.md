# FDB-v3 LiveKit adapter

The adapter runs the AccessFlow controller in one voice session per LiveKit room. Groq transcribes input, LiveKit Inference provides planning and speech output, and AccessFlow executes the 12 reference mock tools. Each room starts with fresh conversational state. Benchmark expected answers never enter the agent. Tool telemetry is room-scoped.

## Setup

Use Python 3.11 and install the frozen optional dependencies from the repository root:

```powershell
uv sync --frozen --extra fdb
```

Clone the reference at `3e799c45a045256f47d5f1c9cda90157e2d2ec9e`, set `FDB_V3_ROOT` to its `v3` directory, and extract the released corpus there. The worker validates the 12 tool signatures. The full supervised evaluation expects all 100 released original WAVs.

Supply private `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` and `ACCESSFLOW_GROQ_API_KEY` settings through the process environment or reference `v3/.env.local`. Never commit populated configuration or expose it in screenshots.

Defaults are Groq `whisper-large-v3`, LiveKit `openai/gpt-5.6-luna` planning, the `compact-v2` prompt profile and LiveKit `deepgram/aura-2` speech output. Configure these with `FDB_GROQ_STT_MODEL`, `FDB_LIVEKIT_MODEL`, `FDB_PROMPT_PROFILE` and `FDB_TTS_PROVIDER`. Optional Groq planning uses `FDB_PLANNER_PROVIDER=groq` and `FDB_GROQ_MODEL`; optional Groq speech output may require provider model-terms acceptance. Record the actual backend and limits rather than silently switching providers.

## Worker commands

From the repository root:

```powershell
$env:FDB_V3_ROOT = 'C:\path\to\Full-Duplex-Bench\v3'
uv run --frozen --extra fdb python -m accessflow.perception.fdb_v3.agent check
uv run --frozen --extra fdb python -m accessflow.perception.fdb_v3.agent dev
```

`check` validates configuration/imports; it is not an audio acceptance test. `dev` starts a local worker; `start` is the production-style entry point. Use exactly one matching unnamed worker in the evaluation project.

The reference scorer needs a separate compatible Python/NeMo/ffmpeg environment on the same host. Both processes must share the tool log: `/tmp/agent_tool_calls.log` on Linux, or the reference drive's `tmp/agent_tool_calls.log` on Windows. `FDB_TOOL_LOG` configures the worker; the unchanged official runner reads its fixed path.

Prefer the [supervised reproduction command](../../../../docs/FDB_REPRODUCTION.md) for full inference, grading, coverage checks and sanitized judge audits. A targeted released-data subset can use the unchanged `run_tool_benchmark_all_released.py --provider accessflow --root_dir <private-subset>` after separately starting/configuring its worker. It is development evidence, not a full benchmark result.

Reference semantic/latency grading uses its independent OpenAI judge key. This is separate from LiveKit planning. An exact-match tool diagnostic or alternate judge cannot be labelled the organizer's official score. Retain actual audio/results/configuration; keep bulk recordings and private logs outside Git.

## Session hooks

- `user_state_changed` marks speech pending immediately and holds possible writes while transcription resolves.
- `on_user_turn_completed` receives the final transcript.
- `llm_node` sends the transcript through the AccessFlow controller, waits for dispatched calls to finish logging, and summarizes confirmed results. AccessFlow makes the reasoning request while LiveKit schedules the node.

Tests, provider connectivity and bounded audio examples each establish different evidence. Only a validated complete run and its grading reports establish an aggregate reference result; Samsung's organizer rerun establishes the official score.

## In-car destination extension

`accessflow.perception.navigation_agent` reuses the controller and LiveKit speech/interruption path with a separate two-tool catalog. `set_navigation_destination` changes a simulated route per room and projects it to a local SQLite dashboard. Supported destinations are Central Station, City Hospital and Airport Terminal 1; unknown places leave the route unchanged. It does not control a vehicle, calculate road routes or load benchmark tools/data.

Stop the benchmark worker before starting the extension because both use default unnamed LiveKit dispatch. Keep the database and provider settings outside Git:

```powershell
$env:NAV_ENV_FILE = 'C:\path\to\private\.env.local'
$env:NAV_STATE_DB = 'C:\path\to\local\navigation.sqlite3'
uv run --frozen --extra fdb python -m accessflow.perception.navigation_agent dev
```

In a second terminal use the same database path:

```powershell
$env:NAV_STATE_DB = 'C:\path\to\local\navigation.sqlite3'
uv run --frozen --extra fdb python -m uvicorn demo.navigation_app:app --host 127.0.0.1 --port 8011
```

Open `http://127.0.0.1:8011/?room=YOUR_LIVEKIT_ROOM` and connect a microphone-capable LiveKit client to that exact room. Use a fresh room per simulated trip. A confirmed change is spoken, displayed and recorded with its revision. Each room starts at Central Station; the dashboard can retain its final local projection after closure for demonstration. See [running instructions](../../../../docs/RUNNING.md) and [evaluation scope](../../../../docs/EVALUATION_QUICK_GUIDE.md).
