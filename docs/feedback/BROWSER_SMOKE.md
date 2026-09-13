# Browser smoke evidence

Date and branch: 2026-09-13 / atishay/perception

Status: IN PROGRESS

The functional browser smoke passed in a temporary isolated Chrome session. Pixel-level
inspection remains unavailable in this environment because the image inspection helper failed
to open the captured PNG. Physical microphone permission and device capture were not exercised.

## Runtime

- Browser: Chrome 152.0.7977.84, headless mode through Chrome DevTools Protocol
- Route: http://127.0.0.1:8000/
- Rendered inner viewport: 756 x 900; document scroll width: 741
- Backend label: demo/mock
- Local-only runtime addition: websockets 17.1 in the ignored development environment
- Microphone run: Chrome fake UI and fake audio device flags; no person or physical recording
- No committed pyproject or lockfile change; add a WebSocket runtime dependency through the
  shared owner before relying on Uvicorn for a fresh browser setup.

## Requirement matrix

| State | Evidence | Result |
|---|---|---|
| First paint and page identity | Chrome DOM: title AccessFlow mock demo and demo/mock label | PASS |
| WebSocket connection | Chrome event stream included connected and perception_backend statuses | PASS |
| Text submission | Chrome event stream included acknowledge and informational final for Book Wednesday | PASS |
| WAV file control | Chrome selected the checked-in synthetic tone and observed media_received=audio and a mock audio final | PASS |
| Microphone control | Chrome fake device entered recording state, stopped, uploaded a WAV and observed media_received=audio plus a mock final | PASS |
| PNG file control | Chrome selected a session PNG and observed media_received=frame; paired transcript produced its final | PASS |
| Layout overflow | body scroll width 741 was below inner viewport width 756 | PASS |
| Physical microphone permission and capture | No physical device was used in headless Chrome | UNVERIFIED |
| Visual pixel inspection | Captures were produced, but the local image helper could not open them | UNVERIFIED |
| Console and hydration errors | No separate console capture was available in this run | UNVERIFIED |

Captured files during the run: browser-smoke-initial.png, browser-smoke-media-final.png and
browser-smoke-microphone-final.png
in the local checkout. They contain only mock/demo data and are local evidence artifacts.