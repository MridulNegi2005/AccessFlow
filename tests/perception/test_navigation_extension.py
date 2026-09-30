"""Navigation extension changes only a simulated per-room route."""

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


async def test_completed_spoken_request_changes_destination_through_controller():
    executor = NavigationExecutor()
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
