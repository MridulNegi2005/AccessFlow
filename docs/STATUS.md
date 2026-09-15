# Implementation status

Updated 13 September 2026. This file records implementation, not aspirational completion.

## Bootstrap

- Typed v0.1 input events, snapshots, observations, tool manifests/calls and proposals added.
- Protocols, injectable clocks, fake perception/reasoner/tools and baseline policy added.
- Initial engine and controlled safety tests are implemented. The engine baseline covers
  contracts, partial-write blocking, dynamic names, corrections, cancellation, stale reads,
  duplicates, intentional repeat writes and authorization.
- Atishay's owned Workstream B now includes transcript/audio/frame perception seams,
  deterministic turn policy, a labeled fake-agent browser demo, fixture provenance,
  dependency-free PCM loading, local Faster Whisper configuration and optional Ollama
  vision provider tests.
- Git has main, mridul/engine and atishay/perception; the public branch is published.

## Workstream B — Atishay

Updated 16 September 2026.

- Multimodal end to end evidence now covers one session carrying a validated WAV and PNG through
  event_from_message, injected local ASR and vision providers, DemoPerception, and one Agent
  context. Source IDs and backend labels are preserved; the final response is informational.
- Browser event timestamps now cross the owned demo boundary on the event envelope, audio
  speech_start/speech_end values are forwarded into typed audio events, and frame timestamps reach
  image observations. The adapter still accepts the earlier payload timestamp form for compatibility.
- The multimodal regression also covers both arrival orders, a revised audio hypothesis and
  WebSocket paths: the latest transcript revision replaces the prior one while the frame remains
  in the same context, and the combined WAV, PNG and text response exposes both retained
  modalities. A browser transport regression verifies that the revised hypothesis survives the
  session route.
- Partial speech followed by a final image is covered by a write-safety regression:
  correction_pending stays true and no write tool is invoked.
- Image-only vision text that resembles a write request is also blocked: no write call or effect
  is allowed without a spoken request.
- The turn policy now treats image observations as context-only for speech cues, so captions containing
  correction or backchannel words cannot pause, complete or stop a spoken turn; a direct regression
  covers this boundary while existing text behavior remains covered.
- The WebSocket ordering regression also covers PNG arriving before WAV; the later audio final
  retains image context in the same session.
- A session-reset WebSocket regression confirms a new connection does not inherit the prior session's
  audio or image context.
- The WebSocket image boundary also recovers from malformed PNG input with a labeled error and
  keeps the session available for a subsequent text request.
- The WebSocket input boundary also recovers from a non-object multimodal payload with a labeled
  demo/input error and keeps the session available for a subsequent transcript. Encoded uploads are
  rejected before base64 decoding when they exceed the 8 MiB raw-media budget.
- PNG ingestion now validates chunk boundaries, CRCs, legal IHDR values, IDAT presence, zlib stream
  integrity and terminal IEND structure before a frame reaches a vision backend; rejected uploads are
  removed from the session directory. A direct cleanup regression verifies invalid PNG materialization
  leaves no session file behind.
- Failed WAV uploads now remove their post-header validation materialization, and local injected
  audio backends identify themselves separately from the installed Faster Whisper path in the demo label.
  An injected backend without an identity is reported as local/unknown-audio rather than overclaimed.
  Injected vision backends without an identity, including model-only test doubles, now use
  local/unknown-vision rather than crashing or implying an Ollama model.
- A configured vision-backend failure is also covered: it emits backend_failure without a
  misleading final response.
- The Ollama vision provider normalizes syntactically invalid JSON bytes and syntactically valid
  non-object JSON roots into classified invalid JSON errors, with raw-byte, list and null response
  coverage, and normalizes provider timeouts
  into the same stable runtime failure boundary.
- The configured vision failure is also covered through the WebSocket route: backend_failure is
  emitted and the same session completes a later text request. A malformed list response and a
  provider timeout follow the same route and are also recoverable.
- Vision quota exhaustion is covered at provider and WebSocket boundaries: the quota error becomes
  backend_failure, produces no misleading final, and the same session accepts a later transcript.
- HTTP quota responses are also normalized: a JSON error body from a 429 response is surfaced as the
  provider's classified quota failure instead of an opaque transport error.
- The WebSocket regression now exercises an HTTP 429 quota response through the configured vision provider,
  emits backend_failure, and confirms the same multimodal session accepts a later transcript.
- Audio and image adapters reject blank or non-string provider output as a classified runtime failure, so malformed
  perception cannot become a misleading empty observation.
- LocalPerception now accepts an opt-in finite timeout_s for audio and image providers. Deadline expiry is classified by modality and tested directly; the default remains unlimited for compatibility, and synchronous work already running in a worker cannot be forcibly stopped.
- Slow audio and image inference are covered at the perception boundary: replaceable providers run in workers
  while an async heartbeat remains responsive.
- An audio backend failure is also covered through the WebSocket route: backend_failure is emitted,
  then a later PNG and spoken request complete in the same multimodal session with image context retained.
- A protocol-level loopback regression now runs the actual OllamaVisionProvider HTTP path with local
  ASR in one Agent context; it verifies model, prompt, image bytes and informational output without
  claiming live model quality.
- The configured vision environment is covered at the WebSocket boundary: a loopback provider receives
  the PNG and the later response retains the returned image evidence beside the spoken question.
- The combined configured-backend WebSocket regression now calls DemoPerception.from_environment with both
  modalities configured, then checks WAV and PNG transport, backend labels, source IDs and informational output.
- In-flight frame race coverage verifies that a delayed frame 1 result cannot enter the multimodal
  context after frame 2 arrives; only the current frame is presented to the reasoner.
- The changed-frame WebSocket reproducer is a strict expected failure until the controller
  removes the prior frame from the active context.
- A strict conflicting-frame reproducer shows that contradictory visual evidence currently has no
  structured resolution state before a write; an additive provenance/conflict proposal is recorded
  for the engine owner without changing shared contracts here.
- Cross-modal in-flight coverage now proves a delayed audio observation remains usable when a newer
  frame arrives; source acceptance preserves both independent modalities in one reasoner view.
- A fresh local WebSocket run used the installed Faster Whisper base.en CPU INT8 snapshot and the
  configured OllamaVisionProvider against a loopback protocol service; in 1.326 seconds it retained the
  recognized speech and returned image evidence in the same session. Vision quality and reasoning remain unverified.
- A second composition run used the installed Faster Whisper base.en CPU INT8 snapshot for real
  audio inference and an injected vision provider; the paired context completed in 3.222 seconds.
  A fresh Chrome run also routed the speech fixture through that local backend before accepting a
  PNG in the same session. The result is mixed evidence, not a live multimodal model benchmark.
- Browser base64 decoding and WAV/PNG materialization validation now run in a worker from the WebSocket
  receive path, keeping upload handling off the event loop.
- The browser demo renders untrusted multimodal event kinds and payloads through text nodes, so model or
  transcript output is displayed without interpreting markup.
- The real Chrome smoke now passes text, checked in WAV, PNG plus paired transcript, and
  microphone capture through the served AudioWorklet. A separate isolated Chrome run used the
  present Microphone Array without a fake audio-device flag and completed the real getUserMedia,
  WAV upload and mock final path. The fresh CDP run also shows the mock final carrying prior
  audio and image context, with no console or page errors or horizontal overflow.
- The demo reasoner now bounds prior multimodal context to 16,384 characters while retaining the newest evidence by truncating only the item that reaches the remaining capacity. Regressions cover recent evidence, oldest-history omission, the exact bound for an oversized prior item, and request completeness.
- LocalPerception now gives each session one provider call plus one pending item per modality, coalesces obsolete same-session frames and same-utterance audio revisions, suppresses stale results and keeps audio/image workers independent. DemoPerception retains the vision worker for the session and closes active and queued work during WebSocket shutdown; synchronous worker threads remain non-force-cancellable.
- The demo WebSocket now serializes controller events, media statuses and recoverable input errors through one outbound sender, preventing concurrent writes from interleaving. A route regression holds a controller send open while an invalid frame is received and confirms no overlapping WebSocket sends.
- A configured WebSocket regression now exercises the real LocalPerception Faster Whisper model branch with a deterministic factory and the real OllamaVisionProvider HTTP path together. It sends text, two revised WAV hypotheses and PNG in one session, then verifies that the latest audio revision, timestamps, distinct generated event IDs, source IDs, backend labels and one informational multimodal final are retained.
- A configured recovery regression sends a valid PNG, a failing audio revision and a corrected revision for the same utterance. It verifies one classified backend failure, no stale audio observation, and a later final retaining the corrected audio beside the frame.
- A concurrent WebSocket regression keeps two browser sessions open together, carries image and audio in the first session, and verifies that neither modality can appear in a fresh transcript final from the other.
- LocalPerception now closes admission before validation can register new work, suppresses observers that finish validation after shutdown, and marks each bounded worker closed. Audio, image and transcript shutdown races plus post-close DemoPerception admission are covered; closed peers also terminate the demo sender cleanly.
- A route-level cleanup regression confirms valid uploaded WAV and PNG files exist inside the live session directory and that the directory is removed after WebSocket disconnect.
- The conflicting-frame expected failure now uses two content-distinct valid PNG payloads, asserts their Tuesday/Wednesday captions, and waits until the first reaches the reasoner before sending the second. Its remaining failure is a deterministic controller conflict-state gap rather than a perception coalescing or fixture artifact.
- Integrated-state review against origin/mridul/engine 919ed27 confirms targeted active-frame replacement and image-only informational tests pass there. That controller removes the superseded frame before planning, so the conflicting-evidence proposal still needs an additive pre-replacement comparison or provenance signal; no protected engine or contract file was changed here.
- A fresh shallow public-clone check on 16 September 2026 checked out `atishay/perception`, resolved `origin` to the shared GitHub repository and included `ATISHAY_START_HERE.md` at commit `4892c185`.
- WAV validation now reads the declared PCM frames in bounded chunks and rejects a truncated payload before audio inference; the new regression passes in the full multimodal suite.
- PNG validation now checks decompressed scanline sizing and filter bytes, including Adam7 row sizing, before an image reaches a vision provider; incomplete scanline coverage passes in the full suite.
- PNG validation now groups scanline accounting instead of materializing one entry per declared row, rejects decoded payloads above 64 MiB before decompression, and avoids an unbounded zlib flush. A huge-dimension PNG regression covers the resource boundary.
- PNG validation now requires a correctly sized palette before IDAT for indexed-color images and bounds indexed palette entries by bit depth.
- Ollama vision configuration now rejects non-string model/endpoints and non-finite, boolean or non-positive timeouts with stable ValueErrors before a request is attempted.
- Browser sends now queue up to 16 text, WAV or PNG actions while the WebSocket is connecting, flush them in order on open, and report labeled transport errors when the queue is full or the session is closed.
- Browser transcript submissions now keep one utterance ID across partial and final hypotheses, incrementing revisions in order and closing the active utterance only after its final hypothesis.
- Browser payload factories now defer transcript revisions and audio/frame identity allocation until a send is accepted or queued. Media IDs use a page-scoped monotonic sequence, preventing rapid uploads from reusing a source identity; rejected microphone uploads are reported as rejected.
- Threaded browser upload materialization is now shielded from receiver cancellation and drained before the session directory is cleaned up, so a disconnect cannot race an in-flight WAV or PNG write. A focused cancellation regression covers this boundary.
- PCM loading, energy activity, WebRTC VAD and pause-threshold boundaries now reject booleans, wrong numeric types and non-finite values with stable ValueErrors instead of leaking arithmetic or range TypeErrors.
- The bounded audio worker now keeps pending work per utterance key, so a newer revision for one utterance cannot discard an unrelated queued utterance; same-utterance replacement and the single active provider-call limit remain intact.
- A real local Uvicorn/WebSocket run on the current demo served a WAV, PNG and transcript sequentially in one session; it emitted media statuses and finals whose last context retained both audio and image evidence.
- A fresh current-head Uvicorn/WebSocket smoke repeated the mock route with the checked-in WAV and a valid PNG: both media acknowledgments arrived in one session, and the final retained audio and image context.
- A current-head served run also used the cached Faster Whisper base.en CPU INT8 model and a loopback Ollama vision endpoint: the speech fixture was transcribed, the PNG produced image evidence, and the final transcript retained both real audio and vision observations. This is protocol/backend evidence with mock reasoning, not a live quality benchmark.

- Final verification is 187 tests passed with 4 strict expected failures, including 71 passing demo
  tests and 100 passing perception tests; Ruff, compilation and git diff --check are clean. The browser runtime
  still uses local only websockets 17.1.
- The four expected failures record current controller integration gaps: image-only informational response,
  direct or WebSocket replacement of a prior active frame, and unresolved conflicting-frame evidence before
  a write. The owned timing-policy seam now accepts optional activity metadata while shared engine/controller
  wiring remains a pending additive proposal. Proposals and corresponding integrated-branch behavior are
  available for the engine owner; no engine or contract file was changed here.
- Evidence is mixed and still bounded: live vision quality and non mock reasoning are still
  open. Direct inspection of the existing 13–14 September captures shows no visible clipping,
  overlap or broken text in the shown viewport; a fresh current-HEAD full-page visual inspection
  remains open.
- origin/mridul/engine was fetched at 919ed27 for integrated state review. No engine owned
  files were changed and this branch remains atishay/perception.

## Still required

- Broader engine race tests and validation of the normalized status reconciliation route.
- Live reasoning adapters, official-kit adapter after the kit is supplied, replay and metrics.
- Held-out generated-case ASR and endpoint measurements are recorded; human speech and endpoint quality, live vision service and real multimodal
  benchmark on declared hardware.
- Manual browser/device smoke proof, a completed voluntary feedback session, demo video and final presentation assembly.
- Docker/CI verification, the 60-scenario authored/provenance-tracked set, reviewed disclosure
  and final release assembly.

No live model, official compatibility, latency or completion target is currently certified.

## Checkpoint 17 - 13 September 2026: feedback and recording safeguards

Prepared the owned feedback and presentation artifacts for later human-led validation.

- docs/feedback/SESSION_TEMPLATE.md requires voluntary participation, separate capture
  consent and anonymized notes by default.
- docs/presentation/DEMO_RECORDING_SCRIPT.md provides a 4m40s evidence-labeled sequence
  for the current mock/local boundaries.
- No participant feedback or recording was collected in this checkpoint.
- Manual browser/device smoke, engine integration and final presentation recording remain.
## Checkpoint 18 - 13 September 2026: held-out generated speech and endpoint check

Measured three newly generated voice cases after fixing the local evaluation configuration.

- Faster Whisper preserved the fluent request, repeated phrase, correction and two-part
  request through LocalPerception.observe.
- WebRTC produced no internal candidate for the fluent or repetition case.
- On the labeled 1.2 second break, the candidate overlapped the full break but included
  0.669 seconds of early acoustic margin.
- The results are held-out generated-fixture evidence only; human speech accuracy and
  endpoint quality remain unverified.
## Checkpoint 19 - 13 September 2026: opt-in local audio demo path

Added an environment-gated local audio mode to the owned browser demo.

- The default remains demo/mock.
- Setting ACCESSFLOW_DEMO_WHISPER_MODEL to an existing model path routes WAV input through
  LocalPerception and displays the local backend label.
- Text and image inputs remain demo/mock.
- A real checked-in WAV completed the WebSocket route with the cached Faster Whisper model;
  the controller emitted its informational final output.
- Browser permission/device capture and live vision remain unverified.
## Checkpoint 20 - 13 September 2026: presentation content outline

Added docs/presentation/SLIDE_OUTLINE.md as a template-neutral content draft.

- Covers the problem, failure mode, architecture, correction/timing, action safety,
  multimodal boundary, evidence and limitations.
- Ties numbers to the current generated fixtures, local model configuration and test suite.
- Marks the official template, recording, feedback, integration and release work as
  outstanding.
## Checkpoint 21 - 13 September 2026: session path isolation

Hardened the browser media boundary against client-supplied filesystem paths.

- Session WebSocket traffic now roots no-byte fallbacks in the session temporary directory.
- Existing base64 WAV/PNG validation and cleanup remain unchanged.
- The boundary has a focused regression test; no shared contract or dependency changed.
## Checkpoint 22 - 13 September 2026: local model configuration guard

Added explicit validation for the optional local model path.

- Invalid configuration is reported as demo/config before an agent starts.
- The default mock mode and valid local configuration remain unchanged.
- Demo tests cover both the error event and the valid opt-in label.
## Checkpoint 23 - 13 September 2026: opt-in local Ollama vision path

Added an optional Ollama PNG provider and environment-gated demo routing.

- The provider accepts only loopback HTTP(S) endpoints.
- PNG bytes are sent to an already-running service; no model download occurs.
- LocalPerception preserves frame identity and reports the provider backend name.
- Mocked provider and demo tests cover successful responses and configuration/service errors.
- No Ollama executable or loopback service was available on this machine; live model
  availability and vision quality remain unverified.
## Checkpoint 24 - 13 September 2026: WebSocket media protocol smoke

Verified the browser demo's validated media path end to end for base64 WAV and PNG payloads.

- The WebSocket reports the received media kind and preserved source ID after materialization.
- WAV transport reaches the mock controller and emits its expected informational final.
- PNG transport is validated and session-scoped; the current v0.1 agent requires a paired
  transcript before producing a controller final, so image-only planning remains an engine
  integration item.
- Demo tests: 18 passed; full suite: 77 passed; Ruff and git diff --check are clean.

## Checkpoint 25 - 13 September 2026: functional Chrome browser smoke

Ran the local demo through a temporary isolated Chrome session using the actual page controls.

- Text produced the visible mock acknowledgment and informational final output.
- The checked-in WAV file control produced a media-received audio status and mock final.
- The PNG file control produced a media-received frame status; the current v0.1 agent then
  produced a final after a paired transcript.
- The rendered document had no horizontal overflow in the captured viewport.
- The smoke required local-only websockets 17.1 because the committed Uvicorn dependency
  does not currently include a WebSocket runtime. This is recorded as a dependency proposal.
- Physical microphone/device capture, pixel inspection and separate console capture remain
  unverified.
## Checkpoint 26 - 13 September 2026: synthetic microphone browser smoke

Exercised the microphone controls in isolated Chrome with Chrome's synthetic audio device.

- Start entered the recording state and enabled the stop control.
- Stop closed the capture path, encoded the samples as WAV and uploaded them through the
  session WebSocket.
- The browser observed media_received=audio and the mock controller final.
- No person or physical microphone was recorded. Physical device permission, pixel inspection
  and separate console capture remain unverified.
