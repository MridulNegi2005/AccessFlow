"""FDB-v3 tool boundary: real registry calls stay isolated and observable."""

import asyncio
import json

import pytest
from pydantic import ValidationError

from accessflow.contracts import ResultBinding, ToolCall
from accessflow.perception.fdb_v3 import tools


class Registry:
    FUNCTIONS = {"book_flight": object(), "track_order": object()}

    def __init__(self):
        self.calls = []

    def call(self, name, **arguments):
        self.calls.append((name, arguments))
        return {"status": "success", "value": name}


def _call(call_id, operation_id, *, tool="book_flight", arguments=None, effect="write"):
    return ToolCall(call_id=call_id, operation_id=operation_id, tool=tool,
                    arguments=arguments or {"passenger_name": "A"},
                    dependencies={}, effect=effect)


async def test_same_operation_executes_once_and_records_one_room_scoped_call(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "validate_official_registry", lambda registry: None)
    registry = Registry()
    path = tmp_path / "agent_tool_calls.log"
    executor = tools.FDBMockExecutor(registry, "eval-room", telemetry_path=path)

    first, retry = await asyncio.gather(
        executor.execute(_call("first", "same-operation")),
        executor.execute(_call("retry", "same-operation")),
    )

    assert first.status == retry.status == "success"
    assert first.committed and retry.committed
    assert registry.calls == [("book_flight", {"passenger_name": "A"})]
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["room"] == "eval-room"
    assert records[0]["call"]["function"] == "book_flight"
    assert records[0]["call"]["args"] == {"passenger_name": "A"}
    assert records[0]["call"]["timestamp_end"] >= records[0]["call"]["timestamp_start"]


async def test_conflicting_or_cancelled_operation_never_invokes_mock_tool(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "validate_official_registry", lambda registry: None)
    registry = Registry()
    executor = tools.FDBMockExecutor(registry, "eval-room", telemetry_path=tmp_path / "calls")

    assert (await executor.execute(_call("first", "operation"))).status == "success"
    conflict = await executor.execute(_call("changed", "operation", arguments={"passenger_name": "B"}))
    assert conflict.status == "unknown"
    assert conflict.error == "operation_conflict"

    assert await executor.cancel("cancelled-before-start") == "cancelled_before_commit"
    cancelled = await executor.execute(_call("cancelled-before-start", "other-operation"))
    assert cancelled.status == "cancelled"
    assert len(registry.calls) == 1


async def test_drain_waits_for_concurrent_mock_call_telemetry(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "validate_official_registry", lambda registry: None)

    class DelayedRegistry(Registry):
        def call(self, name, **arguments):
            import time
            if name == "track_order":
                time.sleep(0.05)
            return super().call(name, **arguments)

    registry = DelayedRegistry()
    path = tmp_path / "calls"
    executor = tools.FDBMockExecutor(registry, "eval-room", telemetry_path=path)
    slow = asyncio.create_task(executor.execute(_call(
        "read", "read-operation", tool="track_order", arguments={"order_id": "O1"},
        effect="read")))
    fast = asyncio.create_task(executor.execute(_call(
        "write", "write-operation")))
    await asyncio.sleep(0)

    assert (await fast).status == "success"
    await executor.drain()
    assert (await slow).status == "success"
    names = [json.loads(line)["call"]["function"] for line in path.read_text().splitlines()]
    assert set(names) == {"book_flight", "track_order"}


async def test_parallel_calls_keep_every_jsonl_record_intact(monkeypatch, tmp_path):
    monkeypatch.setattr(tools, "validate_official_registry", lambda registry: None)
    path = tmp_path / "calls"
    executor = tools.FDBMockExecutor(Registry(), "eval-room", telemetry_path=path)
    calls = [_call(f"call-{number}", f"operation-{number}", tool="track_order",
                   arguments={"order_id": str(number)}, effect="read")
             for number in range(20)]

    results = await asyncio.gather(*(executor.execute(call) for call in calls))

    assert all(result.status == "success" for result in results)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(records) == 20
    assert {record["call"]["args"]["order_id"] for record in records} == {
        str(number) for number in range(20)}


def test_manifest_set_and_required_fields_match_declared_fdb_interface():
    declared = {manifest.name: manifest for manifest in tools.manifests()}
    assert len(declared) == 12
    assert declared["book_flight"].effect == "write"
    assert declared["track_order"].effect == "read"
    assert declared["add_to_cart"].parameters["required"] == ["product_id", "quantity"]


def test_current_contract_cannot_bind_a_single_unmatched_search_result():
    # A read can return one product, but a user asking for "the cheapest" has no
    # product field to match before that read. The A-owned contract requires one.
    with pytest.raises(ValidationError):
        ResultBinding(
            slot="product_id", source_call_index=0,
            collection_pointer="/products", value_pointer="/product_id",
            match_slots={},
        )
