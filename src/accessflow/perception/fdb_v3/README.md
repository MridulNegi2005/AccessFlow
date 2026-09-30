# FDB-v3 LiveKit adapter

This optional adapter runs the existing AccessFlow controller inside one LiveKit
voice session per room. Groq transcribes, LiveKit Inference plans and speaks,
and AccessFlow executes
the 12 official mock tools. The adapter writes the official room-scoped tool-call
log, starts each room with fresh state, and never uses scenario answers.

## Local setup

1. Use Python 3.11 and install the project plus
   [`requirements.txt`](requirements.txt) in an agent virtual environment.
   The root lockfile is intentionally untouched because it belongs to the
   shared-code owner. The official scorer adds NeMo and its README uses a
   different Python setup. Give the scorer a second environment on the same
   machine so its heavyweight dependencies cannot change the tested agent
   environment. Its `livekit-agents~=1.3` range includes the agent's 1.8.3
   pin; the separation is for reproducibility, not a proven version conflict.
2. Clone `https://github.com/DanielLin94144/Full-Duplex-Bench` at commit
   `3e799c45a045256f47d5f1c9cda90157e2d2ec9e`. Set `FDB_V3_ROOT` to
   its `v3` directory. The agent validates all 12 official tool signatures
   before starting a room.
3. Download the separate `fdb_v3_data_released.zip` linked from the official
   v3 README. Verify it is a ZIP, extract its `fdb_v3_data_released/` directory
   under `FDB_V3_ROOT`, and confirm that it contains 100 `input.wav` files.
   Keep recordings and result files outside this repository.
4. In [LiveKit Cloud](https://cloud.livekit.io), create a **project** inside
   the account, then open that project's API keys page. Set `LIVEKIT_URL`,
   `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` in `FDB_V3_ROOT/.env.local`.
   The official clone ignores that file, and both this agent and the official
   runner read it. Set `ACCESSFLOW_GROQ_API_KEY` (or `GROQ_API_KEY`) there too
   if it is not already in the private user environment. Do not paste API
   secrets into this repository, chat, or screenshots. A Cloud account alone
   does not supply project keys.
   The worker uses LiveKit Inference `openai/gpt-5.6-luna` and AccessFlow's
   `compact-v2` planner profile by default. Set `FDB_LIVEKIT_MODEL` or
   `FDB_PROMPT_PROFILE` to change them. `FDB_PLANNER_PROVIDER=groq` selects the
   earlier Qwen planner; `FDB_GROQ_MODEL` then controls its model. That path
   reached this account's 7,000 input-token-per-minute limit during multi-step
   cases. The LiveKit planner completed released two- and three-tool recordings
   in bounded local checks, but these are not an official aggregate score.
   Groq `whisper-large-v3` now transcribes by default with a general domain
   vocabulary hint; `FDB_GROQ_STT_MODEL` can select another supported model.
   By default, speech uses LiveKit Inference's `deepgram/aura-2` voice, billed
   through the LiveKit project. Set `FDB_TTS_PROVIDER=groq` to use Orpheus;
   the Groq account owner must then accept the
   [Orpheus model terms](https://console.groq.com/playground?model=canopylabs%2Forpheus-v1-english).
   This account returned `model_terms_required` in that optional mode.

From the repository root, with the **agent environment** active, run:

```powershell
$env:FDB_V3_ROOT = 'C:\path\to\Full-Duplex-Bench\v3'
python -m accessflow.perception.fdb_v3.agent check
python -m accessflow.perception.fdb_v3.agent dev
```

`dev` is for local evaluation. Use `start` for a production-style worker. The
agent writes `agent_tool_calls.log` where the official runner reads it. On
Windows, that is the `tmp` directory on the benchmark clone's drive; the
worker's `FDB_TOOL_LOG` override can set that exact location if needed.

Run the official scorer in a **second terminal on the same machine** with its
own environment (the official README uses Python 3.10), documented
Python/NeMo/ffmpeg dependencies, the same LiveKit project, and the extracted
recordings. The official runner reads `/tmp/agent_tool_calls.log` directly;
the worker writes that path on Linux. On Windows, `Path('/tmp/...')` resolves
to the `tmp` directory on the scorer's current drive. Run both processes from
the benchmark clone's drive, or set `FDB_TOOL_LOG` for the worker to that
drive's `tmp/agent_tool_calls.log`. The official runner does not read
`FDB_TOOL_LOG`. A GPU run on another machine therefore needs both environments,
the agent code, and the private `.env.local` configured there; moving only the
scorer would lose the tool-call evidence.

Start with one released example:

```powershell
cd $env:FDB_V3_ROOT
python run_tool_benchmark.py --provider accessflow --example 'EXAMPLE_ID_FROM_A_RELEASED_FOLDER'
```

Then use `run_tool_benchmark_all_released.py --provider accessflow` for the
full set. Run `evaluate_tool_calls.py`, `evaluate_pass_rate.py`, and
`analyze_tool_latency.py` on those results. The official `--use-llm` judge
requires its separately configured OpenAI key; an exact-match run without
that judge is diagnostic, not the organizer's score. Keep the generated
recordings, logs, and reports out of the AccessFlow repository. See the
[official v3 README](https://github.com/DanielLin94144/Full-Duplex-Bench/blob/main/v3/README.md)
for the runner's current commands and audio download link.

## LiveKit hooks

- `user_state_changed` marks speech as pending immediately. This holds a
  possible write while the transcription is still being decided.
- `on_user_turn_completed` receives the final transcript from LiveKit.
- `llm_node` passes that transcript to the AccessFlow controller. It waits for
  every dispatched mock call to finish logging and summarizes confirmed
  results when concurrent calls would otherwise leave the spoken reply partial.
  The configured LiveKit LLM object also lets the SDK schedule this custom
  node; AccessFlow makes the actual reasoning request.

Released flight and finance recordings completed through LiveKit with audible
replies and room-scoped telemetry. A separate transcription of the final
finance output heard all three confirmed results. One scripted active-speech
interruption also produced the later corrected cart action. Other recordings,
interruption reliability, official scoring, and a physical microphone remain
separate checks. Passing unit tests or these bounded runs does not establish a
benchmark score.

## Separate in-car destination extension

`accessflow.perception.navigation_agent` uses the same AccessFlow controller,
LiveKit speech path, and interruption handling with a separate two-tool
catalog. Its `set_navigation_destination` action changes a simulated route
for that room and projects it into a local SQLite-backed dashboard. It
supports Central Station, City Hospital, and Airport Terminal 1; an unknown
place leaves the route unchanged. It does not control a car, calculate a road
route, or use FDB benchmark tools or data.

Stop the benchmark worker before starting this worker; both use LiveKit's
default unnamed dispatch. Set `NAV_ENV_FILE` to a private file with the same
LiveKit and Groq keys (or set those variables in the environment), then run:

```powershell
$env:NAV_ENV_FILE = 'C:\path\to\private\.env.local'
$env:NAV_STATE_DB = 'C:\path\to\local\navigation.sqlite3'
python -m accessflow.perception.navigation_agent dev
```

In another terminal, start the local display with the **same** `NAV_STATE_DB`:

```powershell
$env:NAV_STATE_DB = 'C:\path\to\local\navigation.sqlite3'
python -m uvicorn demo.navigation_app:app --host 127.0.0.1 --port 8011
```

Open `http://127.0.0.1:8011/?room=YOUR_LIVEKIT_ROOM`. Use a separate LiveKit
room for each simulated trip. A successful destination change is acknowledged
aloud, shown on the display, and logged with the final revision. The route
starts at Central Station for every room; the dashboard retains the latest
local state after a room closes for demonstration. The database stays outside
the repository and carries no benchmark state.
