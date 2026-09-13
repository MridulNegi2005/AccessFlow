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
