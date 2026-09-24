# AccessFlow microphone check — user run sheet

This is a local, non-destructive speech-capture check. It is designed to verify
the real browser microphone path and, only when the page reports a real ASR
backend, transcription of a correction. It does not create a booking, reminder,
payment, or other external action.

## Before recording

1. Open the configured local ASR page. In the current test setup it is
   `http://127.0.0.1:8001/`; port `8000` may be the mock-only instance. Start a
   fresh task/session if the page offers that control.
2. Confirm the perception label names a real audio backend, such as
   `local/Faster Whisper CPU INT8 audio`. The reasoner may still be
   `demo/mock-reasoner`: that is acceptable for checking capture and
   transcription, but cannot prove the agent understood or acted on the
   request. If perception says `demo/mock audio`, do not count the run as ASR.
3. Click the microphone control once. When the browser asks, allow microphone
   access for `127.0.0.1`. Wait until the page indicates recording has started
   (for example, a live timer or waveform). If it remains on “Waiting for
   microphone permission” or says recording has not started, stop and report
   the message; do not keep clicking.
4. The clip is sent to the local server when recording stops. Use only the
   harmless invented sentence below—no names, account details, or private
   calendar content.

## Read this exact script

Speak at a normal pace, with about a two-second pause at the marked point:

> “Set a reminder for Tuesday at 3. [pause about two seconds] Actually,
> Wednesday at 5. Tell me only the final time.”

After “time,” wait about one second, then click the microphone control once to
stop. The current UI sends the completed WAV when capture stops; do not click
Run a second time for the same clip. Wait for the final response.

## What to do after speaking

After the page finishes, just tell the reviewer **“done.”** The reviewer checks
the visible page and available server output; you do not need to read or report
backend labels, durations, or statuses. If the reviewer cannot see the result,
send a screenshot. The local Uvicorn log records page/WebSocket connections,
not audio bytes or transcripts, so a connection line alone is not proof of ASR.

Expected ASR evidence is that the displayed recognized text preserves both the
initial Tuesday/3 p.m. and corrected Wednesday/5 p.m. The current mock reasoner
may simply echo the transcript; that does not test reasoning or prove that a
reminder was created. Never treat this harmless note as authorization for a
real action. Record capture, ASR, reasoning and action evidence separately.

## Follow-up interruption check (separate run)

This is a later engineering acceptance test, not a required user action while
the page still uploads only after Stop. Once ongoing capture is implemented,
review the first clip, use headphones to reduce speaker echo, start an answer's
read-aloud playback, then start microphone capture and
say:

> “Stop speaking, please. Correction: make that six p.m.”

The acceptance run must establish that playback stops at speech onset, new
speech reaches the agent, and no stale action wins. Button-driven Stop and
speech-triggered interruption are separate outcomes; do not claim automatic
barge-in from a successful upload after output finishes.

## What happens after the report

The reviewer first checks the perception label and displayed transcript. If
capture fails, fix the owned browser permission/device/teardown path and repeat
only that stage. If perception is mock, do not count it as ASR. If real ASR is
shown, compare the recognized words with the script and record timing or
correction errors. Test reasoning/action behavior separately; the official
Samsung raw-media evaluation still requires the participant kit and Mridul's
common runtime/contract integration.
