"""Offline contract doubles. These are not speech recognition or live model evidence."""
import asyncio
from collections import deque

from .contracts import Observation, PlanProposal, ToolResult, TurnDecision


class FakePerception:
    def __init__(self, scripted=None):
        self.scripted = scripted or {}

    async def observe(self, event):
        if event.event_id in self.scripted:
            for observation in self.scripted[event.event_id]:
                yield observation
        elif event.kind == "transcript":
            p = event.payload
            yield Observation(event_id=event.event_id, source_id=p.utterance_id, revision=p.revision,
                              modality="text", text=p.text, final=p.final, speech_start=p.speech_start,
                              speech_end=p.speech_end, backend="fake/text-pass-through")
        else:
            raise ValueError("Fake perception needs explicitly scripted audio/image observations")


class FinalFlagPolicy:
    """Contract baseline only; no semantic or acoustic end-of-turn detection."""
    def update(self, observation, view):
        return TurnDecision(kind="complete" if observation.final else "continue")


class ScriptedReasoner:
    def __init__(self, proposals=()):
        self.proposals = deque(proposals)
        self.views = []

    async def plan(self, view, manifests):
        self.views.append(view.model_copy(deep=True))
        return self.proposals.popleft() if self.proposals else PlanProposal()


class FakeTools:
    """Manifest-name independent mock. Gate gives tests exact control of completion."""
    def __init__(self, gate=None, outcome="success", ignore_cancel=False):
        self.gate = gate
        self.outcome = outcome
        self.ignore_cancel = ignore_cancel
        self.calls = []
        self.cancelled = set()
        self.effects = {}

    async def execute(self, call):
        self.calls.append(call)
        if self.gate:
            await self.gate.wait()
        else:
            await asyncio.sleep(0)
        if call.call_id in self.cancelled and not self.ignore_cancel:
            return ToolResult(call_id=call.call_id, status="cancelled")
        committed = call.effect == "write" and self.outcome == "success"
        result = {"mock": True, "tool": call.tool, "arguments": call.arguments}
        if committed:
            self.effects.setdefault(call.operation_id, result)
        return ToolResult(call_id=call.call_id, status=self.outcome, result=result, committed=committed)

    async def cancel(self, call_id):
        self.cancelled.add(call_id)
        committed = any(c.call_id == call_id and c.operation_id in self.effects for c in self.calls)
        return "unknown" if self.ignore_cancel or committed else "cancelled_before_commit"


class MockOnlyAuthorization:
    """Use ONLY when the entire executor is a test double with no external effects."""
    def allows(self, view, call):
        return True
