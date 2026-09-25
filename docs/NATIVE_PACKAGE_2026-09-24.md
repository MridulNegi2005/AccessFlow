# Native installation package — 24 September 2026

Later24September update: actual Samsung MP3 admission and isolated native audio runs
are now implemented. See [audio admission](SAMSUNG_AUDIO_ADMISSION_2026-09-24.md)
and [remaining media coordination](MEDIA_COMPLETION_COORDINATION_2026-09-24.md).
The checkpoint details below retain their original test counts and limitations.

## What is now available

The A-owned builder can include a pinned, hash-checked Faster Whisper installation,
an explicitly selected installation WAV and optional vision configuration/PNG.
The common runtime warms those assets and fails clearly when they are unavailable.
This supersedes the previous checkpoint's text-only builder limitation.

Text packaging remains the default. Native mode adds the locked audio dependencies;
there is no model download or implicit backend switch during evaluation. Vision
weights/server are **not** included: an explicitly configured Ollama service is
still required when enabling vision. Official MP3 assembly is still outstanding.
Do not call this package complete for all Samsung modalities yet.

## Reproduce installation

Run from the repository root in PowerShell. These commands use public model files,
do not train/fine-tune anything, and do not publish a package. The installed base.en
snapshot is the same revision already documented in Atishay's ASR measurements.

```powershell
uv sync --frozen --extra audio --extra dev
.venv/Scripts/python.exe -m scripts.install_asr_model --repository Systran/faster-whisper-base.en --revision 3d3d5dee26484f91867d81cb899cfcf72b96be6c --output models/submission-base.en
.venv/Scripts/python.exe -m scripts.build_samsung_package --kit ../participant-kit/participant-kit --output artifacts/native-candidate --team AccessFlow --model qwen/qwen3.8-27b --asr-model-dir models/submission-base.en --warmup-audio tests/fixtures/audio/synthetic_speech.wav --audio-provenance "Existing development fixture generated with Windows speech synthesis on 2026-09-13; no participant recording. See docs/feedback/PROVENANCE.md."
uv venv --python 3.11 artifacts/native-candidate-env
uv pip install --index-url https://pypi.org/simple --python artifacts/native-candidate-env/Scripts/python.exe -r artifacts/native-candidate/requirements.txt
```

Use new model/package output directories; existing directories are never overwritten.
If a download fails, it may leave partial files, but no success record is issued.
Inspect the failed directory before retrying into a new directory. The model installer
accepts an immutable 40-character revision and stores `installation_source.json`.
It does not use saved Hugging Face credentials for this public download.

Confirm the registered team label before actual submission. Keep generated packages
under ignored `artifacts/`: they contain copied organizer materials and model weights.
Keep provider credentials outside tracked files; the existing packaged entry still
requires the declared Groq credential for reasoning setup.

The selected WAV already exists in B's generated development fixtures. It is used
only to load/test the ASR installation, not as a hidden example or representative
human recording. Its expected transcript is never supplied to the agent. The
copied source files and the recording are unchanged.

For vision, add all of:

```text
--vision-model <explicit-installed-Ollama-model>
--vision-url <HTTP-or-HTTPS-origin>
--warmup-image <existing-installation-PNG>
--image-provenance <fixture-origin-and-permission>
```

`--perception-timeout` controls the native deadline (default 30 seconds, maximum
110). ASR is required by the current B worker even for vision, so this builder
does not invent a vision-only worker interface. B owns any future worker change.

## Reproducibility and boundaries

- Only declared model files from a fixed allowlist are copied. Every selected file
  must match the installation record; model total size is bounded to 512 MiB.
  Config/model/tokenizer/vocabulary are required; declared optional model cards,
  license and preprocessing files are preserved. Extra cache files and `.env`
  files are excluded. Symlink model files are rejected.
- WAV/PNG inputs are structurally validated with the existing perception validators.
  Each needs explicit provenance. Silence can pass the packaging format check but
  cannot pass actual ASR warm-up: runtime requires recognized nonempty speech.
- The package uses fixed relative paths under `assets/`; absolute original machine
  paths are not serialized. Entry validation rejects missing assets, escaping paths,
  unsupported settings and conflicting environment before changing the environment.
- `assets/installation.json` records the model origin/revision, fixture provenance
  and hashes, and explicitly says packaging is not live-inference verification.
  `package_manifest.json` additionally hashes all copied package inputs.
- The native dependency export contains conditional pins. The builder resolves
  their union for CPython 3.11.15, Windows AMD64 and Linux x86_64, independent of the
  build host. It rejects target version conflicts, URLs, editable dependencies and
  non-exact pins. This avoids passing marker quotes to Samsung's minimal YAML
  parser, which strips terminal quotes incorrectly. The Windows-only colorama
  dependency is harmless in the Linux union. This is a declared target selection,
  not evidence of Linux execution or support for arbitrary architectures/versions.

The actual generated package had 37 exact pins and 86 hashed inputs. The supplied
evaluator parsed the same pins as requirements.txt and imported its agent without
errors in a fresh Python 3.11.15 Windows virtual environment. Every installed
version and packaged hash matched. Model warm-up then succeeded from that package.

## Actual measurements and limits

With the existing generated 5.304-second recording:

| Check | Observed result |
| --- | --- |
| Repository process worker, first ASR warm-up | 5.161 seconds |
| Same worker, second transcription | 1.386 seconds |
| Fresh package virtual environment, ASR warm-up | 5.418 seconds |
| Observed backend | `faster-whisper/cpu-int8` |
| Recognized content | My screen keeps flickering after the update. Book Wednesday at 5. |

These measure real ASR, not fake perception. They do **not** measure reasoning,
tool completion, microphone streaming, official MP3 assembly, vision, Docker,
Linux execution, repeated official scores or held-out speech quality. The fresh
environment used the same Windows host and cached dependency wheels.

See `docs/evidence/native-package-2026-09-24/README.md` for retained reports, test
results, exact requirements, installation origin and hashes. The reproducible
installer was also run successfully into a separate local directory at the pinned
revision, with matching model-file hashes.

## Next work and ownership

Mridul: official MP3 admission/assembly after the outstanding ownership agreement,
full real queue-path tests, and the remaining submission environment checks.
Atishay: ASR/timing/vision implementation, physical microphone evidence and demo
adoption of the shared configured runtime. **Both must coordinate** clip/turn
finality, interruption semantics and the shared demo/evaluation settings. No B
source/tests were changed here; no fake transcripts or replacement recordings were
created to stand in for his work. Code completion remains ahead of accuracy tuning.
