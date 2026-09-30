# Legacy queue-package hosting

This guide supports the older queue-based development kit and the package builder.
The current submission interface is FDB-v3 over LiveKit; use
[FDB reproduction](FDB_REPRODUCTION.md) for that evaluation.

## Assemble the development package

```powershell
uv run --frozen python -m scripts.build_samsung_package --kit C:\path\to\queue-kit --output artifacts\queue-package --team AccessFlow --model qwen/qwen3.8-27b
```

The package copies declared source, locked requirements and selected kit files,
excludes credentials and caches, and records input hashes. Use a new output directory.
The kit must supply `harness/runner.py`, `harness/scorer.py` and `docs/TOOLS.md`.
This does not establish compatibility with the current LiveKit benchmark.

## Container

From the generated package directory, with Docker installed:

```sh
docker build --platform linux/amd64 -t accessflow-eval .
docker run --name accessflow-evaluation --env SECRET_GROQ_API_KEY accessflow-eval
docker cp accessflow-evaluation:/results/results.json ./results.json
```

Supply credentials through the existing host environment; never bake keys into an
image. Keep failed results in the record. Corrected Docker/Linux execution is not
verified in the current environment. The repository-root Dockerfile is an offline
text-regression image, not a full voice-evaluation container.

## Optional local vision service

A generated package may contain `hosting/start_vision_server.py`. It launches an
already-installed declared local Ollama service; it downloads no model. Its profile
must specify a loopback endpoint and installed model. Version, model identity and
startup/cleanup are checked separately from inference quality. Use the command's
`--help` for its required executable, model-store, version, digest and log arguments.

The active FDB voice runtime uses hosted speech/planning services and does not need
this legacy local-vision path.
