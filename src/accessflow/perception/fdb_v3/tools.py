"""FDB-v3 mock-tool bridge. The official benchmark remains the tool authority."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from accessflow.contracts import ToolManifest, ToolResult


_PROCESS_TELEMETRY_LOCK = threading.Lock()


# These are interface shapes and short task descriptions, not benchmark answers.
# The runtime checks them against the official mock_apis.py before a room starts.
_TOOLS = (
    ("search_flights", "read", "Find flights for a destination and date. Preserve the stated month and day without adding a year; write a spoken ordinal day as a plain number (for example, March 2nd becomes March 2). Returns /flights rows with /flight_id, /destination, and /date; a uniquely matching row can supply a requested booking.",
     {"destination": "string", "date": "string"}, ("destination", "date")),
    ("book_flight", "write", "Book a flight for a passenger. Use the flight_id from a uniquely matching search_flights row when the user requested booking.",
     {"passenger_name": "string", "flight_id": "string"}, ("passenger_name",)),
    ("update_identity_doc", "write", "Update an identity document.",
     {"doc_type": "string", "doc_number": "string"}, ("doc_type", "doc_number")),
    ("get_card_benefits", "read", "Look up benefits for a card type.",
     {"card_type": "string"}, ("card_type",)),
    ("get_exchange_rate", "read", "Get a currency conversion rate and amount.",
     {"amount": "number", "from_currency": "string", "to_currency": "string"},
     ("amount", "from_currency", "to_currency")),
    ("modify_autopay", "write", "Change the source account for automatic bill payment. bill_type is a concise lowercase snake_case bill category; use underscores between category words and omit action words such as autopay.",
     {"bill_type": "string", "source_account": "string"}, ("bill_type", "source_account")),
    ("search_apartments", "read", "Find apartments that match location and budget.",
     {"city": "string", "bedrooms": "integer", "max_price": "number"},
     ("city", "bedrooms", "max_price")),
    ("calculate_commute", "read", "Calculate travel time between two addresses.",
     {"origin_address": "string", "destination_address": "string", "mode": "string"},
     ("origin_address", "destination_address")),
    ("update_search_filter", "write", "Update an apartment search filter.",
     {"filter_name": "string", "value": None}, ("filter_name", "value")),
    ("track_order", "read", "Look up the current state of an order. When requested, perform this read even if the user also asked for an independent task. An order ID spelled with spoken separators is one identifier: remove spaces and hyphens between its letters and digits.",
     {"order_id": "string"}, ("order_id",)),
    ("search_products", "read", "Find products by query and optional budget; perform the search when requested, even if another independent task is also requested. Returns /products rows with /product_id, /name, and /price. For an explicit cart add, declare its write contract before this read. When choice is otherwise unspecified, product_id may come from exactly one valid returned row. If the user asked for the cheapest and exactly one valid row is returned, that sole row is the unambiguous cheapest candidate and may supply product_id. If several rows are returned, ranking is unsupported; ask the user to select.",
     {"query": "string", "max_price": "number"}, ("query",)),
    ("add_to_cart", "write", "Add a product and quantity to the cart only after an explicit user request. For a searched product, use product_id only from the current accepted search result under its selection rules and a write contract declared before search. A request to add one singular item without another quantity means quantity 1; preserve any explicit quantity or correction.",
     {"product_id": "string", "quantity": "integer"}, ("product_id", "quantity")),
)


def manifests() -> list[ToolManifest]:
    return [ToolManifest(
        name=name,
        description=description,
        effect=effect,
        parameters={
            "type": "object",
            "properties": {key: ({"type": kind} if kind else {})
                           for key, kind in properties.items()},
            "required": list(required),
            "additionalProperties": False,
        },
        timeout_s=30,
    ) for name, effect, description, properties, required in _TOOLS]


def validate_official_registry(registry: Any) -> None:
    """Fail if the pinned benchmark changes a tool's accepted parameters."""
    functions = registry.FUNCTIONS
    expected = {item[0]: item for item in _TOOLS}
    if set(functions) != set(expected):
        raise ValueError("FDB-v3 mock tool names differ from the pinned interface")
    for name, function in functions.items():
        _, _, _, properties, required = expected[name]
        parameters = {key: param for key, param in inspect.signature(function).parameters.items()
                      if param.kind not in (inspect.Parameter.VAR_KEYWORD,
                                            inspect.Parameter.VAR_POSITIONAL)}
        actual_required = {key for key, param in parameters.items()
                           if param.default is inspect.Parameter.empty}
        if set(parameters) != set(properties) or actual_required != set(required):
            raise ValueError(f"FDB-v3 mock tool signature changed: {name}")


@contextmanager
def _telemetry_lock(path: Path):
    """Serialize JSONL appends across tool threads and LiveKit room processes."""
    lock_path = path.with_name(path.name + ".lock")
    with _PROCESS_TELEMETRY_LOCK, lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class FDBMockExecutor:
    """Per-room executor with operation deduplication and official call telemetry."""

    def __init__(self, registry: Any, room_name: str, *, telemetry_path: Path = Path("/tmp/agent_tool_calls.log")):
        validate_official_registry(registry)
        if not room_name:
            raise ValueError("A LiveKit room name is required")
        self.registry = registry
        self.room_name = room_name
        self.telemetry_path = Path(telemetry_path)
        self._lock = asyncio.Lock()
        self._operations: dict[str, tuple[str, dict[str, Any], asyncio.Task[dict[str, Any]]]] = {}
        self._call_operations: dict[str, str] = {}
        self._cancelled: set[str] = set()

    async def drain(self) -> None:
        """Wait for calls already sent to the mock registry to finish logging."""
        async with self._lock:
            tasks = [entry[2] for entry in self._operations.values()]
        if tasks:
            await asyncio.gather(*(asyncio.shield(task) for task in tasks),
                                 return_exceptions=True)

    def operation_ids(self) -> frozenset[str]:
        return frozenset(self._operations)

    def confirmed_results(self, *, excluding: frozenset[str] = frozenset()) -> list[tuple[str, dict]]:
        """Return only successful registry results from completed, distinct operations."""
        confirmed = []
        for operation_id, (tool, _, task) in self._operations.items():
            if operation_id in excluding or not task.done() or task.cancelled():
                continue
            try:
                result = task.result()
            except Exception:
                continue
            if isinstance(result, dict) and result.get("status") == "success":
                confirmed.append((tool, result))
        return confirmed

    def _invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        result = self.registry.call(name, **arguments)
        ended = time.time()
        record = {"room": self.room_name, "call": {
            "function": name, "args": arguments,
            "timestamp_start": started, "timestamp_end": ended,
        }}
        line = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        self.telemetry_path.parent.mkdir(parents=True, exist_ok=True)
        with _telemetry_lock(self.telemetry_path):
            descriptor = os.open(self.telemetry_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, line)
            finally:
                os.close(descriptor)
        return result

    async def execute(self, call):
        if call.call_id in self._cancelled:
            return ToolResult(call_id=call.call_id, status="cancelled")
        if call.tool not in self.registry.FUNCTIONS:
            return ToolResult(call_id=call.call_id, status="failed", error="unknown_tool")
        async with self._lock:
            if call.call_id in self._cancelled:
                return ToolResult(call_id=call.call_id, status="cancelled")
            operation = call.operation_id
            existing = self._operations.get(operation)
            if existing is not None and (existing[0] != call.tool or existing[1] != call.arguments):
                return ToolResult(call_id=call.call_id,
                                  status=("unknown" if call.effect == "write" else "failed"),
                                  error="operation_conflict")
            if existing is None:
                task = asyncio.create_task(asyncio.to_thread(
                    self._invoke, call.tool, dict(call.arguments)))
                self._operations[operation] = (call.tool, dict(call.arguments), task)
            else:
                task = existing[2]
            self._call_operations[call.call_id] = operation
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            return ToolResult(call_id=call.call_id, status=("unknown" if call.effect == "write" else "failed"),
                              error=type(error).__name__)
        if not isinstance(result, dict) or result.get("status") != "success":
            return ToolResult(call_id=call.call_id, status="failed", result=result if isinstance(result, dict) else {})
        return ToolResult(call_id=call.call_id, status="success", result=result,
                          committed=call.effect == "write")

    async def cancel(self, call_id: str) -> str:
        self._cancelled.add(call_id)
        operation = self._call_operations.get(call_id)
        if operation is not None and operation in self._operations:
            return "unknown"
        return "cancelled_before_commit"
