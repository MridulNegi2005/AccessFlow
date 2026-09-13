# Local lightweight model trials, 14 September 2026

Repeated trials on `scenarios/live_dev`. Mock tools, developer-authored criteria.
Not the held-out set and not an official score.

Hardware: GTX 1650, 4096 MiB VRAM, 15.8 GiB system RAM. Ollama 0.34.0 on D:.

## Two configuration defects found first

Both produced results that looked like model failures and were not.

**1. Forced GPU placement on qwen2.5:7b.** The server log records:

```
common_fit_params: failed to fit params to free device memory:
                   n_gpu_layers already set by user to 99, abort
load_tensors: offloaded 29/29 layers to GPU
load_tensors: CUDA0 model buffer size = 4168.09 MiB
```

The card has 4096 MiB. A leftover `num_gpu` setting from the earlier gemma3 placement
experiment overrode automatic fitting, so the model was forced entirely onto the GPU,
failed to fit and spilled into shared system memory. The 13 September qwen2.5:7b result
of 2/4 at a 26.54 s mean was measured in that state and is not a clean measurement.

**2. Reasoning models emit a think block.** qwen3:4b scored 0/4 with **zero successful
requests**; all four scenarios ended in `ReadTimeout` at 90.1 s. The think block alone
exceeded the deadline. Setting `ACCESSFLOW_OLLAMA_THINK=0` changed the same model on the
same fixtures from 0/4 to 3/4.

Any local run must record its offload line and its think setting next to its score.

## qwen3:4b, three trials

2.5 GB, 26/37 layers on GPU, thinking disabled, 90 s request and 95 s inference deadlines.

| Scenario | t2 | t3 | t4 | Verdict |
|---|---|---|---|---|
| development-text-correction-01 | pass | pass | pass | stable |
| device-correction-before-plan | pass | pass | pass | stable |
| lost-response-status-reconciliation | pass | fail | fail | timing-marginal |
| support-read-then-service | fail | fail | fail | never passes |
| **Total** | **3/4** | **2/4** | **2/4** | |

Successful request times ranged from 14.7 s to 40.1 s. The same scenario passed in one
trial and timed out in the next on identical settings.

## support-read-then-service

This case needs four slots and a two-step read-then-write chain. It is the heaviest of
the four and no local model has passed it.

A diagnostic copy at the maximum legal 110 s completion timeout still failed. Two model
requests succeeded, at 19.4 s and 26.8 s, and the plans set no slots at all: `device`,
`day` and `hour` were all absent. The failure is planning quality, not elapsed time.

| Model | Size | Result on this case |
|---|---|---|
| gemma3:4b | 3.3 GB | fail |
| qwen2.5:3b | 1.9 GB | fail, omits slots |
| qwen2.5:7b | 4.7 GB | fail, measured while spilling |
| qwen3:4b | 2.5 GB | fail, omits slots, three trials |
| qwen3.8-27b hosted | n/a | **pass** |

## Conclusions

1. qwen3:4b is the best local model tested. At 2.5 GB it matches or beats qwen2.5:7b
   while fitting the card far better.
2. Local small models are not merely less accurate on this hardware. At 14 s to 40 s per
   request, with two or three requests per scenario against a 95 s budget, they are
   **non-deterministic against the official 120-second cap**. The same configuration
   scored 3/4, 2/4 and 2/4.
3. The four-slot two-step chain is a capacity wall. Every model at or below 7 B omits the
   slot updates its own dependencies reference.
4. Gemma 4 has no small variant. The smallest tags are 12b at 7.6 GB, then 26b and 31b.
   All exceed 4 GB VRAM by a wide margin, so a local Gemma 4 trial would measure the
   hardware rather than the model.

## Next

Test `google/gemma-4-31b-it` through the NVIDIA NIM backend rather than locally. The
adapter is registered; the run needs `ACCESSFLOW_NVIDIA_API_KEY`.

Traces: `artifacts/qwen3-4b-t1` through `artifacts/qwen3-4b-t4`, and
`artifacts/qwen3-4b-slowdiag.jsonl` for the 110-second diagnostic.
