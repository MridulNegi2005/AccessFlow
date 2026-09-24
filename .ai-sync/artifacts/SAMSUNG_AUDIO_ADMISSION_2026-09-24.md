# Samsung audio admission - 24 September 2026

## Result and scope

Samsung's actual queue adapter now accepts real MP3 chunks, assembles each turn only
at its supplied `end_of_turn`, runs the ordinary WAV perception route, and fences
obsolete conversion results. Real official audio development runs reached local CPU
ASR and hosted Qwen without a runtime crash. This closes a missing input path; it
does not establish acceptable task accuracy, live microphone endpointing or readiness
for submission.

Priority remains code completion before prompt/model accuracy tuning. No B-owned
code or tests were modified. PPT, video and submission actions are excluded.

## Ownership resolution and compatibility

The earlier converter checkpoint left the broader turn bridge pending coordination.
Inspection of AGENTS.md assigns shared types, controller and Samsung adapters to A.
This implementation stays within that boundary: an additive controller-only
`SpeechStatusEvent` expresses pending/failed transport input; B still receives a
normal completed WAV with the existing Audio/Observation contract. It does not
require B to change ASR, infer an endpoint, or accept partial audio as final.

This is an A-side implementation decision, not a claim of teammate approval.
Both teammates must coordinate browser adoption, source/revision propagation,
acoustic endpoint timing and uncertainty. The new event must not be sent into
Perception.observe. See CONTRACT.md and CONTRACT_PROPOSALS.md for examples.

## Execution behavior

- First valid audio chunk queues pending speech immediately. Existing write work
  is canceled/superseded conservatively; current frame evidence is retained.
- Partial chunks are accumulated as references, not transcribed independently.
  Finality comes solely from the validated organizer boolean.
- Conversion runs in a bounded subprocess, leaving queue input/output responsive.
  A raw input wins a simultaneous decode race; a ready result then gets service
  after that batch, so sustained input cannot starve media admission.
- Text, explicit interruption or a newer audio turn invalidates old conversions.
  Only the input pump admits current-generation WAVs. Controller source/revision
  checks also reject obsolete ASR/planning results.
- Missing/corrupt/oversized media or a turn without its final chunk produces an
  honest clarification. No transcript or successful action is fabricated.
- An already-final turn can finish decoding during Samsung's normal tail window.
  scenario_end does not end the internal session early.
- Admitted WAVs remain available until perception shutdown. Temporary files and
  exact converter processes are cleaned up; an admitted file is never removed while
  ASR may still be reading it.
- Limits:32 turns/session,32 clips/turn,8MiB/clip,16MiB encoded/turn,120 seconds
  decoded/turn,16MiB cumulative admitted PCM/session,10-second decode deadline.
  Invalid protocol metadata fails explicitly; resource/media failures clarify.

No acoustic endpoint is invented: organizer event timestamps and duration metadata
are not calibrated speech start/end. The public files' actual decoded lengths differ
from duration_ms. Internal unknown speech timestamps remain their existing zero defaults.

## Verification

- Final full suite: **1318 passed,2 skipped,1 existing xfailed**,70.10 seconds.
- Focused protocol/queue/controller/contract suite: **45 passed**,1.59 seconds.
- Earlier full run:1308 passed,2 skipped,1 xfailed before the queue-fairness fix
  and ten additional cases. Earlier new-test fixture errors are retained separately;
  they were incorrect test fields/arguments, not hidden production test failures.
- Controlled tests cover unresolved speech with a frame, write cancellation, late
  ASR/decoder results, explicit interruption, missing final/corrupt media, queue
  fairness, resource limits and malformed metadata. Codec/ASR fakes are labeled.

Actual audio runs used faster-whisper base.en CPU INT8 plus Groq
`qwen/qwen3.8-27b`, full/prose,950 output-token cap, process perception and default
0.08-second partial debounce. Setup used the existing generated speech fixture.
External tools were organizer mocks; no scenario annotations reached the agent.

| Public development case | Score | Actual outcome |
|---|---:|---|
| pub06 audio disfluency |54.6|ASR preserved Boston then New York. Qwen retained New York but requested departure date/passenger details; no search/final checkpoint.|
| pub05 audio ambiguity |51.5|First ASR remained incorrect; later Boston was recognized. Clarifications occurred, but the first missed the scorer's window; no search/final checkpoint.|

Setup took4.532s and4.266s; entire attempts took12.00s and14.56s respectively.
These are individual exposed public attempts, **not medians or completion percentages**.
Both received fast-filler latency credit and a repeated-filler penalty. Fast transport
acknowledgment does not prove a fast substantive answer or a good voice experience.
No prompting/transcription correction was introduced to fit those cases.

Retained evidence: [audio-admission-2026-09-24](evidence/audio-admission-2026-09-24/README.md).

## Package and vision checks

The rebuilt native audio package verified89 file hashes and37 exact installed pins,
then passed the official importer/parser and ran pub06 through its packaged entry
from an isolated Python environment. Setup5.375s,total12.906s,score54.6. The venv
was reused from the earlier clean installation on this Windows host; this is not
a new clean OS or Docker test. Package profile uses1.0s partial debounce and supplied
docs/TOOLS.md, unlike the direct audio runs. All source imports were verified inside
the package. Package/weights/organizer media remain ignored, not published.

The existing portable Ollama0.34.0 installation and gemma3:4b Q4_K_M weights were
found on D: and started on localhost11435. No model download was needed. With the
default30s perception deadline, the first vision setup failed (34.25s whole attempt).
The harness did not retain its exception cause; do not assert a proven timeout cause.
With an explicit110s deadline, setup passed in26.765s, but the public visual case
ended before current image evidence arrived. Its66.2 score included a text-only manual
lookup and no final. It is **not successful visual task completion**.

A separate real observation of the supplied public PNG took23.688s with a warm
vision server and fresh perception worker. It returned an image observation citing
HDMI/USB-C/Thunderbolt; no caption correctness claim is made without image review.
The worker closed cleanly. This latency exceeds the official six-second tail and
is an immediate runtime/perception readiness gap. Raising a timeout does not fix it.
See [the coordination handoff](MEDIA_COMPLETION_COORDINATION_2026-09-24.md).

## Next work

**Mridul:** verify the current native package through the official entry; finish
vision service/runtime integration and platform checks; retain failures; carry the
completed23September corpus-boundary review forward (no whole-repository security
certification is implied); run repeated official evaluation once the declared package is
complete. Then address model/task accuracy with separate evidence.

**Atishay:** real microphone/ASR/vision measurements, endpoint uncertainty, barge-in,
browser runtime adoption and matched-timing tests in owned components. Frontend
polish remains deferred. Audio breadth is not supplied by these two exposed cases.

**Both:** agree on browser use of transport status, calibrated endpoint metadata and
any worker options needed to keep vision responses within the official tail budget.
Do not confuse A's format/finality bridge with B's acoustic endpoint policy.
