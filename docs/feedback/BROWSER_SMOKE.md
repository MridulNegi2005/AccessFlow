# Browser smoke evidence

Date and branch: 2026-09-14 / atishay/perception

Status: FUNCTIONAL EVIDENCE COMPLETE; PIXEL INSPECTION OPEN

The functional browser smoke passed in a temporary isolated Chrome session, including the
served AudioWorklet microphone path. A second isolated run used the machine's real microphone
endpoint without a fake audio-device flag and completed the same capture and upload path.
Pixel-level inspection remains unavailable because the image inspection helper failed to open
the captured PNG.

## Runtime

- Browser: Chrome 152.0.7977.84, headless mode through Chrome DevTools Protocol
- Route: http://127.0.0.1:8000/
- Rendered inner viewport: 756 x 900; document scroll width: 741
- Backend label: demo/mock
- Local-only runtime addition: websockets 17.1 in the ignored development environment
- Microphone run: Chrome fake UI and fake audio device flags; no person or physical recording
- Physical-device run: Chrome used the present Microphone Array endpoint without a fake
  audio-device flag; getUserMedia, AudioWorklet capture, WAV upload and the demo final completed
- Recorder module: /recorder-worklet.js, served by the demo and loaded by AudioWorkletNode.
- No committed pyproject or lockfile change; add a WebSocket runtime dependency through the
  shared owner before relying on Uvicorn for a fresh browser setup.

## Requirement matrix

| State | Evidence | Result |
|---|---|---|
| First paint and page identity | Chrome DOM: title AccessFlow mock demo and demo/mock label | PASS |
| WebSocket connection | Chrome event stream included connected and perception_backend statuses | PASS |
| Text submission | Chrome event stream included acknowledge and informational final for Book Wednesday | PASS |
| WAV file control | Chrome selected the checked-in synthetic tone and observed media_received=audio and a mock audio final | PASS |
| Microphone control | Fresh Chrome fake device entered recording state, stopped, uploaded a WAV and observed media_received=audio plus a mock final | PASS |
| Physical microphone permission and capture | Isolated Chrome without fake audio-device flags entered recording from the present Microphone Array, stopped, uploaded a WAV and observed media_received=audio plus a mock final | PASS |
| PNG file control | Chrome selected a session PNG and observed media_received=frame; paired transcript produced its final | PASS |
| Visible multimodal context | Fresh Chrome final after WAV, PNG and text included both prior audio and image context in the response | PASS |
| Browser local-ASR mode | Fresh Chrome used the cached Faster Whisper snapshot; the audio acknowledgment reported faster-whisper/cpu-int8 and included the recognized speech | PASS |
| Combined media session | Fresh Chrome sent a WAV, then a PNG and paired transcript in one browser session; both media statuses and finals were observed | PASS |
| Layout overflow | body scroll width 741 was below inner viewport width 756 | PASS |
| Visual pixel inspection | Captures were produced, but the local image helper could not open them | UNVERIFIED |
| Console and hydration errors | Fresh CDP run returned no Runtime exceptions, console errors, deprecation warnings or page errors | PASS |

Captured files during the run: browser-smoke-initial.png, browser-smoke-media-final.png,
browser-smoke-microphone-final.png and browser-smoke-console-final.png
in the local checkout. They contain only mock/demo data and are local evidence artifacts.
