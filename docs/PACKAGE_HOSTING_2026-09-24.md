# Package hosting and container path - 24 September 2026

## Scope and readiness

Generated Samsung packages now contain a Dockerfile for the actual official evaluator
and a portable Python launcher for an already-installed local vision service. The
repository-root Dockerfile remains an explicitly labeled offline regression image.
Do not present its fake text replay as a submission or media check.

The package recipe and process lifecycle are tested, including a real Windows Ollama
startup/identity/shutdown check. **Docker/Linux execution remains unverified:** Docker
and Podman are unavailable here, and WSL has no installed distribution. The container
recipe is not a passed clean-install gate. Vision's previously measured23.688s latency
and actual microphone testing remain open. No B-owned source or tests were modified.

## Measured checkpoint

Final full suite:1344 passed,2 skipped,1 existing xfailed in79.52s;Ruff clean.
Earlier focused package/hosting checks passed101 cases. The two original non-loopback
configuration failures are retained as reproductions,not passing results.

Actual installed service startup verified version/model identity in6.016s and stopped
its own PID on port11436. A95-file native vision candidate then verified every hash
and37 installed pins in the existing isolated Windows venv. Its packaged launcher
started the declared service in6.125s;actual agent setup warmed faster-whisper CPU INT8,
gemma3:4b vision and hosted qwen/qwen3.8-27b successfully in47.906s. The test service
was stopped afterward;the existing port11435 service remained. No new official task
score,accuracy improvement or Docker success is implied. The tested candidate used
an explicit110s perception timeout;this does not fix the previously measured slow vision.

Live measurements predate only the final invalid-port/empty-userinfo rejection,which
leaves the tested valid profile unchanged. Evidence retains the candidate's exact
hashes separately from final source hashes. See docs/evidence/package-hosting-2026-09-24
in the repository for reports,recipe,profile,reproduction helper and final tests.

## Generated package container

Build the package with scripts/build_samsung_package.py as described in
docs/NATIVE_PACKAGE_2026-09-24.md. Use the generated package directory as build context,
not the repository root. ASR assets are included only when explicitly requested; vision
requires an external declared local model installation and service.

From that package directory, with Docker installed:

```sh
docker build --platform linux/amd64 -t accessflow-eval .
docker run --name accessflow-evaluation --env SECRET_GROQ_API_KEY accessflow-eval
docker cp accessflow-evaluation:/results/results.json ./results.json
```

Supply the existing SECRET_GROQ_API_KEY environment variable through your terminal's
credential handling first; never bake a key into an image/build argument. Docker's
`--env NAME` passes the host's existing value. The container defaults to the official
evaluator, three repetitions and its normal timing. These runs consume hosted quota;
do not mistake a rate-limit failure for a passing run. Retain the container until the
result is copied. [Docker runtime/environment documentation](https://docs.docker.com/engine/containers/run/).

The recipe installs exact locked Python requirements from binary wheels, installs
libgomp1, copies only declared package areas, runs as UID10001 and writes results to
/results. Optional assets have a placeholder so text packages can build too. The
deny-by-default context excludes credentials/caches while retaining required ASR
tokenizer.json. The base Python3.11 Debian image and apt snapshot are not digest-pinned;
capture the actual image digest and installed OS packages when validating the target.

## Vision installation and startup

The hosting script downloads nothing. Install the declared Ollama version and the
explicit model/checkpoint before evaluation, using official distributions. Record the
binary origin/hash and installed model digest. This machine's existing installation
is Ollama0.34.0 and gemma3:4b Q4_K_M with model digest:

```text
a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a
```

This identifies the measured installation, not permission to silently substitute
a different checkpoint or claim it is fast enough. Public origin and installation
instructions: [Ollama](https://github.com/ollama/ollama),
[configuration reference](https://github.com/ollama/ollama/blob/main/docs/faq.mdx).

Use a generated package with explicit Ollama vision settings. Its runtime_profile.json
must name the model and an HTTP IPv4 loopback URL with a port (e.g.127.0.0.1:11435).
The launcher freezes cloud-disabled mode, one loaded model/one parallel request,
4096 context, flash attention and q8_0 KV cache. It does not inherit arbitrary
OLLAMA_* tuning or provider credentials from the calling environment.

From the generated package, replace the three local installation/log paths:

```sh
python hosting/start_vision_server.py --profile runtime_profile.json --executable <installed-ollama-executable> --models-dir <installed-model-store> --log <new-log-file> --expected-version 0.34.0 --expected-model-digest a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a --check-only
```

Check-only starts a fresh service, checks exact API version/model digest, then stops
that child. It does **not** warm inference or certify speed. For evaluation, omit
--check-only and leave the launcher running in one terminal. Start the evaluator in
another. Ctrl+C stops the launcher's child. Existing ports/logs are refused; no other
service is reused, killed or reconfigured. Abrupt OS/process termination is not a
graceful cleanup guarantee. Inference subprocess teardown after forced termination
has not been verified by the startup-only live check.

An existing service can still be managed separately; the agent only consumes its
explicit loopback URL. Actual model inference remains in setup/perception, with no
scenario annotations available during startup. B owns provider/worker changes.

For a **Linux Docker Engine host** running the vision launcher on its loopback, use:

```sh
docker run --name accessflow-vision-evaluation --network host --env SECRET_GROQ_API_KEY accessflow-eval
```

The image profile and host service must use the same loopback port/model. Host networking
shares the host network namespace; a regular bridge container's localhost would refer
to itself. This is a Linux deployment instruction, not a verified Docker Desktop recipe.
Do not change the current B provider to accept a remote host to work around that mismatch.
[Docker host-network documentation](https://docs.docker.com/engine/network/drivers/host/).

## Acceptance and ownership

Mridul owns package generation, settings validation, launcher and container checks.
Atishay owns vision inference speed/options, audio endpointing, microphone and browser
adoption. Both agree any new optional worker arguments before A packages them.

Before calling the code submission-ready, execute the built container on the declared
platform; verify native imports/setup/media/cleanup, supply the actual vision service,
and retain official repeated-run results and failures. A script or green mocked suite
alone does not close those gates. PPT/video/form/tag work is excluded from this checkpoint.
