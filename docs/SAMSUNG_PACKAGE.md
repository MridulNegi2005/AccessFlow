# Samsung development package — 22 September 2026

Owner: Mridul. A local assembler now produces a self-contained package that passes
the supplied evaluator's import and contract smoke stages. This is preparation,
not a submission or release. The current package remains incomplete for Samsung
audio/vision evaluation and quota-constrained multi-step tasks.

## Build and install

From the project root, with the supplied kit extracted:

```powershell
uv run --offline --frozen python -m scripts.build_samsung_package --kit ../participant-kit/participant-kit --output artifacts/my-samsung-package --team AccessFlow --model qwen/qwen3.8-27b
uv venv --python 3.11 artifacts/my-package-env
uv pip install --index-url https://pypi.org/simple --python artifacts/my-package-env/Scripts/python.exe -r artifacts/my-samsung-package/requirements.txt
```

Use a new output directory each time. `AccessFlow` is the development package label;
confirm the actual registered team spelling before assembling a submission.
`--model` is explicit; the builder never reads `.env`, retrieves a key or selects
a fallback model. Package assembly itself makes no inference requests.

The assembler copies tracked Python implementation files, the package entry
template, the selected kit's evaluator/harness/docs/public scenarios/media, and
the lock/build inputs. It excludes `.env`, repository history, cached bytecode,
the kit's baseline agent, untracked source and unrelated files. Generated packages
live under ignored `artifacts/`; do not commit the copied organizer kit.

`requirements.txt` and `submission.yaml` contain the same21 exact public-PyPI pins
exported from `uv.lock`. Unsupported exports with local paths, URLs, editable
requirements, markers or duplicate names fail rather than producing broken YAML.
If the dependency profile later requires conditional packages, extend this logic
and test Samsung's minimal YAML parser before changing the lockfile.

Every packaged input has a SHA-256 in `package_manifest.json`, alongside the base
commit and dirty-worktree flag. The manifest does not hash itself. It describes the
actual working-tree bytes; it does not imply that a dirty source matches the base
commit. No output directory is overwritten or deleted.

## Configure and use the official commands

The generated entry point is `agent.agent:ParticipantAgent`, imported in-process
with the original two queues. It derives its media root from the package location
and explicitly loads `docs/TOOLS.md`. It never receives scenario dictionaries or
answer keys. The copied evaluator owns those inputs.

`runtime_profile.json` declares Groq, the selected model, the official API endpoint,
the selected prompt/read-answer modes (defaults full/prose), output cap950,
context-character cap32768, partial debounce1.0s, fast read retry and JSON-object
response mode. Conflicting existing environment
values cause an explicit error instead of silently changing the reported profile.

Supply `SECRET_GROQ_API_KEY` in the environment/portal. The entry maps this to the
existing provider adapter's key setting at setup. A local `ACCESSFLOW_GROQ_API_KEY`
is also accepted for development; if both exist with different values, setup fails.
Keys are not serialized into the profile or package. Constructor/import validation
requires no key and contacts no model; setup performs the existing bounded warm-up.

From the generated package directory, using its fresh environment:

```powershell
../my-package-env/Scripts/python.exe -c "import eval_submission as e; config, agent, errors = e.validate_submission('.'); assert not errors, errors; errors = e.contract_smoke_test(agent, 300); assert not errors, errors; print('Import and setup passed')"
../my-package-env/Scripts/python.exe run_local.py --scenario scenarios/pub_04_text_no_tool.json --agent agent.agent:ParticipantAgent --time-scale 1 --quiet --json public-check.json
../my-package-env/Scripts/python.exe eval_submission.py . --reps 3 --out official-check.json
```

The last command runs the entire official procedure and consumes hosted quota.
It has **not** been completed for this package. Do not change the official timing
scale, skip failed modalities, or describe a one-case result as the whole procedure.

## A startup incompatibility found and repaired

The supplied contract smoke test sends a partial user utterance without first
providing a tool manifest. The original adapter crashed with
`SamsungProtocolError: tool_manifest must be the first official event` even though
its import stage passed.

The runtime now buffers up to32 user/media/interruption/end events and64KiB of
serialized input while awaiting the real manifest. It does not send those events
to perception/planning, issue actions, or invent tools. After validating the
manifest, it delivers the session start then replays buffered inputs in order,
preserving speech timestamps and taking a copy of mutable incoming data.

Unknown event kinds and unsolicited tool results still fail. Overflow is an
explicit failure, not silent loss of user instructions. Cancellation releases
the pending input and managed tasks. The pure protocol translator still requires
the manifest first; only the runtime handles early arrival. No fake empty manifest,
fixture-name check or special case for the smoke test's utterance was introduced.

## Verified scope

- Eighteen package/profile/boundary tests and five startup tests added. Focused
  package/runtime/protocol suite36 passed; final full suite1070passed/1skip/1xfail,
  two dependency warnings,55.27s. Ruff clean. No B implementation or tests changed.
- Fresh Python3.11.15 environment on Mridul's Windows machine, with21 pins installed
  from public PyPI. The first offline install failed because required distributions
  were unavailable in the local cache; the explicit online install succeeded.
- The first assembled package passed official import validation but failed the
  startup smoke. The rebuilt package passed both stages with the live hosted
  backend, using only the portal-style secret and no preexisting profile variables.
- All25 inspected package/evaluator/AccessFlow module origins resolved inside the
  generated package, using the fresh interpreter in isolated mode. This excludes
  accidental success through the repository's editable installation.
- The rebuilt package ran the supplied `run_local.py` command on the public no-tool
  case:100.0, no tool calls, informational final at703ms. One exposed case, not the
  full suite, a median, or multimodal evidence.

Original reports, both package manifests, dependency versions, hashes and final
test XML are retained in `evidence/samsung-package-2026-09-22/`. An initial new
startup test omitted the manifest's required schema version and timed out; its
fixture was corrected, without relaxing production manifest validation.
The package and grounding evidence folders preserve raw bytes through Git instead
of normalizing their recorded line endings. All12 hashed artifacts were checked
against staged blobs and an exported checkout with Windows newline conversion enabled.

## Remaining ownership

Mridul: official full/repeated evaluation, quota and answer grounding, additional
packaging checks including Docker/Linux and remaining file-boundary review.
Two prompt-only attempts at missing-price-qualifier grounding failed and were
reverted; their evidence remains in `evidence/samsung-grounding-2026-09-22/`.

Both Mridul and Atishay must coordinate Samsung MP3 assembly, vision configuration
and endpoint/frame semantics. Atishay owns B perception/demo changes and recordings;
Mridul owns the Samsung boundary, dependencies, package profile and integration.
Neither should implement the other's files. Demo correlation and frame timing
reports remain open even though this full run passed. No release tag, workflow
change, registration, publishing of the generated kit or final submission occurred.

## Explicit candidate profiles — 24 September 2026

The builder now accepts `--prompt-profile compact-v2 --read-answer-mode evidence`
for an explicitly selected candidate. Both settings are serialized in the package
profile, validated against supported modes, and enforced before environment mutation.
An inherited conflicting read-answer mode now fails instead of silently changing
behavior. Defaults remain full/prose; this does not select the release configuration.

```powershell
uv run --offline --frozen python -m scripts.build_samsung_package --kit ../participant-kit/participant-kit --output artifacts/candidate-package --team AccessFlow --model qwen/qwen3.8-27b --prompt-profile compact-v2 --read-answer-mode evidence
```

Regenerate packages with the current builder; do not mix an old runtime_profile.json
with the new entry wrapper. Old self-contained packages retain their old wrapper and
are unchanged. Other multimodal/model installation and repeated-evaluation gates
remain open. Candidate creation is local, not publication or submission.
