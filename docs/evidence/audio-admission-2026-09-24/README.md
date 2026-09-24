# Audio admission evidence - 24 September 2026

See ../../SAMSUNG_AUDIO_ADMISSION_2026-09-24.md for implementation and limits.

- full-final.xml:1318 passed,2 skipped,1 existing xfailed,70.10s.
- focused.xml:45 passed; package-tests.xml:64 passed. Ruff and diff checks passed.
- full-before-fairness.xml:1308 passed before the starvation guard and additional cases.
- Initial controller fixtures:2 failures (async cancellation assertion and wrong helper
  argument order); initial queue fixtures:2 failures (wrong action and observation kind);
  second queue fixture:1 failure (wrong action name). Corrected to actual contracts,
  preserving production guards. All initial outputs retained, not recast as successes.
- public-audio-*.json:actual official queues,CPU ASR and hosted Qwen,one exposed attempt
  each. Scores51.5/54.6; tasks did not complete. No mocked perception in these runs.
- vision-setup-failed.json:first default30s attempt failed setup; exception cause was
  not preserved by the runner. No score and no claimed successful image perception.
- vision-official-tail-missed.json:110s setting allowed warm-up;score66.2 included a
  text-only lookup but no image-grounded final. Official six-second tail unchanged.
- vision-single-observation.json:actual public PNG observation23.688s,worker closed.
  Warm Ollama server/fresh worker; no scenario annotations and no accuracy certification.
- package-public-audio.json:isolated native package,89 hashes/37 pins/official import
  verified;actual pub06 score54.6. Reused earlier fresh Windows venv,not a fresh OS.
- verify_package.py reproduces that package check with an isolated Python:
  `python -I verify_package.py <package-directory> <new-output-json>`.
  Supply the declared SECRET_GROQ_API_KEY outside tracked files; the script includes none.
- runtime_profile/requirements/package_manifest are the measured package inputs.
  Vision is disabled in that audio package; vision tests used the repository configuration.

Source base is5d13a26 plus this implementation delta. Runtime source hashes remained
stable during live checks. Reports retain their own raw source/scenario hashes;
verification.json also provides normalized source hashes and exact evidence hashes.
Generated packages,weights,organizer media and credentials are not committed here.
One attempted focused command named a nonexistent test_native_package.py and collected
nothing; corrected command used test_package_media.py and passed64 tests. No test
result is claimed for the mistyped invocation.

No B source/tests were edited. No microphone,three-repetition score,Docker/Linux,
release tag,submission or accuracy-tuning success is established by this evidence.
