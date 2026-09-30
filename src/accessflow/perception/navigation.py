"""Small, local in-car navigation state for a voice extension demo.

This changes a simulated dashboard destination, not a vehicle or map service.
No benchmark tool, scenario, or telemetry is imported here.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

from accessflow.contracts import ToolManifest, ToolResult


DESTINATIONS = ("Central Station", "City Hospital", "Airport Terminal 1")
_ALIASES = {
    "central station": "Central Station",
    "the central station": "Central Station",
    "city hospital": "City Hospital",
    "the city hospital": "City Hospital",
    "airport terminal 1": "Airport Terminal 1",
    "airport terminal one": "Airport Terminal 1",
    "the airport terminal 1": "Airport Terminal 1",
}


def navigation_manifests() -> list[ToolManifest]:
    return [
        ToolManifest(
            name="get_navigation_state", effect="read",
            description="Read the current simulated in-car destination.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        ToolManifest(
            name="set_navigation_destination", effect="write",
            description=("Change the simulated in-car destination when the user explicitly asks. "
                         "Available places: Central Station, City Hospital, Airport Terminal 1. "
                         "Use the place the user finally requested after any correction. "
                         "Ask for clarification if the place is unclear; do not guess."),
            parameters={
                "type": "object",
                "properties": {"destination": {"type": "string"}},
                "required": ["destination"], "additionalProperties": False,
            },
        ),
    ]


class NavigationStateStore:
    """Local dashboard projection; the per-room executor remains authoritative."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def write(self, room_name: str, destination: str, revision: int) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=5)) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS navigation_state (
                    room_name TEXT PRIMARY KEY,
                    destination TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            # Only write if our revision is strictly greater than any stored one.
            # This prevents a late old thread from overwriting a newer committed state.
            cursor = connection.execute("""
                INSERT INTO navigation_state (room_name, destination, revision, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(room_name) DO UPDATE SET
                    destination=excluded.destination,
                    revision=excluded.revision,
                    updated_at=excluded.updated_at
                WHERE excluded.revision > navigation_state.revision
            """, (room_name, destination, revision, time.time()))
            return cursor.rowcount > 0

    def read(self, room_name: str) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None
        with closing(sqlite3.connect(self.path, timeout=5)) as connection:
            try:
                row = connection.execute(
                    "SELECT destination, revision, updated_at FROM navigation_state WHERE room_name=?",
                    (room_name,),
                ).fetchone()
            except sqlite3.OperationalError as error:
                if "no such table" not in str(error):
                    raise
                return None
        if row is None:
            return None
        return {"room": room_name, "destination": row[0],
                "revision": row[1], "updated_at": row[2],
                "mode": "simulated_navigation"}


class NavigationExecutor:
    """Per-room, idempotent simulated navigation with no external effects."""

    def __init__(self, initial_destination: str = "Central Station", *,
                 room_name: str | None = None, state_store: NavigationStateStore | None = None):
        if initial_destination not in DESTINATIONS:
            raise ValueError("Initial destination must be in the demo catalog")
        if (room_name is None) != (state_store is None):
            raise ValueError("Room name and state store must be supplied together")
        self.destination = initial_destination
        self.revision = 0
        self.room_name = room_name
        self.state_store = state_store
        self._lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._operations: dict[str, tuple[str, dict[str, Any], ToolResult]] = {}
        self._call_operations: dict[str, str] = {}
        self._cancelled: set[str] = set()
        self._persistence_tasks: dict[str, asyncio.Task[ToolResult]] = {}
        self._next_revision = 0

    async def initialize(self) -> None:
        if self.state_store is not None and self.room_name is not None:
            await asyncio.to_thread(self.state_store.write, self.room_name,
                                    self.destination, self.revision)
            state = await asyncio.to_thread(self.state_store.read, self.room_name)
            if state is not None:
                self.destination = state["destination"]
                self.revision = state["revision"]
                self._next_revision = self.revision

    async def execute(self, call) -> ToolResult:
        task: asyncio.Task[ToolResult] | None = None
        result: ToolResult | None = None
        async with self._lock:
            if call.call_id in self._cancelled:
                return ToolResult(call_id=call.call_id, status="cancelled")
            arguments = dict(call.arguments)
            prior = self._operations.get(call.operation_id)
            if prior is not None:
                if prior[0] != call.tool or prior[1] != arguments:
                    return ToolResult(call_id=call.call_id,
                                      status="unknown" if call.effect == "write" else "failed",
                                      error="operation_conflict")
                result = prior[2]
                self._call_operations[call.call_id] = call.operation_id
                task = self._persistence_tasks.get(call.operation_id)
                if task is None:
                    return result.model_copy(update={"call_id": call.call_id})
            elif call.tool == "get_navigation_state" and not arguments:
                result = ToolResult(call_id=call.call_id, status="success", result={
                    "destination": self.destination, "revision": self.revision,
                    "mode": "simulated_navigation",
                })
            elif call.tool == "set_navigation_destination":
                raw = arguments.get("destination")
                resolved = _ALIASES.get(raw.strip().casefold()) if isinstance(raw, str) else None
                if len(arguments) != 1 or resolved is None:
                    result = ToolResult(call_id=call.call_id, status="failed",
                                        error="unsupported_destination", result={
                                            "available_destinations": list(DESTINATIONS),
                                        })
                else:
                    previous = self.destination
                    if resolved != previous:
                        if self.state_store is not None and self.room_name is not None:
                            # Reserve a distinct revision and record the operation
                            # before the persistence task can start a DB thread.
                            revision = max(self.revision, self._next_revision) + 1
                            self._next_revision = revision
                            pending = ToolResult(call_id=call.call_id, status="unknown",
                                                 error="persistence_in_progress")
                            self._operations[call.operation_id] = (call.tool, arguments, pending)
                            self._call_operations[call.call_id] = call.operation_id
                            task = asyncio.create_task(self._persist_destination(
                                call.call_id, call.operation_id, resolved, previous, revision))
                            self._persistence_tasks[call.operation_id] = task
                        else:
                            self.revision += 1
                            self.destination = resolved
                    if task is None:
                        result = ToolResult(call_id=call.call_id, status="success", committed=True,
                                            result={"destination": self.destination,
                                                    "previous_destination": previous,
                                                    "revision": self.revision,
                                                    "mode": "simulated_navigation"})
            else:
                result = ToolResult(call_id=call.call_id, status="failed", error="unknown_tool")

            if task is None and result is not None:
                self._operations[call.operation_id] = (call.tool, arguments, result)
                self._call_operations[call.call_id] = call.operation_id

        if task is not None:
            # Cancelling the controller's await cannot stop a running SQLite
            # thread. Keep this operation alive, and return its real result on
            # the ordinary path.
            return (await asyncio.shield(task)).model_copy(update={"call_id": call.call_id})
        assert result is not None
        return result

    async def _persist_destination(
        self, call_id: str, operation_id: str, destination: str,
        previous: str, revision: int,
    ) -> ToolResult:
        assert self.state_store is not None and self.room_name is not None
        async with self._write_lock:
            applied = False
            write_error: Exception | None = None
            try:
                applied = await asyncio.to_thread(
                    self.state_store.write, self.room_name, destination, revision)
            except Exception as error:
                write_error = error
            try:
                state = await asyncio.to_thread(self.state_store.read, self.room_name)
            except Exception:
                state = None

            exact_commit = bool(
                state and state["revision"] == revision
                and state["destination"] == destination
            )
            superseded = bool(state and state["revision"] > revision)
            if exact_commit or applied:
                status, committed, error = "success", True, None
            elif superseded:
                status, committed, error = "cancelled", False, "superseded_by_newer_revision"
            elif write_error is not None and state is not None:
                status, committed, error = "failed", False, "state_store_failure"
            else:
                status, committed, error = "unknown", False, "state_store_outcome_unknown"

            async with self._lock:
                if state and state["revision"] >= revision:
                    if state["revision"] >= self.revision:
                        self.destination = state["destination"]
                        self.revision = state["revision"]
                elif applied and revision >= self.revision:
                    # write() returned only after its SQLite transaction committed.
                    # If the follow-up read failed, use that confirmed commit to
                    # keep the executor ledger aligned with the durable effect.
                    self.destination = destination
                    self.revision = revision
                elif state and state["revision"] >= self.revision:
                    self.destination = state["destination"]
                    self.revision = state["revision"]
                current_destination = self.destination
                current_revision = self.revision
                final = ToolResult(
                    call_id=call_id, status=status, committed=committed,
                    result={
                        "destination": destination if committed else current_destination,
                        "previous_destination": previous,
                        "revision": revision if committed else current_revision,
                        "current_destination": current_destination,
                        "current_revision": current_revision,
                        "mode": "simulated_navigation",
                    },
                    error=error,
                )
                _, arguments, _ = self._operations[operation_id]
                self._operations[operation_id] = (
                    "set_navigation_destination", arguments, final)
                self._persistence_tasks.pop(operation_id, None)
            return final

    async def cancel(self, call_id: str) -> str:
        async with self._lock:
            self._cancelled.add(call_id)
            if call_id in self._call_operations:
                # The operation was registered before dispatch. Once scheduled,
                # thread cancellation cannot be proven from coroutine state.
                return "unknown"
            return "cancelled_before_commit"

    async def drain(self, timeout: float = 5.0) -> tuple[str, ...]:
        """Wait briefly for writes and return operation IDs still unresolved."""
        async with self._lock:
            tasks = dict(self._persistence_tasks)
        if not tasks:
            return ()
        _, pending = await asyncio.wait(tuple(tasks.values()), timeout=timeout)
        return tuple(operation_id for operation_id, task in tasks.items() if task in pending)

    def operation_ids(self) -> frozenset[str]:
        return frozenset(self._operations)

    def confirmed_results(self, *, excluding: frozenset[str] = frozenset()) -> list[tuple[str, dict]]:
        return [(tool, {"status": "success", **result.result})
                for operation, (tool, _, result) in self._operations.items()
                if operation not in excluding and result.status == "success"
                and result.result is not None]
