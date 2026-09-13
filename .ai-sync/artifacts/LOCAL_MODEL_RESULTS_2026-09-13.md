# First local reasoning measurements

These measurements used actual Ollama 0.34.0 / gemma3:4b Q4_K_M on Mridul's
i5-10300H, about 16 GiB RAM and GTX 1650 4 GiB. Tools were in-memory mocks and
inputs were developer-authored text, not held-out examples or participant recordings.

Model digest: `a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a`.
Configuration: 4096-token context, temperature 0, one model/request worker. HTTP
request timeout 20 seconds; controller inference timeout 25 seconds. No hosted fallback.
Models were unloaded before and after each pilot, with unloaded state verified.

| Check | Source commit | Readiness | Plan request | Task outcome |
|---|---|---:|---:|---|
| First cold API setup probe | Direct HTTP, independent of application source | 144.93 s | Not a task | Valid ready=true only |
| Original correction pilot | 6099497, clean | 18.32 s | 8.23 s | 30 s timeout, zero effects; unresolved completion |
| Required-field schema pilot | cc70cae, clean | 17.61 s | 19.72 s | 30 s timeout, missing_dependency, zero effects |

Both task pilots failed. Neither is a successful completion or an official score.
The first application plan passed structural validation but left the corrected request
unresolved. The next version required explicit generation fields and attempted a call,
which the unchanged engine rejected for a missing slot dependency. Generation telemetry
success means valid JSON/PlanProposal, not correct reasoning or successful execution.
These first traces did not record the raw proposal, so further diagnostics are required
before attributing every omitted or incorrect field to a specific model decision.

The original fixture also expected exact 24-hour time without specifying its format in
the tool schema. Separate `scenarios/live_dev` variants make that requirement explicit,
allow 100 seconds for multi-step reasoning, and correctly distinguish a new correction
utterance from an ASR hypothesis replacement. Those variants are development tuning,
not a like-for-like improvement claim or additional independent benchmark cases.

Cold setup memory pressure was high: initially about 1.85 GiB RAM free, falling below
0.5 GiB during the first load. The initial cold response included 89.10 seconds of load
and 55.07 seconds of prompt processing. Subsequent faster loads do not erase that result;
file-system caching and changing machine load were not controlled. No peak-memory or
latency distribution is established by these few probes.

Evidence is in [local-model-2026-09-13](local-model-2026-09-13/): hardware, cold readiness,
both full reports and both raw traces. Reports retain original output paths; the matching
trace files were copied alongside them under descriptive names. Commit/source/scenario
hashes remain unchanged. Setup instructions are in [LOCAL_MODELS.md](../LOCAL_MODELS.md).

Next: record typed proposals, fix demonstrated interpretation errors without weakening
execution guards, and run all four live development variants. Real vision, full scenario
coverage, independent held-out tests and baseline comparisons remain outstanding.

## Grounded schema, automatic GPU placement: 79bd263

All four live-development variants failed on clean source 79bd263. Device correction and
lost-response reconciliation reached the 20-second HTTP timeout, before any effect.
Support and text-correction plans returned structurally valid JSON in 18.97 and 19.74
seconds, but neither completed within its 100-second scenario wait. All model resets
and cleanup checks succeeded. Evidence: `grounded-auto-report.json` and four matching
`grounded-auto-case-*.jsonl` files in the evidence directory above.

The recorded support plan nested its values under a `slots` key and included a schema
keyword in actual tool arguments. The correction plan supplied `05:00 PM` instead of
the manifest's required HH:MM and left request_complete false while proposing a write
and a premature success message. The controller dispatched no effect and did not expose
that false success claim as a final answer. Correctness safeguards worked, but task
completion was 0/4. A model JSON success must not be counted as a task success.

Next experiment: explicit GPU layer placement with identical planner instructions and
timeouts, to distinguish hardware limits from these reasoning errors. The opt-in
ACCESSFLOW_OLLAMA_NUM_GPU setting is recorded in request evidence; unset retains auto.

## Explicit 35-layer placement: df89d01

Same live text-correction fixture and planner prompt, on clean df89d01, with only the
placement option changed: warm-up 12.68 seconds and plan request 11.11 seconds.
Ollama reported all 2,875,520,450 loaded-model bytes in VRAM after warm-up. A sampled
GPU reading during the request showed 3711 MiB used and 225 MiB free. That is a sample,
not a measured peak or a guarantee that other applications can run comfortably alongside it.

The task still failed. It proposed 05:00 for the user's 5 PM, left request_complete false,
and included a premature success message. No tool effect or final success was emitted.
The case timed out after its 100-second task wait; cleanup confirmed the model unloaded.
Evidence: `gpu35-report.json` and `gpu35-trace.jsonl` alongside the previous results.

The roughly 20-to-11-second request change is one development comparison, with different
generated token counts (108 versus 97) and uncontrolled machine/file-cache load. It is
not a latency distribution or an isolated measurement of GPU acceleration. It does show
that runtime optimization alone did not repair the reasoning errors. Request and controller
timeouts remained 20 and 25 seconds; they were not extended to obtain this result.

Next: clarify and test request-understanding versus action-completion semantics and flat
slot/argument data, then compare another explicitly selected local instruction model if
Gemma remains inaccurate. Keep the failed runs and evaluate unfamiliar wording/manifests
before claiming improvement. The project server was explicitly stopped after this run.
