from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from accessflow.adapters.process_perception import ProcessPerception
from accessflow.contracts import Audio, AudioEvent, Frame, FrameEvent, Transcript, TranscriptEvent


WORKER = "tests.engine.worker_fixture"


def _audio(event_id: str = "audio") -> AudioEvent:
    return AudioEvent(
        session_id="s",
        event_id=event_id,
        payload=Audio(path="fixture.wav", utterance_id="u", revision=2, speech_start=1, speech_end=2),
    )


def _frame(event_id: str = "frame") -> FrameEvent:
    return FrameEvent(session_id="s", event_id=event_id, timestamp=4, payload=Frame(path="fixture.png", frame_id="f"))


async def _one(adapter: ProcessPerception, event):
    return [item async for item in adapter.observe(event)]


def _adapter(tmp_path: Path, **kwargs) -> ProcessPerception:
    model = tmp_path / "installed-model"
    model.mkdir()
    return ProcessPerception(model, worker_module=WORKER, **kwargs)


@pytest.mark.asyncio
async def test_text_uses_local_passthrough_without_child(tmp_path: Path):
    adapter = _adapter(tmp_path)
    try:
        event = TranscriptEvent(session_id="s", event_id="text", payload=Transcript(
            utterance_id="u", revision=3, text="hello", final=False,
        ))
        observations = await _one(adapter, event)
        assert observations[0].text == "hello"
        assert observations[0].backend == "local/text-pass-through"
        assert adapter.child_pid is None
    finally:
        await adapter.aclose()


@pytest.mark.asyncio
async def test_persistent_child_serializes_concurrent_requests_and_drains_stderr(tmp_path: Path):
    adapter = _adapter(tmp_path, worker_args=("--mode", "stderr"))
    try:
        first, second = await asyncio.gather(_one(adapter, _audio("a1")), _one(adapter, _audio("a2")))
        assert [items[0].event_id for items in (first, second)] == ["a1", "a2"]
        pid = adapter.child_pid
        assert pid is not None and adapter.child_alive
    finally:
        await adapter.aclose()


@pytest.mark.asyncio
async def test_timeout_terminates_worker_and_next_request_restarts(tmp_path: Path):
    adapter = _adapter(tmp_path, worker_args=("--mode", "block"), observation_timeout_s=2)
    try:
        with pytest.raises(TimeoutError, match="timed out"):
            await _one(adapter, _audio("block"))
        assert not adapter.child_alive
        result = await _one(adapter, _audio("after-timeout"))
        assert result[0].text == "fixture audio"
        assert adapter.child_alive
    finally:
        await adapter.aclose()


@pytest.mark.asyncio
async def test_cancel_terminates_worker_and_next_request_restarts(tmp_path: Path):
    ready = tmp_path / "entered-native-work"
    adapter = _adapter(tmp_path, worker_args=("--mode", "block", "--ready-file", str(ready)),
                       observation_timeout_s=10)
    try:
        pending = asyncio.create_task(_one(adapter, _audio("block")))
        async with asyncio.timeout(5):
            while not ready.exists():
                await asyncio.sleep(0.01)
        process = adapter._process
        assert int(ready.read_text()) == process.pid
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert not adapter.child_alive
        assert process.returncode is not None
        result = await _one(adapter, _audio("after-cancel"))
        assert result[0].event_id == "after-cancel"
    finally:
        await adapter.aclose()


@pytest.mark.parametrize("close_during_startup", [False, True])
async def test_delayed_process_startup_cannot_leak_or_poison_restart(tmp_path, monkeypatch, close_during_startup):
    real_spawn = asyncio.create_subprocess_exec
    spawned, release = asyncio.Event(), asyncio.Event()
    processes = []

    async def delayed_spawn(*args, **kwargs):
        process = await real_spawn(*args, **kwargs)
        processes.append(process)
        spawned.set()
        await release.wait()
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_spawn)
    adapter = _adapter(tmp_path)
    request = asyncio.create_task(_one(adapter, _audio()))
    try:
        await asyncio.wait_for(spawned.wait(), 5)
        request.cancel()
        close = asyncio.create_task(adapter.aclose()) if close_during_startup else None
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(request, 3)
        if close is not None:
            await asyncio.wait_for(close, 3)
        assert processes[0].returncode is not None
        assert not adapter.child_alive
        if not close_during_startup:
            result = await _one(adapter, _audio("restarted"))
            assert result[0].event_id == "restarted"
            assert len(processes) == 2
    finally:
        release.set()
        request.cancel()
        await asyncio.gather(request, return_exceptions=True)
        await adapter.aclose()


@pytest.mark.parametrize("mode", ["malformed", "oversized", "eof", "crash"])
@pytest.mark.asyncio
async def test_bad_worker_protocol_is_rejected(tmp_path: Path, mode: str):
    # Protocol rejection is the subject here, not cold-interpreter startup speed.
    adapter = _adapter(tmp_path, worker_args=("--mode", mode), observation_timeout_s=5)
    try:
        with pytest.raises(RuntimeError, match="worker"):
            await _one(adapter, _frame())
        assert not adapter.child_alive
    finally:
        await adapter.aclose()


@pytest.mark.asyncio
async def test_aclose_is_idempotent_and_leaves_no_child(tmp_path: Path):
    adapter = _adapter(tmp_path)
    await _one(adapter, _audio())
    pid = adapter.child_pid
    assert pid is not None
    await adapter.aclose()
    await adapter.aclose()
    assert adapter.child_pid is None
    assert not adapter.child_alive
    with pytest.raises(RuntimeError, match="closed"):
        await _one(adapter, _audio("closed"))


async def test_native_and_python_stdout_do_not_corrupt_the_protocol(tmp_path):
    adapter = _adapter(tmp_path, worker_args=("--mode", "native_stdout"))
    async with adapter:
        result = await _one(adapter, _audio())
        assert result[0].backend == "fixture/native"


async def test_packaged_worker_starts_and_reports_media_failure_without_inference(tmp_path):
    # Uses the actual worker module and installed dependency paths; nonexistent WAV
    # fails validation before optional ASR import or any model inference.
    adapter = ProcessPerception(model_path=tmp_path)
    event = _audio()
    event.payload.path = str(tmp_path / "missing.wav")
    async with adapter:
        with pytest.raises(RuntimeError, match="backend failure"):
            await _one(adapter, event)
        assert not adapter.child_alive
