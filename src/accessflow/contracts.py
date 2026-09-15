"""Internal v0.1 protocol; this is NOT the unpublished organizer wire protocol."""

from typing import Annotated, Any, Literal, Protocol
from uuid import uuid4

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field, model_validator

VERSION = "0.1"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolManifest(Model):
    name: str
    description: str
    effect: Literal["read", "write"]
    parameters: dict[str, Any]
    status_tool: str | None = None
    idempotency_parameter: str | None = None
    timeout_s: float = Field(default=5, gt=0, le=110)

    @model_validator(mode="after")
    def valid_schema(self):
        Draft202012Validator.check_schema(self.parameters)
        if self.parameters.get("type") != "object":
            raise ValueError("Tool arguments must use an object schema")
        if self.idempotency_parameter and self.idempotency_parameter not in self.parameters.get("properties", {}):
            raise ValueError("Idempotency parameter must be declared in schema")
        return self


class Start(Model):
    tools: list[ToolManifest] = Field(default_factory=list)
    corpus: list[str] = Field(default_factory=list)


class Transcript(Model):
    utterance_id: str
    revision: int = Field(ge=0)
    text: str
    final: bool
    speech_start: float = Field(default=0, ge=0)
    speech_end: float = Field(default=0, ge=0)


class Audio(Model):
    path: str
    utterance_id: str
    revision: int = Field(default=0, ge=0)
    speech_start: float = Field(default=0, ge=0)
    speech_end: float = Field(default=0, ge=0)


class Frame(Model):
    path: str
    frame_id: str


class Interrupt(Model):
    scope: Literal["speech", "task"] = "speech"
    utterance_id: str | None = None


class ToolResult(Model):
    call_id: str
    status: Literal["success", "failed", "cancelled", "unknown"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    committed: bool = False


class End(Model):
    reason: str = "user"


class Envelope(Model):
    contract_version: Literal["0.1"] = VERSION
    session_id: str
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default=0, ge=0)
    sequence: int = Field(default=0, ge=0)


class StartEvent(Envelope):
    kind: Literal["session_start"] = "session_start"
    payload: Start


class TranscriptEvent(Envelope):
    kind: Literal["transcript"] = "transcript"
    payload: Transcript


class AudioEvent(Envelope):
    kind: Literal["audio"] = "audio"
    payload: Audio


class FrameEvent(Envelope):
    kind: Literal["frame"] = "frame"
    payload: Frame


class InterruptEvent(Envelope):
    kind: Literal["interrupt"] = "interrupt"
    payload: Interrupt


class ResultEvent(Envelope):
    kind: Literal["tool_result"] = "tool_result"
    payload: ToolResult


class EndEvent(Envelope):
    kind: Literal["session_end"] = "session_end"
    payload: End = Field(default_factory=End)


InputEvent = Annotated[
    StartEvent | TranscriptEvent | AudioEvent | FrameEvent | InterruptEvent | ResultEvent | EndEvent,
    Field(discriminator="kind"),
]


class Slot(Model):
    value: Any
    confirmed: bool = False
    evidence: list[str] = Field(default_factory=list)
    revision: int = 0


class Snapshot(Model):
    intent: str | None = None
    revision: int = 0
    slots: dict[str, Slot] = Field(default_factory=dict)
    pending_call_ids: list[str] = Field(default_factory=list)
    status: str = "listening"
    correction_pending: bool = False


class OutputEvent(Envelope):
    kind: Literal["acknowledge", "clarify", "tool_call", "cancel_call", "final", "error"]
    payload: dict[str, Any]
    state: Snapshot


class Observation(Model):
    event_id: str
    source_id: str
    revision: int = 0
    modality: Literal["text", "audio", "image"]
    text: str
    final: bool
    speech_start: float = 0
    speech_end: float = 0
    backend: str


class TurnDecision(Model):
    kind: Literal["continue", "complete", "possible_correction", "backchannel", "stop"]
    uncertainty: float = Field(default=0, ge=0, le=1)


class ProposedCall(Model):
    tool: str
    arguments: dict[str, Any]
    # Every argument affecting an effect must be tied to a slot. Literals are permitted
    # for schema constants, but the controller also invalidates all writes on new speech.
    dependencies: list[str] = Field(default_factory=list)
    # Optional parameter -> slot aliases; omitted parameters use their own names.
    # Aliases do not replace dependencies or authorize unmatched argument values.
    argument_slots: dict[str, str] = Field(default_factory=dict)


class PlanProposal(Model):
    intent: str | None = None
    slot_updates: dict[str, Any] = Field(default_factory=dict)
    calls: list[ProposedCall] = Field(default_factory=list)
    clarification: str | None = None
    response: str | None = None
    request_complete: bool = False
    # A model assertion alone is not execution authority; controller also requires
    # a completed utterance and an explicit, externally supplied authorization gate.
    write_requested: bool = False


class SessionView(Model):
    session_id: str
    state: Snapshot
    observations: list[Observation]
    results: list[ToolResult]
    calls: list["ToolCall"] = Field(default_factory=list)
    write_pending: bool = False
    # Set when the previous proposal only repeated calls that already completed.
    repeated_completed_call: bool = False
    # The request `calls` entries should be matched against for continuation checks
    # such as ModelReasoner.write_outstanding. Empty string is a valid id (used by
    # callers, including most tests, that never populate ToolCall.request_id either)
    # and matches only calls that likewise carry the default "".
    active_request_id: str = ""


class ToolCall(Model):
    call_id: str
    operation_id: str
    tool: str
    arguments: dict[str, Any]
    dependencies: dict[str, int]
    effect: Literal["read", "write"]
    # Which accepted request produced this call. Additive/optional: history in the
    # ledger is never deleted, but continuation logic can project only the calls
    # belonging to the currently active request instead of the whole session.
    #
    # Request lifecycle, in terms of this id:
    #  - A NEW REQUEST starts once the previous one is fully resolved (completed,
    #    explicitly cancelled, or superseded) and fresh speech arrives; the engine
    #    mints a new request_id (see Agent.request_id in engine.py).
    #  - A CORRECTION amends slots/intent of the request that is still open, under
    #    the SAME request_id; it invalidates dependent calls but does not start a
    #    new request.
    #  - An INTENTIONAL REPEATED ACTION (e.g. "book Wednesday" twice in a row) is
    #    only possible once the first request finished, so it naturally gets its
    #    own request_id and is dispatched as an independent call.
    request_id: str = ""
    status: Literal["pending", "success", "failed", "cancelled", "unknown", "stale"] = "pending"


class Clock(Protocol):
    def now(self) -> float: ...
    async def sleep(self, seconds: float) -> None: ...


SessionView.model_rebuild()
