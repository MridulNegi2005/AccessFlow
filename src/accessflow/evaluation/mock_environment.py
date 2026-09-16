"""Manifest-driven, deterministic tool environment for offline evaluation.

The environment deliberately has no knowledge of the demonstration workflow.  A
scenario supplies manifests and binds each manifest name to one of the small
capabilities below.  The write ledger is the source of truth for status reads;
the response returned to a caller may intentionally hide that truth to model a
lost transport response.
"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from jsonschema import validate
from pydantic import BaseModel, ConfigDict, Field

from ..clock import RealClock
from ..contracts import ToolCall, ToolManifest, ToolResult


class ArgumentMapping(BaseModel):
    """Map a wire schema's names to the environment's canonical concepts."""

    model_config = ConfigDict(extra="forbid")
    operation_id: str | None = None
    idempotency_parameter: str | None = None
    identity_fields: tuple[str, ...] = ()
    required_identity_fields: tuple[str, ...] = ()


class _BindingConfig(BaseModel):
    """Internal configuration; this is intentionally separate from ToolManifest."""

    model_config = ConfigDict(extra="forbid")
    kind: str
    identity_fields: tuple[str, ...] = ()
    required_identity_fields: tuple[str, ...] = ()
    delay_s: float = Field(default=0, ge=0)
    argument_mapping: ArgumentMapping | None = None

    @property
    def effective_identity_fields(self) -> tuple[str, ...]:
        nested = self.argument_mapping
        nested_fields = nested.identity_fields if nested else ()
        nested_required = nested.required_identity_fields if nested else ()
        return tuple(dict.fromkeys((*self.identity_fields, *self.required_identity_fields,
                                    *nested_fields, *nested_required)))


class LookupConfig(_BindingConfig):
    kind: Literal["lookup"] = "lookup"
    rows: list[dict[str, Any]] = Field(default_factory=list)


class WriteConfig(_BindingConfig):
    kind: Literal["write"] = "write"
    # ``reservation`` and ``action`` are labels for scenario reporting only.
    mode: Literal["write", "reservation", "action"] = "write"
    operation_id_parameter: str | None = None
    idempotency_parameter: str | None = None
    commit_delay_s: float = Field(default=0, ge=0)
    response_delay_s: float | None = Field(default=None, ge=0)
    fail_before_commit: bool = False
    commit_then_unknown: bool = False
    lost_response: bool = False
    result_template: dict[str, Any] = Field(default_factory=dict)

    @property
    def response_wait_s(self) -> float:
        return self.delay_s if self.response_delay_s is None else self.response_delay_s

    @property
    def effective_operation_id_parameter(self) -> str | None:
        nested = self.argument_mapping
        nested_parameter = ((nested.operation_id or nested.idempotency_parameter) if nested else None)
        return nested_parameter or self.operation_id_parameter or self.idempotency_parameter


class StatusConfig(_BindingConfig):
    kind: Literal["status"] = "status"
    operation_id_parameter: str = "operation_id"

    @property
    def effective_operation_id_parameter(self) -> str:
        nested = self.argument_mapping
        nested_parameter = ((nested.operation_id or nested.idempotency_parameter) if nested else None)
        return nested_parameter or self.operation_id_parameter


@dataclass
class _Pending:
    operation_id: str
    tool: str
    semantic_arguments: tuple[tuple[str, Any], ...]
    future: asyncio.Future[ToolResult]
    call_ids: set[str] = field(default_factory=set)
    committed: bool = False
    cancellation_requested: bool = False


class MockEnvironment:
    """An isolated in-memory ``ToolExecutor`` for deterministic evaluations.

    ``bindings`` is an explicit mapping from manifest name to a
    :class:`LookupConfig`, :class:`WriteConfig` or :class:`StatusConfig` (plain
    dictionaries with the same fields are accepted for JSON scenario files).
    No tool name is selected or interpreted by this class.
    """

    def __init__(
        self,
        manifests: Sequence[ToolManifest] | Mapping[str, ToolManifest],
        bindings: Mapping[str, _BindingConfig | Mapping[str, Any]],
        clock=None,
    ):
        if isinstance(manifests, Mapping):
            supplied = list(manifests.values())
        else:
            supplied = list(manifests)
        self.manifests = {manifest.name: manifest.model_copy(deep=True) for manifest in supplied}
        if len(self.manifests) != len(supplied):
            raise ValueError("Duplicate tool manifest name")
        self.clock = clock or RealClock()
        self.bindings: dict[str, _BindingConfig] = {}
        for name, binding in bindings.items():
            if name not in self.manifests:
                raise ValueError(f"Binding has no manifest: {name}")
            config = self._coerce_binding(binding, self.manifests[name])
            if config.kind == "lookup" and self.manifests[name].effect != "read":
                raise ValueError(f"Lookup binding requires a read manifest: {name}")
            if config.kind == "status" and self.manifests[name].effect != "read":
                raise ValueError(f"Status binding requires a read manifest: {name}")
            if config.kind == "write" and self.manifests[name].effect != "write":
                raise ValueError(f"Write binding requires a write manifest: {name}")
            self.bindings[name] = config
        missing = set(self.manifests).difference(self.bindings)
        if missing:
            raise ValueError(f"Missing mock binding(s): {', '.join(sorted(missing))}")

        self._effects: dict[str, dict[str, Any]] = {}
        self._outcomes: dict[str, str] = {}
        self._pending: dict[str, _Pending] = {}
        self._call_to_pending: dict[str, _Pending] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _coerce_binding(binding: _BindingConfig | Mapping[str, Any], manifest: ToolManifest) -> _BindingConfig:
        if isinstance(binding, _BindingConfig):
            return binding.model_copy(deep=True)
        if not isinstance(binding, Mapping):
            raise TypeError("Mock bindings must be typed configs or mappings")
        values = dict(binding)
        kind = values.get("kind")
        if kind is None:
            raise ValueError("Mock binding mappings must declare kind")
        if kind in {"reservation", "action"}:
            values["mode"] = kind
            kind = "write"
        values["kind"] = kind
        config_type = {"lookup": LookupConfig, "write": WriteConfig, "status": StatusConfig}.get(kind)
        if config_type is None:
            raise ValueError(f"Unknown mock binding kind: {kind}")
        return config_type.model_validate(values)

    @property
    def effects(self) -> dict[str, dict[str, Any]]:
        """A detached, JSON-serializable operation ledger snapshot."""

        return copy.deepcopy(self._effects)

    def inspect(self, operation_id: str | None = None) -> dict[str, Any] | None | dict[str, dict[str, Any]]:
        snapshot = self.effects
        if operation_id is None:
            return snapshot
        return snapshot.get(operation_id)

    async def execute(self, call: ToolCall) -> ToolResult:
        manifest = self.manifests.get(call.tool)
        binding = self.bindings.get(call.tool)
        if manifest is None or binding is None:
            return self._failed(call, "unbound_tool")
        if call.effect != manifest.effect:
            return self._failed(call, "effect_mismatch")
        try:
            validate(instance=call.arguments, schema=manifest.parameters)
        except Exception:
            return self._failed(call, "invalid_tool_arguments")
        if manifest.effect == "read":
            return await self._execute_read(call, binding)
        return await self._execute_write(call, binding)

    async def _execute_read(self, call: ToolCall, binding: _BindingConfig) -> ToolResult:
        await self._sleep(binding.delay_s)
        if isinstance(binding, LookupConfig):
            identity = binding.effective_identity_fields
            missing = [name for name in identity if name not in call.arguments]
            if missing:
                return self._failed(call, f"missing_identity_fields:{','.join(missing)}")
            rows = [row for row in binding.rows if all(row.get(k) == call.arguments[k] for k in identity)]
            result = {"rows": copy.deepcopy(rows)}
            return ToolResult(call_id=call.call_id, status="success", result=result)
        if isinstance(binding, StatusConfig):
            parameter = binding.effective_operation_id_parameter
            operation_id = call.arguments.get(parameter)
            if not isinstance(operation_id, str) or not operation_id:
                return self._failed(call, f"missing_operation_id:{parameter}")
            async with self._lock:
                outcome = self._outcomes.get(operation_id)
                if outcome is None:
                    outcome = "committed" if operation_id in self._effects else "unknown"
            return ToolResult(call_id=call.call_id, status="success",
                              result={"operation_id": operation_id, "outcome": outcome})
        return self._failed(call, "invalid_read_binding")

    async def _execute_write(self, call: ToolCall, binding: _BindingConfig) -> ToolResult:
        if not isinstance(binding, WriteConfig):
            return self._failed(call, "invalid_write_binding")
        operation_parameter = (binding.effective_operation_id_parameter
                               or self.manifests[call.tool].idempotency_parameter)
        if operation_parameter is not None and call.arguments.get(operation_parameter) != call.operation_id:
            return self._failed(call, f"operation_id_mismatch:{operation_parameter}")
        identity = binding.effective_identity_fields
        missing = [name for name in identity if name not in call.arguments]
        if missing:
            return self._failed(call, f"missing_identity_fields:{','.join(missing)}")
        semantic = self._semantic_arguments(call.arguments, operation_parameter, identity)

        async with self._lock:
            existing = self._effects.get(call.operation_id)
            if existing is not None:
                if existing["semantic_arguments"] != dict(semantic) or existing["tool"] != call.tool:
                    return self._failed(call, "operation_identity_conflict")
                return self._success_from_effect(call, existing)
            pending = self._pending.get(call.operation_id)
            if pending is not None:
                if pending.semantic_arguments != semantic or pending.tool != call.tool:
                    return self._failed(call, "operation_identity_conflict")
                if pending.cancellation_requested:
                    # Cancellation is confirmed for this attempt, so an
                    # identical retry gets its own future while the old
                    # attempt is still allowed to finish its sleep/cleanup.
                    self._pending.pop(call.operation_id, None)
                    pending = None
            if pending is not None:
                pending.call_ids.add(call.call_id)
                self._call_to_pending[call.call_id] = pending
                waiter = pending.future
            else:
                future = asyncio.get_running_loop().create_future()
                pending = _Pending(call.operation_id, call.tool, semantic, future, {call.call_id})
                self._pending[call.operation_id] = pending
                self._outcomes[call.operation_id] = "unknown"
                self._call_to_pending[call.call_id] = pending
                waiter = None

        if waiter is not None:
            try:
                completed = await asyncio.shield(waiter)
            except asyncio.CancelledError:
                raise
            if pending.cancellation_requested and not completed.committed:
                return ToolResult(call_id=call.call_id, status="cancelled")
            return completed.model_copy(update={"call_id": call.call_id}, deep=True)

        try:
            await self._sleep(binding.commit_delay_s)
            # Cancellation and commit are decided at one lock-protected point.
            # A cancellation observed here is a real no-effect cancellation;
            # once the effect assignment below happens, rollback is impossible.
            async with self._lock:
                current = self._pending.get(pending.operation_id) is pending
                cancelled = pending.cancellation_requested or not current
                if cancelled:
                    result = ToolResult(call_id=call.call_id, status="cancelled")
                    if current:
                        self._outcomes[call.operation_id] = "no_effect"
                elif binding.fail_before_commit:
                    result = self._failed(call, "configured_failure_before_commit")
                    self._outcomes[call.operation_id] = "no_effect"
                else:
                    effect = self._effect_record(call, binding, semantic)
                    # The lock is the commit point. Once this assignment
                    # occurs, cancellation reports too_late and never rolls
                    # back. A retry also replaces a prior no_effect outcome.
                    self._effects[call.operation_id] = effect
                    self._outcomes[call.operation_id] = "committed"
                    pending.committed = True
                    result = None
            if result is not None:
                await self._finish_pending(pending, result)
                return result
            await self._sleep(binding.response_wait_s)
            if binding.commit_then_unknown or binding.lost_response:
                result = ToolResult(call_id=call.call_id, status="unknown", committed=False,
                                    result={"operation_id": call.operation_id})
            else:
                result = self._success_from_effect(call, effect)
            await self._finish_pending(pending, result)
            return result
        except asyncio.CancelledError:
            # A cancelled leader may have lost its response. Preserve the
            # ledger if commit already happened, and make a pending pre-commit
            # operation explicitly no_effect for a later status read.
            async with self._lock:
                committed = pending.committed
                current = self._pending.get(pending.operation_id) is pending
                if current and not committed:
                    self._outcomes[pending.operation_id] = "no_effect"
                if current:
                    self._pending.pop(pending.operation_id, None)
                if not pending.future.done():
                    pending.future.set_result(ToolResult(
                        call_id=call.call_id, status="unknown" if committed else "failed",
                        committed=False, error="mock_execution_cancelled"))
            raise
        except Exception:
            # Keep an already committed effect visible even if a response path
            # is interrupted.  Callers treat this as an unknown write outcome.
            async with self._lock:
                committed = pending.committed
            result = ToolResult(call_id=call.call_id, status="unknown" if committed else "failed",
                                committed=False, error="mock_response_lost")
            await self._finish_pending(pending, result)
            return result

    async def _finish_pending(self, pending: _Pending, result: ToolResult) -> None:
        async with self._lock:
            # A canceled attempt may finish after a same-operation retry has
            # installed a new pending record.  Only the owning attempt may
            # remove the operation's current record.
            if self._pending.get(pending.operation_id) is pending:
                self._pending.pop(pending.operation_id, None)
            if not pending.future.done():
                pending.future.set_result(result.model_copy(deep=True))

    def _effect_record(self, call: ToolCall, binding: WriteConfig,
                       semantic: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
        result = {"operation_id": call.operation_id, "tool": call.tool,
                  "arguments": copy.deepcopy(call.arguments), "mode": binding.mode}
        result.update(copy.deepcopy(binding.result_template))
        # Preserve the canonical values even if a template contains metadata.
        result["operation_id"] = call.operation_id
        result["tool"] = call.tool
        result["arguments"] = copy.deepcopy(call.arguments)
        return {"operation_id": call.operation_id, "tool": call.tool,
                "arguments": copy.deepcopy(call.arguments), "semantic_arguments": dict(semantic),
                "effect": result, "committed": True, "committed_at": self.clock.now()}

    @staticmethod
    def _semantic_arguments(arguments: Mapping[str, Any], operation_parameter: str | None,
                            identity_fields: tuple[str, ...]) -> tuple[tuple[str, Any], ...]:
        # Identity fields are required/filter fields. Every remaining argument
        # can still affect an effect and therefore participates in conflict
        # detection; only the declared idempotency field is excluded.
        values = {name: copy.deepcopy(value) for name, value in arguments.items()
                  if name != operation_parameter}
        return tuple(sorted(values.items(), key=lambda item: item[0]))

    @staticmethod
    def _success_from_effect(call: ToolCall, effect: Mapping[str, Any]) -> ToolResult:
        return ToolResult(call_id=call.call_id, status="success", committed=True,
                          result=copy.deepcopy(effect["effect"]))

    @staticmethod
    def _failed(call: ToolCall, error: str) -> ToolResult:
        return ToolResult(call_id=call.call_id, status="failed", error=error)

    async def cancel(self, call_id: str) -> str:
        async with self._lock:
            pending = self._call_to_pending.get(call_id)
            if pending is None:
                return "unknown"
            if pending.operation_id in self._effects or pending.committed:
                return "too_late"
            pending.cancellation_requested = True
            if self._pending.get(pending.operation_id) is pending:
                self._outcomes[pending.operation_id] = "no_effect"
            return "cancelled_before_commit"

    async def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            await self.clock.sleep(seconds)
        else:
            await asyncio.sleep(0)


__all__ = [
    "ArgumentMapping", "LookupConfig", "MockEnvironment", "StatusConfig", "WriteConfig",
]
