from collections.abc import AsyncIterator
from typing import Protocol

from .contracts import InputEvent, Observation, PlanProposal, SessionView, ToolCall, ToolManifest, ToolResult, TurnDecision


class Perception(Protocol):
    def observe(self, event: InputEvent) -> AsyncIterator[Observation]: ...


class TurnPolicy(Protocol):
    def update(self, observation: Observation, view: SessionView) -> TurnDecision: ...


class Reasoner(Protocol):
    async def plan(self, view: SessionView, manifests: list[ToolManifest]) -> PlanProposal: ...


class ToolExecutor(Protocol):
    async def execute(self, call: ToolCall) -> ToolResult: ...
    async def cancel(self, call_id: str) -> str: ...


class Authorization(Protocol):
    def allows(self, view: SessionView, call: ToolCall) -> bool: ...
