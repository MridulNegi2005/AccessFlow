"""Real format conversion plus deterministic native-process lifecycle regressions."""

import asyncio
import json
from pathlib import Path
import sys
import wave

import pytest

from accessflow.adapters import mp3_decode as decoder
from accessflow.adapters import mp3_decode_worker as worker


@pytest.fixture
def clips(tmp_path):
    av = pytest.importorskip("av")
    import numpy as np
    refs = []
    for index, rate in enumerate((22050, 44100)):
        path = tmp_path / f"clip{index}.mp3"
        refs.append(path.name)
        # Format test signal only, not a recording or speech evaluation fixture.
        with av.open(str(path), mode="w", format="mp3") as container:
            stream = container.add_stream("libmp3lame", rate=rate)
            stream.layout = "mono"
            samples = np.sin(2 * np.pi * (440 + 110 * index) * np.arange(rate // 5) / rate).astype("float32") * 0.1
            frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="fltp", layout="mono")
            frame.sample_rate = rate
            for packet in stream.encode(frame):
                container.mux(packet)
            for packet in stream.encode(None):
                container.mux(packet)
    return refs


async def pcm(root, refs):
    async with decoder.decode_mp3_turn(root, refs) as result:
        with wave.open(str(result.path), "rb") as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 16000)
            assert wav.getnframes() == result.frames
            raw = wav.readframes(wav.getnframes())
        return raw, result


async def test_actual_mp3_clips_preserve_order_and_resample_to_valid_pcm(tmp_path, clips):
    first, one = await pcm(tmp_path, clips[:1])
    second, two = await pcm(tmp_path, clips[1:])
    combined, result = await pcm(tmp_path, clips)
    assert combined == first + second
    assert result.clip_frames == (one.frames, two.frames)
    assert result.frames == one.frames + two.frames
    assert result.duration_s == result.frames / 16000
    assert not result.path.exists()


@pytest.mark.parametrize("refs", [[], ["../escape.mp3"], ["C:/escape.mp3"], ["https://example.test/a.mp3"],
                                ["bad.wav"], ["missing.mp3"], ["nul\x00.mp3"], ["missing.mp3"] * 33])
async def test_bad_references_never_spawn(tmp_path, monkeypatch, refs):
    calls = []

    async def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("must validate before spawning")

    monkeypatch.setattr(decoder.asyncio, "create_subprocess_exec", forbidden)
    with pytest.raises(decoder.AudioDecodeError):
        async with decoder.decode_mp3_turn(tmp_path, refs):
            pytest.fail("invalid input admitted")
    assert not calls


async def test_corrupt_mp3_fails_and_does_not_yield_wav(tmp_path):
    (tmp_path / "bad.mp3").write_bytes(b"not audio")
    with pytest.raises(decoder.AudioDecodeError, match="could not decode"):
        async with decoder.decode_mp3_turn(tmp_path, ["bad.mp3"]):
            pytest.fail("corrupt input admitted")


@pytest.mark.parametrize("timeout", [0, -1, 31, float("nan"), True, "10"])
async def test_invalid_deadline_rejected(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout"):
        async with decoder.decode_mp3_turn(tmp_path, [], timeout_s=timeout):
            pass


@pytest.mark.parametrize("bound", ["MAX_CLIP_BYTES", "MAX_TURN_BYTES", "MAX_SECONDS"])
def test_worker_enforces_encoded_and_decoded_limits(tmp_path, clips, monkeypatch, bound):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"root": str(tmp_path), "references": clips}))
    monkeypatch.setattr(worker, bound, 1 if bound != "MAX_SECONDS" else 0.01)
    with pytest.raises(decoder.AudioDecodeError, match="bound"):
        worker.convert(request)
    assert not (tmp_path / "result.json").exists()


def test_worker_never_overwrites_existing_output(tmp_path, clips):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"root": str(tmp_path), "references": clips}))
    (tmp_path / "turn.wav").write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        worker.convert(request)
    assert (tmp_path / "turn.wav").read_bytes() == b"keep"


@pytest.mark.parametrize("stop", ["cancel", "timeout", "during_spawn", "during_spawn_twice"])
async def test_stop_reaps_exact_worker_and_removes_temporary_directory(tmp_path, monkeypatch, stop):
    (tmp_path / "clip.mp3").write_bytes(b"process fixture bypasses codec")
    spawn_entered = asyncio.Event()
    release_spawn = asyncio.Event()
    original_spawn = asyncio.create_subprocess_exec
    processes = []
    temporary = []

    def command(arguments):
        temporary.append(Path(arguments[0]).parent)
        return [sys._base_executable, "-c", "import time; time.sleep(60)"]

    async def spawn(*args, **kwargs):
        spawn_entered.set()
        if stop.startswith("during_spawn"):
            await release_spawn.wait()
        process = await original_spawn(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(decoder, "_command", command)
    monkeypatch.setattr(decoder.asyncio, "create_subprocess_exec", spawn)

    async def convert():
        async with decoder.decode_mp3_turn(tmp_path, ["clip.mp3"], timeout_s=0.15 if stop == "timeout" else 10):
            pytest.fail("blocking fixture must never finish")

    task = asyncio.create_task(convert())
    try:
        await asyncio.wait_for(spawn_entered.wait(), 2)
        if stop != "timeout":
            task.cancel()
        if stop == "during_spawn_twice":
            await asyncio.sleep(0)  # Allow the first cancellation to enter cleanup.
            task.cancel()
            await asyncio.sleep(0)
        release_spawn.set()
        with pytest.raises(TimeoutError if stop == "timeout" else asyncio.CancelledError):
            await asyncio.wait_for(task, 4)
        assert len(processes) == 1 and processes[0].returncode is not None
        assert not temporary[0].exists()
    finally:
        release_spawn.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        # Even a broken parent must not leave this deliberate test worker behind.
        for _ in range(100):
            if processes:
                break
            await asyncio.sleep(0.01)
        for process in processes:
            if process.returncode is None:
                process.kill()
                await process.wait()
