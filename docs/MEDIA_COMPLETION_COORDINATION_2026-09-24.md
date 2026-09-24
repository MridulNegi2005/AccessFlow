# Media completion coordination - 24 September 2026

Priority: runnable submission code before accuracy tuning or frontend polish.
This is a handoff, not permission for either person to edit the other's components.

## Completed A path

Read SAMSUNG_AUDIO_ADMISSION_2026-09-24.md, CONFIGURED_RUNTIME_2026-09-24.md and
NATIVE_PACKAGE_2026-09-24.md. Samsung queue audio now uses actual MP3 conversion,
explicit end_of_turn and normal B WAV/Observation contracts. Source/revision checks,
pending speech, current-image gating, setup and packaging exist. No B files changed.

New `SpeechStatusEvent` goes only to the controller. It has utterance_id, revision,
pending/failed status, no text/finality/acoustic timestamps. Samsung uses revisions
0/1 for pending and2 for Audio or failure. No B perception support for it is needed.

## B-owned immediate readiness work

1. **Vision latency and worker options.** Actual public-frame perception with existing
   gemma3:4b took23.688s, even with the server warm. The official six-second tail
   ended without image evidence/final. Current provider sends no bounded generation
   options; inspect output length, image preparation and model/service timing first.
   Test proposed generation caps or an alternative explicit vision backend on real
   pixels. Preserve source ID/revision, uncertainty and honest errors. Do not return
   canned captions, supplied annotations or fake embeddings to satisfy checkpoints.
2. **Microphone and streaming tests.** Samsung supplying end_of_turn does not prove
   browser endpoint detection. Test actual capture, continued speech after pauses,
   correction/repetition, barge-in during playback/inference, and cancellation. Record
   actual observed delays and machine/backend. Use voluntary team recordings with
   provenance; synthetic fixtures do not prove human-use performance.
3. **Shared runtime adoption.** Connect the existing demo to the configured real
   composition; retain explicit fake mode for UI tests. Do not duplicate planner,
   authorization or action-ledger logic in the frontend. Stop design polish for now.

## A-owned immediate readiness work

1. Integrate only agreed additive worker/provider options in configured_agent and
   package metadata. Validate/freeze them before setup; no implicit model download,
   silent fallback or inherited environment changing a submitted profile.
2. Finish a reproducible vision-service installation/startup path for the declared
   evaluation environment. The audio package includes ASR weights; it does not
   bundle Ollama/Gemma weights or start that external service automatically.
3. Test package import, setup, raw media, interruptions and cleanup on the supported
   platform. Current evidence is Windows; Docker/Linux is not verified. Check the
   current Docker path against the official procedure, not just fake text replay.
4. Retain both successes and failures. After code paths/platform configuration are
   complete, run three official repetitions and address accuracy/quota failures.
   Single exposed scores54.6/51.5/66.2 are not completion percentages or final results.

## Both must coordinate before changing interfaces

- Agree exact optional vision settings, bounds/defaults and CLI names. B implements
  perception/provider/assigned worker; A validates/wires/packages them. Each adds
  owned tests and golden examples. Neither waits for unimplemented components:
  B tests its real worker directly; A tests its wiring against a fake worker.
- Agree browser pending-speech adoption and calibrated speech start/end metadata.
  Organizer timestamps/duration_ms are not acoustic endpoints. Do not derive timing
  claims from those values or send speech_status to Perception.observe.
- Verify a current frame + speech + correction end to end through both adapters.
  A owns state/authority and stale-result handling; B owns pixels/audio recognition
  and UI/playback behavior. A frame must never grant new write permission.
- Choose one declared release configuration only after it actually runs on the
  evaluation platform. Keep experimental settings and per-backend results separate.

No forms, PPT/video, release tag, public deployment or real external actions are
part of this engineering checkpoint. The frontend remains a testing surface.
