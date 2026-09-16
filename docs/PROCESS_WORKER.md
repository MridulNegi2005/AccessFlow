# Native perception lifecycle

The CLI's `--components local` profile now uses A's `ProcessPerception`. Text still
passes through B's LocalPerception in the parent. WAV and PNG requests run serially in
one persistent Python child, using B's LocalPerception unchanged. The JSONL protocol
carries typed input/observation envelopes, bounded frames and explicit completion.

Each replay owns its perception instance and invokes its optional `aclose()` hook after
controller shutdown, including when replay is canceled. Suite cases use fresh instances.
Cleanup failure is recorded as `perception_cleanup_error` and fails the task criteria;
a successful answer does not hide a failed cleanup. Traces record `perception_cleanup`.
Direct callers should use the adapter as an async context manager or call `aclose()` in
`finally`; `Agent` by itself does not own provider installation or the caller's lifecycle.

## Run it

```powershell
uv sync --frozen --extra dev
uv run accessflow suite scenarios/dev --components local --output-dir artifacts/process-profile
```

This text suite uses no subprocess or real model. For raw WAV, install the audio extra
and an explicitly downloaded Faster Whisper model before running an audio scenario:

```powershell
uv sync --frozen --extra dev --extra audio
uv run accessflow replay path/to/audio-scenario.json --components local --asr-model-path path/to/installed-model
```

No model download occurs in a scenario. The default worker has no configured vision
provider yet; PNG input fails visibly. A custom programmatic worker seam supports
protocol testing, and its fake observations remain labeled `fixture/native`.

## Boundaries and evidence

The adapter serializes native work, bounds execution, drains stderr and validates stdout
protocol frames. On timeout or cancellation it terminates the child and waits for its
exit, escalating to kill when necessary. A later request can create a replacement child;
closing the adapter permanently disallows new requests. Child startup and concurrent
shutdown require explicit handling so a late-created process cannot outlive close.

Tests use actual Python child processes and deliberately blocking fake providers. They
prove process-lifecycle behavior, not speech quality or live-model timing. Backend exception
text and stderr are not written to the evaluation trace. Python and native diagnostic
output must stay separate from the protocol.

One native request runs at a time. The controller cancels superseded revisions of the
same utterance, superseded image-frame workers and all perception workers on interruption;
it also cancels pending reasoning on interruption. The adapter's FIFO lock itself does
not coalesce arbitrary independent input streams. Source/revision checks still reject
late observations even if a callback resists cancellation. The controller inference
deadline includes time awaiting the adapter. Repeated cancellation can require
model reloads. Process startup and reload latency still need hardware measurement with
actual weights. This checkpoint does not certify official 120-second scenarios or the
300-second complete-model warm-up gate, nor does it terminate subprocess trees started by
an arbitrary third-party worker. The packaged local backend uses in-process native libraries
inside its one child. Hosted reasoning cancellation remains a separate HTTP-adapter path.

## Windows launch and regression evidence

Windows virtual-environment `python.exe` was observed to launch a second process: the
adapter's process PID differed from the PID written by the blocking worker. Terminating
the redirector alone therefore did not prove termination of native inference. The adapter
now starts the base interpreter directly on Windows, restoring the invoking environment's
import paths and prefixes. It uses CREATE_NO_WINDOW. The regression checks the worker's
own ready-file PID against the awaited process and requires an exit code after cancellation.
Other platforms retain the ordinary Python module launch.

A separate delayed-startup regression failed because a canceled startup task retained an
exited process and poisoned the next request. Cleanup now clears that completed startup
reference. Tests cover simultaneous close/startup and restart after cancellation.
The controller-to-process revision/interrupt tests also failed before controller worker
cancellation was connected. A callback that returns despite cancellation remains covered
by the older epoch-isolation tests, now explicitly cancellation-resistant.

Verification on Mridul's Windows Python 3.11 environment:

- `uv run --extra dev pytest -q` — 178 passed, two test-client deprecation warnings.
- `uv run --extra dev ruff check .` — passed.
- `uv build --out-dir artifacts/dist` — source distribution and wheel built.
- Fresh installed-wheel local-profile development suite — 4/4.
- Actual packaged child starts, returns typed missing-WAV failure and exits; no model invoked.
- Read-only OS process check after the tests found no matching test/native worker processes.

These are native process and packaging checks using synthetic providers, not a live ASR,
vision, reasoning or official-kit benchmark. Model warm-up/reload latency remains to measure.
