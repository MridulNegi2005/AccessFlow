# AccessFlow presentation outline

This outline is a content draft for the required organizer template. Replace the layout
with the supplied template when it arrives. Every number and claim must stay tied to the
listed commit, backend and hardware.

## Slide 1 — AccessFlow

**Claim:** Give people time to finish speaking, preserve corrections and prevent stale or
unfinished requests from becoming actions.

**Scenario:** “Book Tuesday ... actually, Wednesday at five.” A late result or proposed
write must not silently win over the newer request.

**Status label:** Prototype; no real bookings or payments.

## Slide 2 — The failure mode

Show a short sequence:

1. A person starts a request.
2. The system responds during a pause or acts on an earlier revision.
3. The person corrects or cancels.
4. AccessFlow keeps the latest evidence and action state visible.

State the research question from the implementation plan: can premature responses and
incorrect actions be reduced without making every interaction wait longer?

## Slide 3 — Architecture and ownership

Show the flow:

~~~text
input queue -> perception/timing -> controller -> reasoner -> action ledger -> output
~~~

Annotate:

- Perception preserves event IDs, source IDs, revisions and timestamps.
- Timing provides acoustic facts only.
- The controller owns session state and invalidates stale work.
- Tools are behind manifests and authorization.
- The demo renders OutputEvent state; browser code does not own planning.

## Slide 4 — Corrections and pauses

Show the pause-correction fixture and a visible transcript revision.

Verified local evidence:

- Faster Whisper base.en CPU INT8 retained the correction wording.
- WebRTC produced a timing candidate over a labeled inserted break.
- A pause candidate never becomes semantic completion by itself.

Use the phrase “generated development evidence” on the slide.

## Slide 5 — Action safety

Show the offline controller states for:

- pending result,
- stale result after newer speech,
- uncertain write,
- reconciliation before retry.

Use the rule:

> Proposal, attempt and confirmed effect are separate states.

Mark tool effects as mock/offline in the current demo. Do not show a real booking or customer
record.

## Slide 6 — Multimodal and browser boundary

Show the text, WAV/microphone and PNG controls.

Verified:

- WAV and PNG payloads are size/type validated and stored in a session temporary directory.
- The microphone path encodes mono PCM to WAV in the browser.
- Optional local audio uses an existing Faster Whisper model when configured.
- Text and image demo responses remain mock; live vision is not certified.

## Slide 7 — Evidence

Use a compact table:

| Evidence | Result | Boundary |
|---|---|---|
| Offline suite | 64 tests passed | Software correctness only |
| Held-out generated ASR | 3/3 intended case wordings retained | Generated voice, not human accuracy |
| Labeled pause case | 1.2 s break fully overlapped; candidate IoU 0.606 | Fixed-window timing, early acoustic margin |
| Local demo route | Real WAV reached Faster Whisper and controller | Mock reasoner; no real action |

Include commit, model snapshot, CPU and settings in speaker notes.

## Slide 8 — Limits and next gate

Remaining evidence:

- manual browser permission and physical-device smoke,
- human speech and endpoint quality,
- live vision and non-mock reasoning,
- engine integration review,
- voluntary feedback notes,
- Docker/CI and the 60-scenario set,
- official template, disclosure and final release assembly.

Close with the reproducibility path:

1. clone the public repository,
2. switch to the reviewed branch/commit,
3. run the documented tests,
4. inspect backend labels and limitations before judging results.

## Speaker-note requirements

For the final deck, record the exact commit, model/backend, hardware, fixture provenance,
test command and known warnings on every evidence slide. Label any placeholder as a
placeholder. Do not include participant data, secrets, organizer-private material or
clinical claims.

