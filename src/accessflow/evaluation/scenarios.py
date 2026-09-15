"""Internal development fixtures; labels and scripted reasoning are never live-model input."""
from copy import deepcopy
import math
from pathlib import Path
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from accessflow.contracts import InputEvent, Model, PlanProposal
from accessflow.evaluation.oracle import TaskExpectation


class ScriptedStep(Model):
    input_event_id: str
    after_tools: dict[str, str] = Field(default_factory=dict)
    proposal: PlanProposal


class TerminalOutput(Model):
    kind: Literal["final", "error", "clarify", "acknowledge"] = "final"
    code: str | None = None
    caused_by_event_id: str | None = None


class Scenario(Model):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}$")
    provenance: str = "Provenance not supplied"
    events: list[InputEvent] = Field(min_length=2)
    event_spacing_s: float = Field(default=0.01, ge=0, le=5)
    # Per-gap pacing for multi-turn live cases, where one uniform spacing cannot
    # place a later utterance after an earlier tool result on a slow backend.
    event_gaps_s: list[float] | None = Field(default=None)
    completion_timeout_s: float = Field(default=30, gt=0, le=110)
    proposals: list[PlanProposal] | None = None
    reasoning_steps: list[ScriptedStep] = Field(default_factory=list)
    expected_slots: dict[str, Any] = Field(default_factory=dict)
    expectation: TaskExpectation | None = None
    environment: dict[str, dict[str, Any]] | None = None
    terminal_output: TerminalOutput = Field(default_factory=TerminalOutput)

    @model_validator(mode="before")
    @classmethod
    def stable_event_ids(cls, value):
        value = deepcopy(value)
        if isinstance(value, dict):
            for index, event in enumerate(value.get("events", [])):
                if isinstance(event, dict):
                    event.setdefault("event_id", f"{value.get('id', 'scenario')}:event:{index}")
                    event.setdefault("sequence", index)
        return value

    @model_validator(mode="after")
    def coherent_session(self):
        if self.events[0].kind != "session_start":
            raise ValueError("Scenario must begin with session_start")
        if any(event.kind in {"session_start", "session_end"} for event in self.events[1:]):
            raise ValueError("Only one start is allowed; runner owns session_end")
        if any(event.session_id != self.events[0].session_id for event in self.events):
            raise ValueError("Scenario events must share one session ID")
        ids = [event.event_id for event in self.events]
        if len(set(ids)) != len(ids):
            raise ValueError("Scenario event IDs must be unique; duplicate delivery belongs in fault tests")
        names = [manifest.name for manifest in self.events[0].payload.tools]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate tool manifests")
        if self.proposals is not None and self.reasoning_steps:
            raise ValueError("Choose event proposals or reasoning_steps, not both")
        if any(step.input_event_id not in ids for step in self.reasoning_steps):
            raise ValueError("Scripted step references an unknown input event")
        if self.terminal_output.caused_by_event_id and self.terminal_output.caused_by_event_id not in ids:
            raise ValueError("Terminal criterion references an unknown input event")
        if self.event_gaps_s is not None:
            if len(self.event_gaps_s) != len(self.events) - 1:
                raise ValueError("event_gaps_s must supply one gap between each pair of events")
            if any(not math.isfinite(gap) for gap in self.event_gaps_s):
                raise ValueError("Each event gap must be a finite number")
            if any(gap < 0 or gap > 60 for gap in self.event_gaps_s):
                raise ValueError("Each event gap must be between 0 and 60 seconds")
        total_gap = sum(self.gaps())
        # NaN/inf compare False against `>`, which would silently pass the budget
        # check below; isfinite closes that off explicitly.
        if not math.isfinite(total_gap) or total_gap + self.completion_timeout_s > 114:
            raise ValueError("Scheduled scenario exceeds the internal 114-second replay budget")
        return self

    def gaps(self):
        if self.event_gaps_s is not None:
            return list(self.event_gaps_s)
        return [self.event_spacing_s] * (len(self.events) - 1)


def _reject_non_finite_literal(literal):
    raise ValueError(f"Scenario JSON must not contain non-finite literal: {literal}")


def _resolve_media_paths(raw, base_dir):
    # A committed scenario's WAV/PNG path must resolve the same way regardless of the
    # invoking process's working directory. Relative paths are resolved against the
    # scenario file's own location, not cwd; absolute paths pass through unchanged.
    if not isinstance(raw, dict):
        return
    for event in raw.get("events", []) or []:
        if not isinstance(event, dict) or event.get("kind") not in {"audio", "frame"}:
            continue
        payload = event.get("payload")
        path = payload.get("path") if isinstance(payload, dict) else None
        if isinstance(path, str) and path and not Path(path).is_absolute():
            payload["path"] = str((base_dir / path).resolve())


def load_scenario(path):
    # Python's json accepts the nonstandard NaN/Infinity/-Infinity tokens by
    # default; scenarios must stay valid JSON, so reject them here.
    raw = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=_reject_non_finite_literal)
    _resolve_media_paths(raw, Path(path).resolve().parent)
    return Scenario.model_validate(raw)


class StepReasoner:
    """Transparent offline fixture interpreter, not a natural-language reasoner."""
    def __init__(self, steps):
        self.steps = steps

    async def plan(self, view, manifests):
        event_ids = {observation.event_id for observation in view.observations}
        latest_calls = {call.tool: call for call in view.calls}
        matches = [step for step in self.steps if step.input_event_id in event_ids and all(
            name in latest_calls and latest_calls[name].status == status for name, status in step.after_tools.items())]
        if not matches:
            return PlanProposal()
        # A later matching rule overrides a general initial rule. Scenario authors can
        # explicitly use statuses for post-read and post-reconciliation transitions.
        proposal = matches[-1].proposal.model_copy(deep=True)

        def resolve(value):
            if isinstance(value, dict) and set(value) == {"$operation_of"}:
                call = latest_calls.get(value["$operation_of"])
                if call is None:
                    raise ValueError("Script references a tool that has not executed")
                return call.operation_id
            if isinstance(value, dict):
                return {key: resolve(item) for key, item in value.items()}
            if isinstance(value, list):
                return [resolve(item) for item in value]
            return value

        for call in proposal.calls:
            call.arguments = resolve(call.arguments)
        return proposal
