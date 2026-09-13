# Local model setup and measurements

Mridul's runtime is portable at `D:\AccessFlow-LocalRuntime`. The repository and Python
environment stay in their existing location. Setup inspection found only 1.2 GiB free on
C:, so the archive, extracted runtime and model cache were placed on D:. These are local
installation assets and are not committed to Git.

## Reproduce the runtime

Download the official [Ollama Windows archive](https://github.com/ollama/ollama/releases/download/v0.34.0/ollama-windows-amd64.zip)
and check SHA-256 before extraction:

```text
a7dd1b174f39d3d1b8a25d4cbc86045d0e190b17187bfdcbe2f2ee3b5a11470e
```

Extract into `D:\AccessFlow-LocalRuntime\ollama-v0.34.0`. The verified executable was
signed by Ollama Inc. The standalone distribution is documented in
[Ollama's Windows guide](https://docs.ollama.com/windows).

```powershell
.\scripts\start-local-ollama.ps1
$env:OLLAMA_HOST='127.0.0.1:11435'
& 'D:\AccessFlow-LocalRuntime\ollama-v0.34.0\ollama.exe' pull gemma3:4b
```

The launcher binds loopback port 11435, puts model files in the runtime's models directory,
disables cloud features, and permits one loaded model and one parallel inference request.
It starts a hidden process and records its PID, executable, start time and log paths under
the runtime directory. It creates no recurring task or startup registration. Model location,
cloud-disable and concurrency settings follow the [official FAQ](https://docs.ollama.com/faq).

## Explicit model checks

```powershell
uv run --extra dev python scripts/run_local_model_checks.py
```

This uses the four `scenarios/live_dev` variants with actual Ollama reasoning, text perception and
mock external tools. Before and after each case, it unloads the selected model on the
experiment's dedicated server and checks that it is absent from the loaded-model list.
Each case starts with a constant readiness warm-up; it receives no prior conversation.
These variants allow 100 seconds for task completion; HTTP (20 seconds) and controller
inference (25 seconds) bounds remain in force. There is no paid,
hosted or model fallback. Do not use this runner against a server shared with another task.

Use an empty output directory for each run; an existing nonempty directory is refused.
The output directory contains per-case traces and a report with model digest, server
version, setup timing, criteria, cleanup status and safe model-request telemetry. A partial
run exposes finished_count and not_run_count separately from the total case count. Missing or failed cases
are not successful benchmark examples. Cleanup failure stops further cases. Unexpected
loaded models are rejected without unloading them. Use only the project-owned server;
the Python runner validates loopback and model state, not OS-level endpoint ownership.
The launcher and stop script verify the port's owning process on Windows.

Typed generated plans are included for debugging these synthetic development inputs;
normal backend telemetry remains content-free. Setup and cooperative cancellation are
recorded with safe failure phases. Forced process termination can still interrupt a file
write; inspect the manifest and finished counts before using any report.
This is not held-out or official-kit evaluation.

The generation schema now requires explicit action/completion decisions and is included
in the prompt as well as Ollama's format field, following the
[structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs).
Slot-dependency descriptions guide the model; execution guards still enforce validity.

To stop the dedicated server after testing:

```powershell
.\scripts\stop-local-ollama.ps1
```

The stop script checks both PID start time and executable before unloading models and
stopping the process. A reused PID is not treated as authorization to stop another app.

## Measurement status

Runtime 0.34.0 and gemma3:4b were downloaded and verified. A direct cold API readiness
probe returned `{"ready": true}` in 144.93 seconds (89.10 seconds server-reported load,
55.07 seconds prompt processing). This was a setup diagnostic, not a task-completion
evaluation. The model was only partially placed on the GPU and available RAM fell below
0.5 GiB during that probe. The first two model-backed pilots failed; see the
[preserved results](results/LOCAL_MODEL_2026-09-13.md). Further measurements are in progress.
Current hardware: i5-10300H, about 16 GiB RAM and GTX 1650 4 GiB.
