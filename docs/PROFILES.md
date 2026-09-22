# Run profiles

A profile is the complete set of values that must reach the process for a scored run. The
CLI does not read `.env`. A file in the repository is not proof that its values are in the
environment. Set them in the shell, then verify.

Do not put a key in this file or in any committed file.

Each profile command below clears the settings of the other profiles first. Run the full
command for the profile you use. Do not mix commands from different profiles in one
session.

## Profile: hosted-qwen (primary)

| Setting | Value |
|---|---|
| Backend | `groq` |
| Model | `qwen/qwen3.8-27b` |
| Endpoint | `https://api.groq.com/openai/v1` |
| Response mode | `json_object`, with the generated schema in the prompt |
| Output cap | `ACCESSFLOW_MAX_OUTPUT_TOKENS=950` |
| HTTP request deadline | `--request-timeout 30` |
| Controller inference deadline | default (25 seconds) |

The output cap is required. Groq refuses each request at admission without it:

```
Request too large ... on output tokens per minute (OTPM): Limit 1000, Requested 1990
```

The adapter sends no `max_tokens` unless the cap is set, so the provider compares the
model's default ceiling against the per-minute output budget. The check applies to a single
request, so pacing does not avoid it.

These numbers come from measured runs on 15 September 2026. They are a starting
configuration, not a guarantee about future quota.

PowerShell, full command:

```powershell
Remove-Item Env:ACCESSFLOW_GROQ_API_KEY, Env:ACCESSFLOW_GROQ_MODEL, Env:ACCESSFLOW_GROQ_URL, `
  Env:ACCESSFLOW_MAX_OUTPUT_TOKENS, Env:ACCESSFLOW_OLLAMA_URL, Env:ACCESSFLOW_OLLAMA_NUM_GPU, `
  Env:ACCESSFLOW_OLLAMA_THINK -ErrorAction SilentlyContinue

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
| Backend | `groq` |
| Model | `openai/gpt-oss-120b` |
| Endpoint | `https://api.groq.com/openai/v1` |
| Output cap | not required |
| HTTP request deadline | `--request-timeout 30` |
| Controller inference deadline | default (25 seconds) |
| Limit | 8000 tokens per minute; pace one run per 95 seconds |

Use this profile when the primary model is refused or throttled. Select it explicitly. The
adapter has no automatic fallback and must not gain one.

The output cap is not required for this model. Clear it explicitly. A cap left over from
the primary profile still applies here and the exported evidence would then show a value
this profile does not promise.

PowerShell, full command:

```powershell
Remove-Item Env:ACCESSFLOW_GROQ_API_KEY, Env:ACCESSFLOW_GROQ_MODEL, Env:ACCESSFLOW_GROQ_URL, `
  Env:ACCESSFLOW_MAX_OUTPUT_TOKENS, Env:ACCESSFLOW_OLLAMA_URL, Env:ACCESSFLOW_OLLAMA_NUM_GPU, `
  Env:ACCESSFLOW_OLLAMA_THINK -ErrorAction SilentlyContinue

$env:ACCESSFLOW_GROQ_API_KEY = "<your key>"
$env:ACCESSFLOW_GROQ_MODEL   = "openai/gpt-oss-120b"
$env:ACCESSFLOW_GROQ_URL     = "https://api.groq.com/openai/v1"

.venv\Scripts\python.exe -m accessflow.cli replay scenarios\live_dev\support_then_service.json `
  --backend groq --request-timeout 30 --output artifacts\check.jsonl
```

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
| HTTP request deadline | `--request-timeout 30` |
| Controller inference deadline | default (25 seconds) |

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

PowerShell, full command (run after the server prints its URL):

```powershell
Remove-Item Env:ACCESSFLOW_GROQ_API_KEY, Env:ACCESSFLOW_GROQ_MODEL, Env:ACCESSFLOW_GROQ_URL, `
  Env:ACCESSFLOW_MAX_OUTPUT_TOKENS -ErrorAction SilentlyContinue

$env:ACCESSFLOW_OLLAMA_MODEL  = "qwen3:4b"
$env:ACCESSFLOW_OLLAMA_URL    = "<url the start script printed>"
$env:ACCESSFLOW_OLLAMA_THINK  = "0"
$env:ACCESSFLOW_OLLAMA_NUM_GPU = "37"

.venv\Scripts\python.exe -m accessflow.cli replay scenarios\live_dev\support_then_service.json `
  --backend ollama --request-timeout 30 --output artifacts\check.jsonl
```

## Two deadlines, not one

A run has two independent time limits. Both are correct at their documented values, and
one being shorter than the other is not an error:

- **HTTP request deadline.** How long the backend adapter waits for one model response.
  Set with `--request-timeout`. Exported as `reasoner_evidence.config.request_timeout_seconds`.
- **Controller inference deadline.** How long the controller waits for one planning step
  before it moves on. Set with `--inference-timeout`; defaults to 25 seconds when omitted.
  Exported as `run_metadata.config.inference_timeout_s`.

The controller inference deadline can be shorter than the HTTP request deadline on
purpose: the controller gives up on a slow planning step before the HTTP client would time
out, so a stalled step does not stall the whole session. Do not treat that difference as a
misconfiguration when you read these two values back.

## Verify the profile reached the process

Run in a shell with no inherited project variables. The run metadata records what was
actually used. `load_run_metadata` reads the one `run_metadata` row from the trace file
(that row is written first, not last) and `validate_reasoner_evidence` checks it against
the schema this document promises, instead of a person having to notice a missing key by
eye:

```powershell
.venv\Scripts\python.exe -c "from accessflow.evaluation.replay import load_run_metadata; from accessflow.adapters.models import validate_reasoner_evidence; m = load_run_metadata('artifacts/check.jsonl'); e = validate_reasoner_evidence(m['reasoner_evidence']); print(e['backend'], e['model'], e['config']['endpoint'], e['config']['max_output_tokens'], e['config']['request_timeout_seconds']); print('controller_inference_timeout_s', m['config']['inference_timeout_s'])"
```

Check the model id, the output cap, the endpoint and both deadlines against the profile
table above. `validate_reasoner_evidence` raises a specific error instead of a bare
`KeyError` when a value is missing:

- `reasoner_evidence is null` means the run used no model backend at all (for example
  `--backend offline-fake`). No profile reached the process.
- A schema error names the missing or malformed field directly, for example a missing
  `endpoint`.

The endpoint value has credentials and query-string secrets removed before export. It
matches the profile table's endpoint plus the request path (`/chat/completions` or
`/api/chat`), never a bare host with no path.

### Older traces

A trace recorded before a config value was exported does not carry that value. No trace
in `artifacts/` from 15 September 2026 or earlier carries `endpoint`, and most do not
carry `max_output_tokens`. The strict check above names the absent fields and stops.

To read such a trace, verify the remaining values and report each absent field as
unverified:

```powershell
.venv\Scripts\python.exe -c "from accessflow.evaluation.replay import load_run_metadata; from accessflow.adapters.models import validate_reasoner_evidence, missing_promised_config; m = load_run_metadata('artifacts/check.jsonl'); e = validate_reasoner_evidence(m['reasoner_evidence'], strict=False); print(e['backend'], e['model'], e['config'].get('request_timeout_seconds')); print('unverified:', missing_promised_config(e))"
```

An absent field is not evidence that a particular value was used. Do not substitute a
default and do not report a profile as confirmed for that run. Make a new run to verify
the endpoint and the output cap.


## Samsung documented text profile — measured 22 September 2026

For the recorded live Qwen chain, explicitly set `ACCESSFLOW_SAMSUNG_BACKEND=groq`,
`ACCESSFLOW_MAX_OUTPUT_TOKENS=950`, `ACCESSFLOW_MAX_CONTEXT_CHARS=32768`, and
`ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S=1.0`; supply the chosen key/model/URL locally.
Use `python -m scripts.run_samsung_check --kit ../participant-kit/participant-kit
--tool-documentation docs/TOOLS.md --scenario pub_03_text_chained_booking.json
--output artifacts/samsung/a-new-report.json` on one line.

Context characters default14000, with an explicit permitted range1024–65536;
Ollama's 4096-token profile refuses limits above14000. Partial debounce defaults
0.08s, accepts finite0–5s, and affects speculative incomplete-speech planning,
not completed requests. The document option may also be set through
`ACCESSFLOW_SAMSUNG_TOOL_DOCUMENTATION`. It must name one UTF-8 Markdown file
under kit/docs, at most32768bytes. No document discovery or links are followed.
Return examples remain untrusted interface evidence, not live results or permission.

Full/selected document hashes and line provenance, actual context cap and partial
debounce are recorded. The exposed case completed once; no repeated reliability
claim. A previous attempt hit HTTP429 at the observed7000 input-token/minute quota.
Run serially with quota recovery; no automatic paid fallback. The environment
variables above were scoped to test child processes, not persisted into .env.


## Samsung transient-read retry — 22 September follow-up

`ACCESSFLOW_SAMSUNG_FAST_READ_RETRY` accepts only `1` (default Samsung factory)
or `0` (model-directed control). It enables one exact current transient-read
retry without inference. Generic Agent defaults remain unchanged (opt-in).
The runner records the actual agent flag and execution ledger with operation IDs
and `retry_of_call_id`. No additional official action fields are required.

Measured pub_08 with the documented hosted profile: 100.0 with retry enabled,
81.5 in the matched configuration control. The control's final request hit rate
limit; do not characterize the difference as solely a tail/latency improvement.
See `docs/evidence/samsung-retry-2026-09-22/README.md` for all evidence and limits.


## Experimental compact planner profile — 22 September 2026

Set `ACCESSFLOW_SAMSUNG_PROMPT_PROFILE=compact-v1` explicitly to test condensed
instructions and annotation-free output-schema presentation. Default is `full`;
unknown values fail setup. Full local output validation and controller checks stay
unchanged. Session, manifests and evidence are not truncated. Model evidence now
includes actual `prompt_profile` and up to128 size/hash measurements for initiated
plans. These exclude warm-up and do not establish provider delivery by themselves.
The first compact public attempt used fewer tokens but failed validation and later
hit quota, so it is not adopted as the default. See the retained report in
`docs/evidence/samsung-compact-2026-09-22/README.md`.
