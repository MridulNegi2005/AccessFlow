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

This uses the four development fixtures with actual Ollama reasoning, text perception and
mock external tools. Before and after each case, it unloads the selected model on the
experiment's dedicated server and checks that it is absent from the loaded-model list.
Each case starts with a constant readiness warm-up; it receives no prior conversation.
The normal replay timeout and controller safeguards remain in force. There is no paid,
hosted or model fallback. Do not use this runner against a server shared with another task.

The output directory contains per-case traces and a report with model digest, server
version, setup timing, criteria, cleanup status and safe model-request telemetry. A partial
run exposes finished_count separately from the total case count. Missing or failed cases
are not successful benchmark examples. This is not held-out or official-kit evaluation.

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
0.5 GiB during that probe. Full model-backed task measurements remain in progress.
Current hardware: i5-10300H, about 16 GiB RAM and GTX 1650 4 GiB.
