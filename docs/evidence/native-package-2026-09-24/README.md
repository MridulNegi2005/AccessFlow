# Native package evidence - 24 September 2026

- full.xml: 1271 passed, 2 skipped, 1 expected failure; 62.21 seconds.
- focused-initial.xml: 71 passed before marker-resolution and installer tests.
- focused.xml: 76 passed before installer tests; the final full run includes those tests.
- Ruff passed. All B source/tests remain byte-identical to the merged branch.
- repository-asr.json: actual local CPU INT8 ASR through ProcessPerception,
  5.161s first warm-up and 1.386s subsequent transcription of existing generated speech.
- package-verification.json: fresh venv on the same Windows host,37 exact installed pins,
  86 package hashes verified, official YAML pins equal requirements.txt, official import
  passed, packaged real ASR warm-up5.418s. No reasoning call or official task score.
- model-installation.json: downloaded public immutable snapshot and exact file hashes.
  The new installer was run into a second directory; its record matched the original
  installation exactly. Model weights and copied organizer kit remain ignored locally.
- runtime_profile.json and requirements.txt: actual measured package configuration.

The first native build refused conditional uv exports before creating output. The new
native resolver selects the union for declared CPython3.11.15 Windows/Linux x64 targets;
conflicts/non-exact/private inputs fail. The official minimal YAML parser was exercised
on the actual resulting37 flat pins. Linux itself was not tested.

Source package based on4a384d3 with this implementation delta. Package assembly remains
source_dirty=true because built before the checkpoint commit. Source hashes use CRLF-to-LF
normalization; all retained report/XML hashes use exact bytes. No secret is retained.

Commands and limitations: docs/NATIVE_PACKAGE_2026-09-24.md. Full suite command:
`.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/native-package-full-2026-09-24.xml`.
Fresh package verification used its own Python with -I, explicit package root only, and
verified accessflow.__file__ was inside the package. It did not use the editable repo
installation. No claim of MP3 translation, vision, microphone, Docker or clean OS support.

Independent read-only review of installer/assets/profile/dependency code reported no actionable defect. It performed no additional tests; Linux, MP3 and vision-service limitations remain.
