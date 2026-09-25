"""Bounded MP3 turn conversion; no transcription or turn-finality decisions.

The caller supplies only a completed turn's ordered, rooted references. The WAV
exists for the async context lifetime, so native ASR must finish before leaving it.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


MAX_CLIPS = 32
MAX_CLIP_BYTES = 8 * 1024 * 1024
MAX_TURN_BYTES = 16 * 1024 * 1024
MAX_SECONDS = 120
SAMPLE_RATE = 16000


class AudioDecodeError(ValueError):
    """Stable, content-free media failure at the conversion boundary."""


def admitted_paths(root, references):
    root = Path(root).resolve()
    if not root.is_dir() or not isinstance(references, (list, tuple)) or not 1 <= len(references) <= MAX_CLIPS:
        raise AudioDecodeError("Invalid MP3 turn boundary")
    paths = []
    for ref in references:
        if (not isinstance(ref, str) or not 1 <= len(ref) <= 1024 or "\x00" in ref or ":" in ref
                or Path(ref).is_absolute()):
            raise AudioDecodeError("Invalid MP3 reference")
        try:
            path = (root / ref).resolve()
            if not path.is_relative_to(root) or path.suffix.lower() != ".mp3" or not path.is_file():
                raise AudioDecodeError("MP3 reference is missing or outside its boundary")
        except (OSError, RuntimeError) as exc:
            raise AudioDecodeError("MP3 reference cannot be resolved") from exc
        paths.append(path)
    return paths


@dataclass(frozen=True)
class DecodedTurn:
    path: Path
    sample_rate: int
    frames: int
    clip_frames: tuple[int, ...]

    @property
    def duration_s(self):
        return self.frames / self.sample_rate


def _command(arguments):
    module = "accessflow.adapters.mp3_decode_worker"
    if os.name == "nt" and sys.prefix != sys.base_prefix:
        # Launch the real interpreter, not the Windows venv redirector: killing
        # this PID must stop decoding, rather than orphan its child interpreter.
        bootstrap = ("import json,runpy,sys; c=json.loads(sys.argv[1]); sys.path[:]=c['path']; "
                     "sys.prefix=c['prefix']; sys.exec_prefix=c['exec_prefix']; "
                     "sys.argv=sys.argv[2:]; runpy.run_module(sys.argv[0],run_name='__main__')")
        config = json.dumps({"path": [os.getcwd(), *sys.path], "prefix": sys.prefix,
                             "exec_prefix": sys.exec_prefix})
        return [sys._base_executable, "-c", bootstrap, config, module, *arguments]
    return [sys.executable, "-m", module, *arguments]


async def _reap(startup, process):
    if process is None:
        try:
            process = await startup
        except Exception:
            return
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await asyncio.wait_for(process.wait(), 2)


@asynccontextmanager
async def decode_mp3_turn(root, references, *, timeout_s=10):
    """Convert clips in an isolated process, stop it on cancellation, remove output.

    No organizer duration or text annotation is consumed. Returned duration is
    decoded media duration, not a calibrated speech endpoint or wall-clock label.
    """
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or not 0 < timeout_s <= 30:
        raise ValueError("MP3 decode timeout must be finite and within (0,30]")
    paths = admitted_paths(root, references)
    with tempfile.TemporaryDirectory(prefix="accessflow-mp3-") as temporary:
        folder = Path(temporary)
        request = folder / "request.json"
        request.write_text(json.dumps({"root": str(Path(root).resolve()), "references": list(references)}), encoding="utf-8")
        kwargs = {"stdin": asyncio.subprocess.DEVNULL, "stdout": asyncio.subprocess.DEVNULL,
                  "stderr": asyncio.subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        startup = asyncio.create_task(asyncio.create_subprocess_exec(*_command([str(request)]), **kwargs))
        process = None
        try:
            async with asyncio.timeout(timeout_s):
                process = await asyncio.shield(startup)
                code = await process.wait()
                if code != 0:
                    raise AudioDecodeError("MP3 worker could not decode the turn")
                result_path = folder / "result.json"
                if not result_path.is_file() or result_path.stat().st_size > 4096:
                    raise AudioDecodeError("MP3 worker returned invalid metadata")
                result = json.loads(result_path.read_text(encoding="utf-8"))
                samples = result.get("clip_frames") if isinstance(result, dict) else None
                if (not isinstance(samples, list) or len(samples) != len(paths)
                        or any(type(n) is not int or n <= 0 for n in samples)
                        or sum(samples) > SAMPLE_RATE * MAX_SECONDS):
                    raise AudioDecodeError("MP3 worker returned invalid sample counts")
                wav = folder / "turn.wav"
                if not wav.is_file() or wav.stat().st_size != 44 + 2 * sum(samples):
                    raise AudioDecodeError("MP3 worker returned invalid WAV size")
            yield DecodedTurn(wav, SAMPLE_RATE, sum(samples), tuple(samples))
        finally:
            # Complete a shielded spawn even if cancellation arrived during OS
            # process creation; then kill/reap that exact process before cleanup.
            # A separate cleanup task retains ownership through repeated caller
            # cancellations. Report cancellation only after it has reaped the PID.
            cleanup = asyncio.create_task(_reap(startup, process))
            cancelled = False
            while True:
                try:
                    await asyncio.shield(cleanup)
                    break
                except asyncio.CancelledError:
                    if cleanup.cancelled():
                        raise  # Global shutdown must not spin on a cancelled cleanup task.
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError
