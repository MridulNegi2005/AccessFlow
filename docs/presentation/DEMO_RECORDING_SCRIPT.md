# Demo recording script

Target length: 4 minutes 40 seconds. Record the current prototype with the backend label
and commit visible. The script separates verified implementation from future integration;
do not present a placeholder or mock output as live model evidence.

## 0:00–0:25 — Problem

Show the AccessFlow title and one sentence:

> People often correct, pause or cancel a request while an agent is still working. AccessFlow
> keeps those states visible and prevents an unfinished or outdated request from becoming
> an action.

Show the architecture labels: input, perception/timing, controller, tools and output.

## 0:25–1:20 — Speech correction

Use the generated, provenance-tracked pause-correction fixture or a typed equivalent:

> Book Tuesday ... actually, Wednesday at five.

Show the transcript revision and the correction state. Explain that the local fixture and
timing measurements are development evidence. If using the browser microphone, show the
capture control and its backend label, then state that the current demo transports a WAV
payload into the session-scoped upload route while downstream perception remains demo/mock
until the live integration is available.

Do not claim held-out speech accuracy or clinical representativeness.

## 1:20–2:15 — Pending tool and stale result

Use the fake-agent scenario that displays a pending action, then change the request before
the earlier result returns. Show the old result marked stale and the newer request kept
authoritative.

Narrate:

> A late result is evidence with an old revision. The controller must reconcile it before
> any action is accepted.

If this scenario is not yet wired into the browser demo, show a clearly labeled
integration placeholder and say that the offline contract test proves the behavior; do
not simulate a completed live tool call.

## 2:15–3:00 — Image correction

Upload a PNG through the validated route and show the frame ID and timestamp. Demonstrate
an ambiguous image response from the injected provider and a correction or clarification.

Narrate:

> The PNG path preserves frame identity and timing. The vision provider is replaceable,
> and the current checkpoint does not claim live vision quality.

Do not use a canned caption as if it came from a live vision model.

## 3:00–3:35 — Uncertain write and reconciliation

Show an uncertain or interrupted write in the fake scenario. The visible state should
separate proposal, attempt and confirmed effect, then reconcile the result before retrying.

Narrate:

> A proposed action is not a confirmed side effect. Unknown outcomes stay visible until
> the system has evidence to reconcile them.

If the browser slice is not yet integrated, use the offline test output or a labeled
static capture instead of inventing a tool response.

## 3:35–4:15 — Measurements

Show the README or feedback measurements with the exact configuration:

- Faster Whisper base.en CPU INT8 on Intel Core Ultra 5 125H: generated speech adapter
  elapsed 5.874 seconds for 5.304 seconds of audio, realtime factor 1.108.
- WebRTC activity on the generated pause-correction fixture: one 2.260 second internal
  candidate and one 0.640 second trailing candidate at the recorded threshold.
- The deterministic tone was classified as active audio, so acoustic activity is not
  proof of speech.

Say:

> These are local development measurements on generated fixtures. They are not held-out
> accuracy, latency certification or user-benefit results.

## 4:15–4:40 — Architecture, feedback and limits

Show the owned component boundary and say:

> Perception, timing and the minimal demo are independently testable. The shared engine
> owns authoritative session state and action safety. Feedback will be voluntary and
> anonymized by default. Remaining work includes held-out speech and endpoint cases,
> manual browser and device smoke, live vision, integration, Docker/CI, feedback notes
> and the final presentation.

End on the repository URL, branch or reviewed commit, backend label and known limitations.
