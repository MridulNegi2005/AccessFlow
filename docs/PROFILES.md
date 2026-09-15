# Run profiles

A profile is the complete set of values that must reach the process for a scored run. The
CLI does not read `.env`. A file in the repository is not proof that its values are in the
environment. Set them in the shell, then verify.

Do not put a key in this file or in any committed file.

## Profile: hosted-qwen (primary)

| Setting | Value |
|---|---|
| Backend | `groq` |
| Model | `qwen/qwen3.8-27b` |
| Endpoint | `https://api.groq.com/openai/v1` |
| Response mode | `json_object`, with the generated schema in the prompt |
| Output cap | `ACCESSFLOW_MAX_OUTPUT_TOKENS=950` |
| HTTP request deadline | `--request-timeout 30` |
| Controller inference deadline | default |

The output cap is required. Groq refuses each request at admission without it:

```
Request too large ... on output tokens per minute (OTPM): Limit 1000, Requested 1990
```

The adapter sends no `max_tokens` unless the cap is set, so the provider compares the
model's default ceiling against the per-minute output budget. The check applies to a single
request, so pacing does not avoid it.

These numbers come from measured runs on 15 September 2026. They are a starting
configuration, not a guarantee about future quota.

PowerShell:

```powershell
$env:ACCESSFLOW_GROQ_API_KEY = "<your key>"
$env:ACCESSFLOW_GROQ_MODEL   = "qwen/qwen3.8-27b"
$env:ACCESSFLOW_GROQ_URL     = "https://api.groq.com/openai/v1"
$env:ACCESSFLOW_MAX_OUTPUT_TOKENS = "950"
.venv\Scripts\python.exe -m accessflow.cli replay scenarios\live_dev\support_then_service.json `
  --backend groq --request-timeout 30 --output artifacts\check.jsonl
```

Pace one scenario per 70 to 95 seconds. One run of a three-turn fixture needs about 9500
input tokens.

## Profile: hosted-gptoss (fallback)

| Setting | Value |
|---|---|
| Model | `openai/gpt-oss-120b` |
| Output cap | not required |
| Limit | 8000 tokens per minute; pace one run per 95 seconds |

Use this profile when the primary model is refused or throttled. Select it explicitly. The
adapter has no automatic fallback and must not gain one.

## Profile: local-qwen3-4b

| Setting | Value |
|---|---|
| Backend | `ollama` |
| Model | `qwen3:4b` |
| Endpoint | the port printed by the start script, not the default 11434 |
| Think blocks | `ACCESSFLOW_OLLAMA_THINK=0` |
| Layer placement | `ACCESSFLOW_OLLAMA_NUM_GPU=37` |
| Server flags | `-FlashAttention 1 -KvCacheType q8_0` |
| Context length | 4096 |

Start the server first:

```powershell
.\scripts\start-local-ollama.ps1 -FlashAttention 1 -KvCacheType q8_0
```

The script prints a JSON block with the URL. Use that URL. The project server runs on its
own port and does not replace a user's default Ollama installation.

Pin the layer count for this model only. Automatic fitting is not dependable on a 4096 MiB
card: Ollama holds a 1024 MiB free-memory reserve and drops to 29 of 37 layers when full
offload does not clear it. Confirm the placement in the server log before you record a
score:

```
load_tensors: offloaded 37/37 layers to GPU
```

Do not pin this value for another model. A pinned count is correct for exactly one model,
and a stale pin once made `qwen2.5:7b` request more memory than the card has.

`qwen3:4b` passes the single-turn fixtures. It does not complete the three-turn fixtures.

## Verify the profile reached the process

Run in a shell with no inherited project variables. The run metadata records what was
actually used:

```powershell
.venv\Scripts\python.exe -c "import json; m=[json.loads(l) for l in open('artifacts/check.jsonl',encoding='utf-8')][-1]; e=m['reasoner_evidence']; print(e['backend'], e['model'], e['config'])"
```

Check the model id, the output cap, the endpoint and the deadline. If any value is missing,
the profile did not reach the process.
