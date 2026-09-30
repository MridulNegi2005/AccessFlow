"""Navigation extension changes only a simulated per-room route."""

import asyncio
import threading

import pytest

from accessflow.contracts import PlanProposal, ProposedCall, ToolCall
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FinalFlagPolicy, MockOnlyAuthorization, ScriptedReasoner
from accessflow.perception.fdb_v3.bridge import RoomBridge, spoken_results
from accessflow.perception.navigation import (NavigationExecutor, NavigationStateStore,
                                              navigation_manifests)


def call(call_id, operation_id, destination):
    return ToolCall(
        call_id=call_id, operation_id=operation_id, tool="set_navigation_destination",
        arguments={"destination": destination}, dependencies={},
        effect="write",
    )


async def test_destination_change_is_local_and_idempotent():
    first_room = NavigationExecutor()
    second_room = NavigationExecutor()

    changed = await first_room.execute(call("first", "operation-1", "City Hospital"))
    retry = await first_room.execute(call("retry", "operation-1", "City Hospital"))

    assert changed.status == retry.status == "success"
    assert changed.committed and retry.committed
    assert first_room.destination == "City Hospital"
    assert first_room.revision == 1
    assert second_room.destination == "Central Station"
    assert retry.result["previous_destination"] == "Central Station"


async def test_unknown_destination_and_conflicting_retry_do_not_change_route():
    executor = NavigationExecutor()

    failed = await executor.execute(call("unknown", "operation-1", "Somewhere"))
    assert failed.status == "failed"
    assert executor.destination == "Central Station"

    changed = await executor.execute(call("first", "operation-2", "City Hospital"))
    conflicting = await executor.execute(call("conflict", "operation-2", "Airport Terminal 1"))
    assert changed.status == "success"
    assert conflicting.status == "unknown"
    assert executor.destination == "City Hospital"
    assert executor.revision == 1


async def test_completed_spoken_request_changes_destination_through_controller(tmp_path):
    store = NavigationStateStore(tmp_path / "spoken-navigation.sqlite3")
    executor = NavigationExecutor(room_name="spoken-room", state_store=store)
    await executor.initialize()
    reasoner = ScriptedReasoner([
        PlanProposal(
            intent="change_destination", slot_updates={"destination": "City Hospital"},
            calls=[ProposedCall(
                tool="set_navigation_destination", arguments={"destination": "City Hospital"},
                dependencies=["destination"],
            )], request_complete=True, write_requested=True,
        ),
        PlanProposal(response="The simulated destination is now City Hospital.", request_complete=True),
    ])
    bridge = RoomBridge(
        "navigation-room",
        Agent(FakePerception(), FinalFlagPolicy(), reasoner, executor, MockOnlyAuthorization()),
        tool_manifests=navigation_manifests(),
    )
    await bridge.start()
    try:
        reply = await bridge.complete_turn("Change destination to City Hospital", timeout=5)
        assert "City Hospital" in reply
        assert executor.destination == "City Hospital"
        assert executor.revision == 1
        assert store.read("spoken-room")["destination"] == executor.destination
        assert executor.confirmed_results()[0][1]["destination"] == "City Hospital"
    finally:
        await bridge.close()


def test_confirmed_navigation_result_has_clear_spoken_acknowledgement():
    assert spoken_results([(
        "set_navigation_destination",
        {"status": "success", "destination": "Airport Terminal 1", "mode": "simulated_navigation"},
    )]) == "Simulated destination changed to Airport Terminal 1."


async def test_dashboard_projection_follows_confirmed_route_and_resets_each_room(tmp_path):
    store = NavigationStateStore(tmp_path / "navigation.sqlite3")
    first = NavigationExecutor(room_name="trip-1", state_store=store)
    await first.initialize()
    assert store.read("trip-1")["destination"] == "Central Station"

    assert (await first.execute(call("first", "operation-1", "Airport Terminal 1"))).status == "success"
    assert store.read("trip-1")["destination"] == "Airport Terminal 1"
    assert store.read("trip-1")["revision"] == 1

    second = NavigationExecutor(room_name="trip-2", state_store=store)
    await second.initialize()
    assert store.read("trip-2")["destination"] == "Central Station"
    assert store.read("trip-1")["destination"] == "Airport Terminal 1"

# ---------------------------------------------------------------------------
# B2 regression: navigation cancellation must be honest about DB commits
# ---------------------------------------------------------------------------

def _make_blocking_store(tmp_path, barrier_revision=1):
    """Return a store whose write() blocks until released for the given revision."""

    class BlockingStore(NavigationStateStore):
        def __init__(self):
            super().__init__(tmp_path / "nav_b2.sqlite3")
            self._barrier = threading.Event()
            self._entered = threading.Event()
            self._barrier_rev = barrier_revision

        def write(self, room_name, destination, revision):
            if revision == self._barrier_rev:
                self._entered.set()
                self._barrier.wait()
            super().write(room_name, destination, revision)

        def release(self):
            self._barrier.set()

    return BlockingStore()


async def test_b2_cancel_inside_persistence_returns_unknown_not_false_claim(tmp_path):
    """B2: cancelling the execute coroutine while the DB thread is blocked must
    return 'unknown', not the false 'cancelled_before_commit'."""
    store = _make_blocking_store(tmp_path)
    executor = NavigationExecutor(room_name="b2-room", state_store=store)
    await executor.initialize()

    cid = "call-b2"
    op_id = "operation-b2"
    c = call(cid, op_id, "Airport Terminal 1")

    # Start execute; it will block inside the DB thread at revision 1.
    task = asyncio.create_task(executor.execute(c))
    # Wait until the thread has entered write()
    try:
        assert await asyncio.to_thread(store._entered.wait, 5)

        # Cancel the coroutine. The shielded operation and native DB thread continue.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert await executor.cancel(cid) == "unknown"
    finally:
        store.release()
    assert await executor.drain() == ()

    # The database, executor, and operation ledger must reconcile to the same commit.
    db_state = store.read("b2-room")
    assert db_state is not None
    assert db_state["destination"] == "Airport Terminal 1"
    assert db_state["revision"] == 1
    assert (executor.destination, executor.revision) == (db_state["destination"], 1)
    assert executor.confirmed_results()[0][1]["destination"] == db_state["destination"]


async def test_b2_cancel_before_dispatch_is_genuinely_cancelled(tmp_path):
    """B2: cancelling before the write is dispatched is a real pre-commit cancel."""
    store = _make_blocking_store(tmp_path, barrier_revision=999)  # barrier never fires
    executor = NavigationExecutor(room_name="b2-early", state_store=store)
    await executor.initialize()

    cid = "call-early"
    # A cancellation with no registered operation is known to precede dispatch.
    assert await executor.cancel(cid) == "cancelled_before_commit"
    result = await executor.execute(call(cid, "op-early", "Airport Terminal 1"))
    assert result.status == "cancelled"
    assert executor.destination == "Central Station"


async def test_b2_same_operation_retry_does_not_double_effect(tmp_path):
    """B2: Retrying with the same operation_id must not produce a second DB write."""
    store = NavigationStateStore(tmp_path / "nav_retry.sqlite3")
    executor = NavigationExecutor(room_name="retry-room", state_store=store)
    await executor.initialize()

    c = call("call-1", "op-r", "Airport Terminal 1")
    first = await executor.execute(c)
    await executor.drain()
    assert first.status == "success" and first.committed

    retry = await executor.execute(call("call-1b", "op-r", "Airport Terminal 1"))
    await executor.drain()
    # Same operation_id: idempotent
    assert retry.status == "success" and retry.committed
    # Revision should still be 1 (not 2)
    assert executor.revision == store.read("retry-room")["revision"] == 1


async def test_b2_conflicting_retry_is_rejected(tmp_path):
    """B2: A different destination under the same operation_id is rejected as unknown."""
    store = NavigationStateStore(tmp_path / "nav_conflict.sqlite3")
    executor = NavigationExecutor(room_name="conflict-room", state_store=store)
    await executor.initialize()

    await executor.execute(call("call-a", "op-c", "City Hospital"))
    await executor.drain()

    conflict = await executor.execute(call("call-b", "op-c", "Airport Terminal 1"))
    assert conflict.status == "unknown"
    assert conflict.error == "operation_conflict"


async def test_b2_new_correction_while_old_write_finishing_takes_latest(tmp_path):
    """B2: A later correction must win over an in-flight old write."""
    store = _make_blocking_store(tmp_path)

    class ObservableExecutor(NavigationExecutor):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.new_write_queued = asyncio.Event()

        async def _persist_destination(self, call_id, operation_id, destination,
                                       previous, revision):
            if operation_id == "op-new":
                self.new_write_queued.set()
            return await super()._persist_destination(
                call_id, operation_id, destination, previous, revision)

    executor = ObservableExecutor(room_name="correction-room", state_store=store)
    await executor.initialize()

    # Start old write: Airport Terminal 1 (revision 1), blocked in DB thread
    old_task = asyncio.create_task(executor.execute(call("old-call", "op-old", "Airport Terminal 1")))
    try:
        assert await asyncio.to_thread(store._entered.wait, 5)
        # This distinct user correction queues revision 2 behind the blocked write.
        new_task = asyncio.create_task(
            executor.execute(call("new-call", "op-new", "City Hospital")))
        await executor.new_write_queued.wait()
    finally:
        store.release()
    old_result, new_result = await asyncio.gather(old_task, new_task)
    assert old_result.status == new_result.status == "success"
    assert old_result.result["revision"] == 1
    assert new_result.result["revision"] == 2
    assert await executor.drain() == ()

    # Executor destination must be City Hospital (latest confirmed)
    assert executor.destination == "City Hospital"
    db = store.read("correction-room")
    assert db["destination"] == "City Hospital"


async def test_b2_shutdown_drain_with_pending_work(tmp_path):
    """B2: drain() on shutdown must reconcile all in-flight writes honestly."""
    store = _make_blocking_store(tmp_path)
    executor = NavigationExecutor(room_name="drain-room", state_store=store)
    await executor.initialize()

    task = asyncio.create_task(executor.execute(call("drain-call", "op-drain", "Airport Terminal 1")))
    try:
        assert await asyncio.to_thread(store._entered.wait, 5)
        assert await executor.drain(timeout=0.01) == ("op-drain",)
    finally:
        store.release()
    result = await task
    assert result.status == "success"
    assert await executor.drain() == ()

    db = store.read("drain-room")
    assert db["destination"] == "Airport Terminal 1"
    assert db["revision"] == 1


async def test_b2_second_room_gets_isolated_state(tmp_path):
    """B2: A fresh room must start from Central Station, not inherit a prior room's state."""
    store = NavigationStateStore(tmp_path / "nav_iso.sqlite3")
    first = NavigationExecutor(room_name="room-x", state_store=store)
    await first.initialize()
    await first.execute(call("c1", "op1", "City Hospital"))
    await first.drain()

    second = NavigationExecutor(room_name="room-y", state_store=store)
    await second.initialize()
    assert second.destination == "Central Station"
    assert second.revision == 0
    db = store.read("room-y")
    assert db["destination"] == "Central Station"


async def test_b2_cancel_after_commit_is_not_reported_as_precommit(tmp_path):
    store = NavigationStateStore(tmp_path / "nav_after_commit.sqlite3")
    executor = NavigationExecutor(room_name="after-commit", state_store=store)
    await executor.initialize()
    result = await executor.execute(call("committed-call", "committed-op", "City Hospital"))
    assert result.status == "success" and result.committed
    assert await executor.cancel("committed-call") == "unknown"
    assert store.read("after-commit")["destination"] == "City Hospital"


async def test_b2_write_failure_is_reported_without_claiming_a_commit(tmp_path):
    class FailingStore(NavigationStateStore):
        def write(self, room_name, destination, revision):
            if revision > 0:
                raise OSError("simulated persistence failure")
            return super().write(room_name, destination, revision)

    store = FailingStore(tmp_path / "nav_failure.sqlite3")
    executor = NavigationExecutor(room_name="failure-room", state_store=store)
    await executor.initialize()
    result = await executor.execute(call("failure-call", "failure-op", "Airport Terminal 1"))
    assert result.status == "failed"
    assert not result.committed
    assert executor.destination == store.read("failure-room")["destination"] == "Central Station"
    assert executor.confirmed_results() == []


async def test_b2_commit_followed_by_store_error_is_reconciled_from_database(tmp_path):
    class CommitThenErrorStore(NavigationStateStore):
        def write(self, room_name, destination, revision):
            applied = super().write(room_name, destination, revision)
            if revision > 0:
                raise OSError("simulated lost acknowledgment after commit")
            return applied

    store = CommitThenErrorStore(tmp_path / "nav_uncertain.sqlite3")
    executor = NavigationExecutor(room_name="uncertain-room", state_store=store)
    await executor.initialize()
    result = await executor.execute(call("uncertain-call", "uncertain-op", "Airport Terminal 1"))
    db = store.read("uncertain-room")
    assert result.status == "success" and result.committed
    assert db["destination"] == executor.destination == "Airport Terminal 1"
    assert db["revision"] == executor.revision == 1
    assert executor.confirmed_results()[0][1]["destination"] == db["destination"]


async def test_b2_confirmed_commit_survives_followup_read_failure(tmp_path):
    class ReadFailsOnceStore(NavigationStateStore):
        def __init__(self, path):
            super().__init__(path)
            self.fail_next_read = False

        def write(self, room_name, destination, revision):
            applied = super().write(room_name, destination, revision)
            if revision > 0:
                self.fail_next_read = True
            return applied

        def read(self, room_name):
            if self.fail_next_read:
                self.fail_next_read = False
                raise OSError("simulated dashboard read failure")
            return super().read(room_name)

    store = ReadFailsOnceStore(tmp_path / "nav_read_failure.sqlite3")
    executor = NavigationExecutor(room_name="read-failure-room", state_store=store)
    await executor.initialize()
    result = await executor.execute(call("read-failure-call", "read-failure-op", "City Hospital"))
    actual = NavigationStateStore(store.path).read("read-failure-room")
    assert result.status == "success" and result.committed
    assert (executor.destination, executor.revision) == ("City Hospital", 1)
    assert actual["destination"] == executor.destination
    assert executor.confirmed_results()[0][1]["destination"] == actual["destination"]
