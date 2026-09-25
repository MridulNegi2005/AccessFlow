# Package hosting evidence - 24 September 2026

See ../../PACKAGE_HOSTING_2026-09-24.md for commands and limitations.

- config-boundary-before.xml:2 failures/9 passes reproduce A accepting non-loopback
  settings that B's existing provider rejects. Fixed in the A validator only.
- hosting-focused.xml:16 process lifecycle/configuration tests passed using a real
  Python child serving fake metadata. This is not model-inference evidence.
- package-focused.xml:101 passed before final invalid-port/empty-userinfo cases.
- full-before-final-url-validation.xml:1339 passed,2 skipped,1 existing xfailed.
- live-startup-only.json:actual existing Ollama0.34.0 and gemma3:4b digest verified
  on port11436 in6.016s,then owned service stopped. Existing port11435 remained.
- isolated-package-full-setup.json:95 package hashes,37 exact installed pins,
  official import/parser,packaged hosting script and real ASR/vision/Qwen warm-up.
  Service startup6.125s;agent setup47.906s;no scenario score. Reused isolated Windows
  venv. Windows service exit1 is the launcher's intentional terminate,not setup failure.
  Observed no listener on11436 after cleanup;existing port11435/PID2892 remained.
- Dockerfile/dockerignore.txt/profile/requirements/package manifest are exact measured
  package inputs. Docker itself was NOT run. The container recipe is unverified
  against a real daemon/platform,despite passing structural and input-selection checks.
- verify_hosting_candidate.py reproduces the isolated setup check on this installation;
  supply SECRET_GROQ_API_KEY externally and a new output path. It names the explicitly
  measured D: runtime; adapt those paths for a different machine and label new evidence.

Intermediate review corrected an overbroad token filename exclusion that would remove
ASR tokenizer.json,and a .py COPY destination error. Final tests explicitly cover both.
The miniature ignore matcher tests only the selected glob cases,not complete Docker
ignore semantics. Do not present it as an executed Docker build.

Live setup predates only the last fail-fast invalid-port/empty-userinfo rejection.
Those checks leave the tested valid127.0.0.1:11436 profile unchanged. Final source hashes
and final full-suite result are in verification.json/full-final.xml;the measured package
retains its own exact file hashes rather than being silently relabeled as final source.
No B implementation edits,model download,new official task run,accuracy tuning,
Linux execution,workflow dispatch,main push,release or submission occurred.
