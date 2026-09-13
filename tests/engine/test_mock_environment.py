import asyncio

from accessflow.clock import ManualClock
from accessflow.contracts import ToolCall, ToolManifest
from accessflow.evaluation.mock_environment import (
    LookupConfig, MockEnvironment, StatusConfig, WriteConfig,
)


def manifest(name, effect, properties, required=(), idempotency_parameter=None):
    return ToolManifest(name=name, description=name, effect=effect,
                        idempotency_parameter=idempotency_parameter,
                        parameters={"type": "object", "properties": properties,
                                    "required": list(required), "additionalProperties": False})


def call(tool, operation_id, arguments, effect):
    return ToolCall(call_id=f"call-{operation_id}-{tool}", operation_id=operation_id,
                    tool=tool, arguments=arguments, dependencies={}, effect=effect)


async def test_manifest_names_are_only_wired_by_explicit_bindings():
    search = manifest("calendar_query_v2", "read", {"day": {"type": "string"}})
    env = MockEnvironment([search], {"calendar_query_v2": LookupConfig(rows=[{"day": "Wed", "id": 7}])})

    result = await env.execute(call("calendar_query_v2", "query-1", {"day": "Wed"}, "read"))

    assert result.status == "success"
    assert result.result == {"rows": [{"day": "Wed", "id": 7}]}


async def test_renamed_operation_field_and_selected_identity_are_supported():
    write = manifest("reserve_v2", "write",
                     {"request_token": {"type": "string"}, "date": {"type": "string"},
                      "person": {"type": "string"}},
                     required=("request_token", "date", "person"), idempotency_parameter="request_token")
    env = MockEnvironment([write], {"reserve_v2": WriteConfig(
        operation_id_parameter="request_token", identity_fields=("date", "person"), mode="reservation")})

    result = await env.execute(call("reserve_v2", "op-1",
                                    {"request_token": "op-1", "date": "2026-09-20", "person": "M"}, "write"))

    assert result.status == "success"
    assert env.effects["op-1"]["arguments"]["request_token"] == "op-1"
    assert env.effects["op-1"]["arguments"]["person"] == "M"


async def test_same_operation_replays_effect_but_conflicting_args_do_not_mutate_ledger():
    write = manifest("reservation", "write", {"date": {"type": "string"}, "device": {"type": "string"}},
                     required=("date", "device"))
    env = MockEnvironment([write], {"reservation": WriteConfig(identity_fields=("date",))})
    first = await env.execute(call("reservation", "op-1", {"date": "Wed", "device": "A"}, "write"))
    replay = await env.execute(call("reservation", "op-1", {"date": "Wed", "device": "A"}, "write"))
    conflict = await env.execute(call("reservation", "op-1", {"date": "Wed", "device": "B"}, "write"))

    assert first.status == replay.status == "success"
    assert replay.committed is True
    assert conflict.status == "failed"
    assert conflict.error == "operation_identity_conflict"
    assert env.effects["op-1"]["arguments"]["date"] == "Wed"


async def test_argument_mapping_can_be_nested_for_renamed_operation_field():
    write = manifest("reserve", "write", {"request_key": {"type": "string"}, "date": {"type": "string"}},
                     required=("request_key", "date"))
    env = MockEnvironment([write], {"reserve": WriteConfig(
        argument_mapping={"operation_id": "request_key", "identity_fields": ["date"]})})

    result = await env.execute(call("reserve", "op-1", {"request_key": "op-1", "date": "Wed"}, "write"))

    assert result.status == "success"


async def test_failure_before_commit_has_no_effect_and_status_is_normalized():
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    status = manifest("check", "read", {"transaction": {"type": "string"}}, required=("transaction",))
    env = MockEnvironment([write, status], {
        "reserve": WriteConfig(fail_before_commit=True),
        "check": StatusConfig(operation_id_parameter="transaction"),
    })

    failed = await env.execute(call("reserve", "op-1", {"date": "Wed"}, "write"))
    observed = await env.execute(call("check", "status-1", {"transaction": "op-1"}, "read"))

    assert failed.status == "failed" and not failed.committed
    assert env.effects == {}
    assert observed.result == {"operation_id": "op-1", "outcome": "no_effect"}


async def test_commit_then_lost_response_keeps_effect_for_reconciliation():
    clock = ManualClock()
    write = manifest("book", "write", {"date": {"type": "string"}}, required=("date",))
    status = manifest("status_read", "read", {"op": {"type": "string"}}, required=("op",))
    env = MockEnvironment([write, status], {
        "book": WriteConfig(commit_then_unknown=True, response_delay_s=2),
        "status_read": StatusConfig(operation_id_parameter="op"),
    }, clock)
    task = asyncio.create_task(env.execute(call("book", "op-1", {"date": "Wed"}, "write")))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    clock.advance(0)
    await asyncio.sleep(0)
    assert env.effects["op-1"]["committed"] is True
    assert (await env.execute(call("status_read", "s-1", {"op": "op-1"}, "read"))).result == {
        "operation_id": "op-1", "outcome": "committed"
    }
    clock.advance(2)
    result = await task
    assert result.status == "unknown"


async def test_cancel_before_commit_is_only_reported_before_commit_and_does_not_write():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig(commit_delay_s=5)}, clock)
    task = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(4):
        await asyncio.sleep(0)
    assert await env.cancel("call-op-1-reserve") == "cancelled_before_commit"
    clock.advance(5)
    result = await task
    assert result.status == "cancelled"
    assert env.effects == {}


async def test_cancel_after_commit_reports_too_late_and_never_rolls_back():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig(response_delay_s=5)}, clock)
    task = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(4):
        await asyncio.sleep(0)
    assert env.effects["op-1"]["committed"] is True
    assert await env.cancel("call-op-1-reserve") == "too_late"
    clock.advance(5)
    assert (await task).status == "success"
    assert "op-1" in env.effects


async def test_cancelled_duplicate_waiter_does_not_cancel_shared_leader():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig(commit_delay_s=5) }, clock)
    leader = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(3):
        await asyncio.sleep(0)
    duplicate_call = call("reserve", "op-1", {"date": "Wed"}, "write")
    duplicate = asyncio.create_task(env.execute(duplicate_call))
    for _ in range(3):
        await asyncio.sleep(0)
    duplicate.cancel()
    try:
        await duplicate
    except asyncio.CancelledError:
        pass
    clock.advance(5)
    assert (await leader).status == "success"
    assert "op-1" in env.effects


async def test_cancelled_leader_cleans_pending_and_records_no_effect():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    status = manifest("inspect", "read", {"key": {"type": "string"}}, required=("key",))
    env = MockEnvironment([write, status], {
        "reserve": WriteConfig(commit_delay_s=5), "inspect": StatusConfig(operation_id_parameter="key")
    }, clock)
    leader = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(3):
        await asyncio.sleep(0)
    leader.cancel()
    try:
        await leader
    except asyncio.CancelledError:
        pass
    assert env.effects == {}
    observed = await env.execute(call("inspect", "s-1", {"key": "op-1"}, "read"))
    assert observed.result == {"operation_id": "op-1", "outcome": "no_effect"}


async def test_invalid_arguments_and_effect_are_rejected_before_binding_runs():
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig()})

    invalid = await env.execute(call("reserve", "op-1", {"date": 3}, "write"))
    mismatch = await env.execute(call("reserve", "op-2", {"date": "Wed"}, "read"))

    assert invalid.error == "invalid_tool_arguments"
    assert mismatch.error == "effect_mismatch"
    assert env.effects == {}


async def test_failed_attempt_then_successful_retry_reports_committed_status():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    status = manifest("inspect", "read", {"key": {"type": "string"}}, required=("key",))
    env = MockEnvironment([write, status], {
        "reserve": WriteConfig(fail_before_commit=True), "inspect": StatusConfig(operation_id_parameter="key")
    }, clock)
    assert (await env.execute(call("reserve", "op-1", {"date": "Wed"}, "write"))).status == "failed"
    # Change only the configured capability, retaining the operation identity.
    env.bindings["reserve"] = WriteConfig()
    assert (await env.execute(call("reserve", "op-1", {"date": "Wed"}, "write"))).status == "success"
    observed = await env.execute(call("inspect", "s-1", {"key": "op-1"}, "read"))
    assert observed.result == {"operation_id": "op-1", "outcome": "committed"}


async def test_cancelled_attempt_is_detached_for_immediate_same_operation_retry():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig(commit_delay_s=5)}, clock)

    cancelled = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(3):
        await asyncio.sleep(0)
    assert await env.cancel("call-op-1-reserve") == "cancelled_before_commit"

    retry_call = call("reserve", "op-1", {"date": "Wed"}, "write").model_copy(
        update={"call_id": "call-op-1-reserve-retry"})
    retry = asyncio.create_task(env.execute(retry_call))
    for _ in range(3):
        await asyncio.sleep(0)

    clock.advance(5)
    assert (await cancelled).status == "cancelled"
    assert (await retry).status == "success"
    assert env.effects["op-1"]["committed"] is True


async def test_late_cancelled_attempt_cleanup_cannot_remove_retry_or_clobber_status():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    status = manifest("inspect", "read", {"key": {"type": "string"}}, required=("key",))
    env = MockEnvironment([write, status], {
        "reserve": WriteConfig(commit_delay_s=10),
        "inspect": StatusConfig(operation_id_parameter="key"),
    }, clock)

    cancelled = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(3):
        await asyncio.sleep(0)
    assert await env.cancel("call-op-1-reserve") == "cancelled_before_commit"
    before_retry = await env.execute(call("inspect", "status-before", {"key": "op-1"}, "read"))
    assert before_retry.result == {"operation_id": "op-1", "outcome": "no_effect"}

    # A faster replacement commits while the canceled attempt is still
    # sleeping, so its late cleanup must preserve the committed retry.
    env.bindings["reserve"] = WriteConfig(commit_delay_s=5)
    retry_call = call("reserve", "op-1", {"date": "Wed"}, "write").model_copy(
        update={"call_id": "call-op-1-reserve-retry"})
    retry = asyncio.create_task(env.execute(retry_call))
    for _ in range(3):
        await asyncio.sleep(0)
    assert await env.cancel("call-op-1-reserve") == "cancelled_before_commit"
    while_retry_waits = await env.execute(call("inspect", "status-pending", {"key": "op-1"}, "read"))
    assert while_retry_waits.result == {"operation_id": "op-1", "outcome": "unknown"}

    clock.advance(5)
    assert (await retry).status == "success"
    assert env.effects["op-1"]["committed"] is True

    clock.advance(5)
    assert (await cancelled).status == "cancelled"
    assert env.effects["op-1"]["committed"] is True
    after_retry = await env.execute(call("inspect", "status-after", {"key": "op-1"}, "read"))
    assert after_retry.result == {"operation_id": "op-1", "outcome": "committed"}


async def test_conflicting_retry_does_not_detach_cancelled_attempt():
    clock = ManualClock()
    write = manifest("reserve", "write", {"date": {"type": "string"}}, required=("date",))
    env = MockEnvironment([write], {"reserve": WriteConfig(commit_delay_s=5)}, clock)

    cancelled = asyncio.create_task(env.execute(call("reserve", "op-1", {"date": "Wed"}, "write")))
    for _ in range(3):
        await asyncio.sleep(0)
    assert await env.cancel("call-op-1-reserve") == "cancelled_before_commit"

    conflict_call = call("reserve", "op-1", {"date": "Thu"}, "write").model_copy(
        update={"call_id": "call-op-1-reserve-conflict"})
    conflict = await env.execute(conflict_call)
    assert conflict.status == "failed"
    assert conflict.error == "operation_identity_conflict"

    retry_call = call("reserve", "op-1", {"date": "Wed"}, "write").model_copy(
        update={"call_id": "call-op-1-reserve-retry"})
    retry = asyncio.create_task(env.execute(retry_call))
    for _ in range(3):
        await asyncio.sleep(0)
    clock.advance(5)
    assert (await cancelled).status == "cancelled"
    assert (await retry).status == "success"


async def test_instances_do_not_share_effect_ledger():
    write = manifest("book", "write", {"date": {"type": "string"}}, required=("date",))
    first = MockEnvironment([write], {"book": WriteConfig()})
    second = MockEnvironment([write], {"book": WriteConfig()})
    await first.execute(call("book", "op-1", {"date": "Wed"}, "write"))

    assert first.effects and second.effects == {}
