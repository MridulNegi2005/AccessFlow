# MP3 converter evidence - 24 September 2026

- focused.xml:final24 passed in4.32 seconds; focused-initial.xml23 passed in4.36 seconds.
- full.xml:final1295 passed,2 skipped,1 expected failure in63.69 seconds.
- full-initial.xml:1294 passed before the repeated-cancellation regression/repair.
- Ruff clean; no B source/test/worker, shared contract or Samsung admission change.
- live-public-media.json: actual forced-MP3 decoding followed by existing real CPU
  INT8 ASR on all four supplied public audio clips (three complete turns). Only paths
  entered the decoder; neither decoder nor ASR received scenario annotations/labels.
- pub05 first recording transcribed poorly; retained verbatim. The second recognized
  Boston. pub06 concatenated correction text retained Boston then New York.

These are exposed public development clips, not held-out or clinical samples.
No official queue/task/scoring, model reasoning, microphone or vision was exercised.
No raw organizer media was copied into this evidence directory.

The only new synthesized audio consists of unit-test tones generated in temporary
test directories for codec order/resampling assertions; these are not human recordings.
Cancellation/timeout tests use a blocking child and verify its exact process exit and
removal of temporary files, including cancellation before process creation completes.

Source parent ecc6691; changes belong to this report's commit. Source hashes normalize
CRLF to LF; retained XML/JSON hashes cover exact bytes. See MP3_CONVERTER_2026-09-24.md
for the required joint turn/finality/controller integration that remains outstanding.

Commands:
`.venv/Scripts/python.exe -m pytest tests/engine/test_mp3_decode.py -q`
`.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/mp3-converter-full-2026-09-24.xml`
`.venv/Scripts/python.exe -m ruff check .`

Independent read-only review found repeated cancellation during shielded startup could
abandon a soon-to-start process. double-cancel-before.xml reproduces that failure; the
fixture itself reaped its deliberate worker. Cleanup now has its own shielded owner and
survives repeated caller cancellation before propagating it. The final focused/full runs
cover the fix. Real public ASR measurements preceded only this cleanup change; the
conversion/ASR path is unchanged and is not claimed to have been live-remeasured afterward.
Source hashes at the live check and final source hashes are recorded separately.
