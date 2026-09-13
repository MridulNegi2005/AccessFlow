# Reproducible development commands

Use Python 3.11 and uv 0.11.16 (the version used locally). From repository root:

```powershell
uv python install 3.11
uv sync --frozen --extra dev
uv run pytest -q
uv run ruff check .
uv run accessflow replay scenarios/dev/text_correction.json
uv run accessflow metrics artifacts/replay.jsonl
```

`uv.lock` pins the dependency resolution. `artifacts/` is local output and ignored by Git.
Commit selected reviewed final metrics under docs/results/ later, with commit/configuration
and provenance. The synthetic example is development-only, not one of the teammate-held-out cases.

## Optional live reasoning

No provider switch is automatic. There are zero automatic retries on quota/network failure.
The controller bounds inference; HTTP adapters use a single async worker and a bounded context.
MockOnlyAuthorization is appropriate here only because the replay always uses FakeTools.
The generic engine defaults to denying writes. Do not connect that mock authorization to
a real executor. All external booking/service effects remain excluded by project scope.

Install Ollama separately, then explicitly download the selected model before evaluation:

```powershell
ollama pull gemma3:4b
uv run accessflow warmup --backend ollama
uv run accessflow replay scenarios/dev/text_correction.json --backend ollama
```

For Gemini, set `ACCESSFLOW_GEMINI_API_KEY` in your process environment through your normal
secret manager, then run `uv run accessflow warmup --backend gemini`. The code does not load
.env files automatically. Never paste keys into a shared prompt, commit or trace. Confirm
your account is on an acceptable free quota before opting in; code cannot guarantee the
billing configuration of an already configured key. No billing setup or paid fallback exists.
The selected model name is configurable using the variables in .env.example. Live access,
latency, quality and account quota were **not tested in the bootstrap**.

Request formats follow [Gemini generateContent](https://ai.google.dev/api/generate-content)
and [Ollama chat](https://docs.ollama.com/api/chat). Provider output is parsed as JSON and
validated against PlanProposal. Models propose actions; the controller validates and dispatches.

## Docker

```powershell
docker build -t accessflow .
docker run --rm accessflow
```

The image runs the offline text replay. It contains no downloaded ASR/LLM weights. Docker
was unavailable on Mridul's host during bootstrap; CI performs build/run verification.
Do not call Docker tested until the corresponding CI run succeeds.

## Official kit

`adapters/internal.py` parses our v0.1 envelopes. `official_adapter()` deliberately raises
NotImplementedError until the real organizer schema is supplied. A successful internal
replay is not official-kit compatibility. The controller defaults to 115 seconds, leaving
headroom below 120, and explicit model warm-up is bounded below 300 seconds. Real machine
timings remain to be measured. Cancellation of a Python task cannot forcibly terminate a
misbehaving native model; perception implementations must bound their worker lifetime.
