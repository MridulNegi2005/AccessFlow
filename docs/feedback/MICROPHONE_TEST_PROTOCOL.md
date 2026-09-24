# AccessFlow microphone check — user run sheet

This is a local, non-destructive speech-capture check. It is designed to verify
the real browser microphone path and, only when the page reports a real ASR
backend, transcription of a correction. It does not create a booking, reminder,
payment, or other external action.

## Before recording

1. Open the local AccessFlow page at `http://127.0.0.1:8000/` and start a fresh
   task/session if the page offers that control.
2. Read the backend/status label before speaking. Continue with the ASR check
   only if it says `local/Faster Whisper CPU INT8 audio` (or another explicitly
   configured real audio model). If it says `demo/mock audio` or `demo/mock`,
   stop here and report that exact label; a canned/mock answer is not a
   transcription result, and we should configure the local ASR server first.
3. Click the microphone control once. When the browser asks, allow microphone
   access for `127.0.0.1`. Wait until the page indicates recording has started
   (for example, a live timer or waveform). If it remains on “Waiting for
   microphone permission” or says recording has not started, stop and report
   the message; do not keep clicking.
4. The clip is sent to the local server when recording stops. Use only the
   harmless invented sentence below—no names, account details, or private
   calendar content.

## Read this exact script

Speak at a normal pace, with about a 1.5-second pause at the marked point:

> “Please read this draft meeting note back to me. The meeting is Tuesday at
> three p.m. [pause about one and a half seconds] Tuesday—actually, Wednesday
> at five p.m. Tell me only the final day and time.”

After “time,” wait about one second, then click the microphone control once to
stop. The current UI sends the completed WAV when capture stops; do not click
Run a second time for the same clip. Wait for the final response.

## What to record and send back

Please report these five observations (a screenshot is optional):

- The exact backend/status label shown before recording.
- Whether the browser permission prompt appeared and whether recording visibly
  started.
- The clip duration shown by the page, if available.
- The exact transcript if the UI shows one; otherwise the exact final answer.
- Whether an error, duplicate request, or unexpected extra submission appeared.

Expected ASR evidence is that both the initial Tuesday/3 p.m. and corrected
Wednesday/5 p.m. are represented in the recognized text when revisions are
shown, and that the final answer selects Wednesday at 5 p.m. The assistant must
not treat the note as authorization to perform a real action. If the backend
label is mock, or the final answer looks plausible but no transcript/backend
evidence is exposed, record it as capture/UI evidence only—not ASR success.

## Follow-up interruption check (separate run)

Do this only after reviewing the first clip. Use headphones to reduce speaker
echo. Start an answer's read-aloud playback, then start microphone capture and
say:

> “Stop speaking, please. Correction: make that six p.m.”

Note whether playback stops at speech onset, only after pressing the playback
Stop control, or not at all; then stop/send the microphone clip and report
whether the correction reached the page. The current browser path is
upload-on-stop, not continuous streaming, so a successful recording after the
output does **not** prove automatic barge-in. We will label button-driven stop
and speech-triggered interruption separately and will not claim the latter
works unless the observed output actually stops automatically and the new
correction reaches the agent.

## What happens after the report

We will first check the backend label and the raw observed result. If capture
fails, we will fix the owned browser permission/device/teardown path and repeat
only the failed stage. If capture succeeds but the label is mock, we will not
interpret the mock response as recognition; we will locate/configure the
installed ASR backend before asking for another speech run. If real ASR is
shown, we will compare the result with the script, preserve the timing and
transcript evidence, and fix any owned transcription/correction issue. Then we
will separately test output interruption and image understanding; the official
Samsung raw-media evaluation still requires the participant kit and Mridul's
common runtime/contract integration.
