# Local inference tuning, 14 September 2026

Hardware: NVIDIA GTX 1650, 4096 MiB VRAM, 3801 MiB free, compute capability 7.5, driver
610.88. Ollama 0.34.0 portable on D:, bundled CUDA 12 and 13 runtimes. Model `qwen3:4b`,
2.5 GB, 37 layers, thinking disabled.

## What was already configured

`scripts/start-local-ollama.ps1` set `OLLAMA_NUM_PARALLEL=1`,
`OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=4096`, `OLLAMA_KEEP_ALIVE=5m`,
`OLLAMA_NO_CLOUD=1`, and a model directory on D:. Flash attention and KV cache type were
never set, so Ollama used `flash_attn=auto` and an f16 KV cache.

## The measured bottleneck

Baseline, from 12 successful requests in the untuned runs:

| Phase | Rate | Tokens | Time |
|---|---|---|---|
| Prompt evaluation | 2727 tok/s | 1462 | 0.5 s |
| **Generation** | **7.9 tok/s** | 162 | **20.5 s** |
| Total per request | | | 25.2 s |

Generation was 80 percent of wall time. The cause was visible in the server log:

```
load_tensors: offloaded 26/37 layers to GPU
load_tensors:    CUDA0 model buffer size = 1745.66 MiB
load_tensors:  CUDA_Host model buffer size = 934.54 MiB
llama_kv_cache:  CUDA0 KV buffer size = 400.00 MiB
llama_kv_cache:    CPU KV buffer size = 176.00 MiB
```

GPU use was about 2237 MiB of 3801 MiB free. Roughly 1560 MiB of VRAM sat idle while 11 of
37 layers ran on the CPU. Every generated token crossed that boundary.

## The change

`scripts/start-local-ollama.ps1` now accepts `-FlashAttention`, `-KvCacheType` and
`-ContextLength`, and records all three in `ollama-server.json`. Defaults preserve the
previous behaviour.

Run with:

```
scripts/start-local-ollama.ps1 -FlashAttention 1 -KvCacheType q8_0
```

Flash attention is required for a quantized KV cache. Together they reduce the KV cache
from 576 MiB across both devices to 306 MiB on the GPU, which frees enough VRAM for every
layer:

```
llama_context: flash_attn = enabled
load_tensors: offloaded 37/37 layers to GPU
load_tensors:    CUDA0 model buffer size = 2375.91 MiB
llama_kv_cache:  CUDA0 KV buffer size = 306.00 MiB
```

## Result

Warm measurements, 12 successful requests across two suite runs.

| Measure | Before | After | Change |
|---|---|---|---|
| Generation | 7.9 tok/s | **38.1 tok/s** | 4.8 times faster |
| Total per request | 25.2 s | **8.6 s** | 2.9 times faster |
| Slowest request | 41 s | **14.1 s** | |
| Scenario runtime | 16 s to 59 s | **4 s to 17 s** | |
| Suite score | 3/4, 4/4 | 3/4, **4/4** | unchanged |

The single failure was `lost-response-status-reconciliation` rejecting a reconciliation plan
for `missing_dependency`. The status tool's `receipt` parameter carries the controller's
operation id, which is not a slot, so listing it as a dependency fails. That case passed in
the other run and in three of four earlier untuned runs. It is plan variance on a known
contract edge, not a tuning regression.

## Do not pin num_gpu

An earlier session left `num_gpu` at 99, which forced `qwen2.5:7b` to request a 4168 MiB
buffer on a 4096 MiB card and spill into shared memory. The tuned run was first verified
with an explicit `ACCESSFLOW_OLLAMA_NUM_GPU=37`, then repeated with it unset.

With flash attention and a q8_0 KV cache, Ollama's own fitting selects 37/37 layers and
reaches 37.3 tok/s, matching the pinned result. Leave `num_gpu` unset: automatic fitting
adapts to each model, while a pinned layer count is correct for exactly one.

## Remaining headroom

Generation still dominates at roughly 4.5 s for 170 output tokens. Prompt evaluation is
1.45 s for 1462 tokens at about 1006 tok/s. Further gains would come from reducing output
tokens, which means changing the proposal schema, rather than from more runtime tuning.
The 781-token system prompt is 54 percent of the input but only about 0.8 s of the request.

Traces: `artifacts/qwen3-tuned-1.jsonl`, `artifacts/qwen3-tuned-suite`,
`artifacts/qwen3-tuned-suite2`, `artifacts/qwen3-autofit.jsonl`.
