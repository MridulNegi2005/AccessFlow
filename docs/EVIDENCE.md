# Verification evidence

Software tests, microphone observations and benchmark grading measure different layers.

| Check | Evidence and scope |
|---|---|
| Full software suite | Latest recorded run: 1,614 passed, 8 skipped; two dependency warnings. |
| Voice integration | Bounded released-audio probes reached LiveKit and produced spoken replies and mock actions. This is not an aggregate accuracy score. |
| Physical microphone | Four manually observed checks covered corrections, interruption, stop clarification and fresh-room isolation. Individual transcripts and measured interruption delays were not retained. |
| Extension | Destination-state simulation with separate tools and a dashboard; no vehicle control or road routing. |
| Released corpus | 100 WAV inputs validated, totaling 78.632 minutes. Output manifests must establish completed coverage. |
| Official score | No official aggregate benchmark score is claimed. The organizer rerun determines that score. |
| Presentation | Eight Samsung-template slides rendered and visually inspected; native PowerPoint playback not independently tested. |
| Disclosure | Three-page filled template rendered and visually inspected; human signature and declaration review are required. |

JSON records in [evidence](evidence/) retain dated configuration and runtime observations.
They are not a live status feed. Model-comparison traces are retained as regression-test
fixtures; they do not constitute official benchmark results.

See [reproduction](FDB_REPRODUCTION.md) and the [README](../README.md) for setup and media.
