# MP3 format conversion checkpoint — 24 September 2026

Later24September update: actual Samsung MP3 admission and isolated native audio runs
are now implemented. See [audio admission](SAMSUNG_AUDIO_ADMISSION_2026-09-24.md)
and [remaining media coordination](MEDIA_COMPLETION_COORDINATION_2026-09-24.md).
The checkpoint details below retain their original test counts and limitations.

## Implemented scope

An A-owned utility now converts an explicitly supplied, complete turn's ordered
MP3 clips to one mono PCM16 WAV at 16 kHz. It uses the existing locked PyAV audio
dependency in an isolated process. It performs no transcription, inference, speech
endpoint detection or controller admission. B's perception/worker/policy are unchanged.

This makes the missing format conversion executable without deciding the remaining
joint C24-1/2 turn semantics. `SamsungProtocol._reject_audio` remains in place until
the converter is integrated with correct pending-speech/interruption handling.
Do not describe this checkpoint as successful official audio task execution.

```python
from accessflow.adapters.mp3_decode import decode_mp3_turn

async with decode_mp3_turn(kit_root, ordered_references) as decoded:
    # Pass decoded.path to the existing ASR interface and finish consuming its
    # observations here. The temporary WAV is deleted when this context exits.
    ...
```

`DecodedTurn` includes actual total and per-clip sample counts and decoded duration.
These are media-duration measurements, not speech start/end timestamps. No expected
transcript, scenario dictionary, organizer annotation or ground truth is accepted.

## Execution and resource boundaries

- One through 32 relative MP3 references rooted below the declared media directory.
  Missing files, absolute/network references, traversal outside the root and other
  extensions are rejected before process creation. The worker repeats admission.
- Encoded limits: 8 MiB per clip, 16 MiB per turn. Reads are bounded even if a file
  grows after stat. Decoded limit: 120 seconds at 16 kHz mono PCM16.
- Each clip is opened from an in-memory byte snapshot with the MP3 demuxer forced.
  A disguised playlist cannot ask the decoder to open external/network resources.
- Clips are resampled independently, flushed and concatenated in supplied order.
  No fabricated inter-clip silence is inserted from organizer timing metadata.
- The caller's event loop remains free during decoding. Default process deadline
  is 10 seconds, configurable up to 30. Cancellation or timeout kills and reaps the
  exact decoder process. Windows uses the real interpreter instead of a venv
  redirector, so killing its PID cannot leave the codec child behind.
- Cancellation during process creation is covered, including repeated cancellation:
  startup is shielded, its process
  is obtained and stopped, then temporary files are removed. Decoder stdout/stderr
  cannot cause unbounded parent buffering; metadata and WAV size are checked.
- Files under the kit directory are still assumed to be trusted immutable installed
  assets. This is not a defense against a hostile local administrator replacing the
  installation during a call. No unrelated process is terminated.

## Actual public-media measurements

Existing pinned Faster Whisper base.en, CPU INT8; Windows Python 3.11.15. ASR was
warmed with the previously documented generated installation fixture (3.840 seconds).
Only explicit MP3 file lists were sent through decoding and ASR.

| Public file/turn | Actual decoded duration | Decode | ASR | Actual recognized text |
| --- | --- | --- | --- | --- |
| pub_05_turn1.mp3 | 3.072 s | 0.853 s | 1.193 s | I broke up, and I did too fast. |
| pub_05_turn2.mp3 | 1.565 s | 0.862 s | 1.123 s | I said Boston. |
| pub_06 two clips, supplied in order | 7.488 s | 0.971 s | 1.347 s | Book a flight to Boston. Actually make that New York. |

The first ambiguity recording is a poor transcription, **not a successful task**.
Do not hide it, substitute its reference text, or tune against it while calling it
held-out. Correction content survived ordered assembly in pub_06, but no reasoning,
tool dispatch, speech timing, microphone or official score was evaluated here.
This is a single public development check, not a reliability statistic.

The pub_06 clips decode to 4.128 and 3.360 seconds; their event `duration_ms` fields
say 1.2 and 1.1 seconds. Retain event timestamps as organizer scheduling metadata
and sample counts as measured media duration. **Both Mridul and Atishay must
coordinate** a truthful clock mapping; neither value establishes when a live person
finished speaking. Do not synthesize a calibrated endpoint label from these fields.

## Required next integration

Mridul owns the adapter/controller side. Atishay owns transcription uncertainty,
speech activity/finality, turn policy and microphone transport. The complete bridge
still needs the shared decision recorded under C24-1/2:

1. Receive nonfinal clips without exposing a completed command or dispatching a
   write. An incomplete turn must remain pending until an authoritative finality
   signal arrives; handle missing final clips with bounded failure/cleanup.
2. Keep latest image context alive while speech arrives. Reusing a broad speech
   interrupt purely as an audio-arrival marker currently cancels pending vision,
   so it is not an acceptable shortcut for image-plus-audio scenarios.
3. Keep tool results/explicit interruptions responsive during decoding and ASR.
   Supersede old conversion/transcription results by source identity and generation.
4. Carry real observation identity, uncertainty and explicit timing provenance into
   the controller; do not invent transcripts or final partial observations.
5. Run pub_05/pub_06 through the actual generated entry and actual tools, preserving
   ambiguity failures and latency. Current direct conversion/ASR evidence cannot
   replace this gate.

No shared contract, B source/test, submission tag, real external action or workflow
was changed. Runtime input integration remains open rather than being silently
assigned or simulated by this utility.

## Verification

`tests/engine/test_mp3_decode.py` covers real codec/resampling/order, corrupt input,
path/size/duration limits, no output overwrite, timeout/cancel, cancellation during
spawn and removal of temporary output. Test tones are unit-test signals, not new
speech recordings or perception-quality evidence. Retained reports and hashes are
under `docs/evidence/mp3-converter-2026-09-24/`.
