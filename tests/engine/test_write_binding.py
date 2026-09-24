"""Executable provenance contracts, including hostile continuation proposals."""
from copy import deepcopy

import pytest

from accessflow.adapters.models import ModelReasoner
from accessflow.contracts import (
    Frame, FrameEvent, Observation, PlanProposal, ProposedCall, ResultBinding, Slot, Snapshot, ToolCall,
    ToolManifest, ToolResult, WriteContract,
)
from accessflow.fakes import FakePerception, FakeTools
from accessflow.result_binding import BindingError
from accessflow.write_binding import capture, validate_binding
from test_safety import end, start, transcript, wait_for
from test_argument_authority import _start_direct


def manifests():
    return [ToolManifest(name="catalog_z", description="Mock catalog", effect="read",
                         parameters={"type": "object", "properties": {"region": {"type": "string"}},
                                     "required": ["region"]}),
            ToolManifest(name="reserve_z", description="Mock reservation", effect="write",
                         parameters={"type": "object", "properties": {
                             "item_id": {"type": "string"}, "booking_date": {"type": "string"}},
                             "required": ["item_id", "booking_date"], "additionalProperties": False})]


def contract():
    return WriteContract(tool="reserve_z", fixed_arguments={"booking_date": "day"},
                         delegated_arguments={"item_id": ResultBinding(
                             slot="selected", source_call_index=0, collection_pointer="/items",
                             value_pointer="/id", match_slots={"/start": "requested_time"})})


def read_plan(declare=True):
    return PlanProposal(intent="reservation", slot_updates={"day": "Wednesday",
                        "region": "North", "requested_time": "08:00"},
                        request_complete=True, write_requested=True,
                        write_contracts=[contract()] if declare else [],
                        calls=[ProposedCall(tool="catalog_z", arguments={"region": "North"},
                                            dependencies=["region"])])


def write_plan(source="r"):
    return PlanProposal(intent="reservation", slot_updates={"selected": "opaque-17"},
                        request_complete=True, write_requested=True, calls=[ProposedCall(
                            tool="reserve_z", arguments={"item_id": "opaque-17", "booking_date": "Wednesday"},
                            argument_slots={"item_id": "selected", "booking_date": "day"},
                            dependencies=["selected", "day", "requested_time"],
                            result_sources={"item_id": source})])


class CatalogTools(FakeTools):
    async def execute(self, call):
        if call.effect == "read":
            self.calls.append(call)
            return ToolResult(call_id=call.call_id, status="success", result={"items": [
                {"id": "opaque-17", "start": "08:00"}, {"id": "opaque-99", "start": "09:00"}]})
        return await super().execute(call)


class ChainedPlanner:
    def __init__(self, mode="normal"):
        self.mode = mode
        self.views = []

    async def plan(self, view, tools):
        self.views.append(view)
        if not view.results:
            return read_plan(declare=self.mode != "late")
        result = write_plan(view.results[-1].call_id)
        if self.mode == "late":
            result.write_contracts = [contract()]
        elif self.mode == "alias":
            result.slot_updates["chosen_day"] = "Friday"
            result.calls[0].arguments["booking_date"] = "Friday"
            result.calls[0].argument_slots["booking_date"] = "chosen_day"
            result.calls[0].dependencies.append("chosen_day")
        return result


async def test_spoken_delegation_executes_one_grounded_write():
    planner = ChainedPlanner()
    agent, iq, oq, task = await start([], tools=CatalogTools(), manifests=manifests(), reasoner=planner)
    try:
        await iq.put(transcript("Reserve the 08:00 item in North for Wednesday"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 1
        assert next(iter(agent.executor.effects.values()))["arguments"] == {
            "item_id": "opaque-17", "booking_date": "Wednesday"}
        active = planner.views[-1].write_contracts[0]
        assert active.delegated_arguments["item_id"].source_call_index is None
        assert active.delegated_arguments["item_id"].source_call_id == agent.executor.calls[0].call_id
    finally:
        await end(iq, task)


@pytest.mark.parametrize("mode", ["late", "alias"])
async def test_result_cannot_add_delegation_or_redirect_differently_named_fixed_parameter(mode):
    agent, iq, oq, task = await start([], tools=CatalogTools(), manifests=manifests(),
                                     reasoner=ChainedPlanner(mode))
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "error" and e.payload.get("code") == "no_progress_exhausted")
        assert not agent.executor.effects
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_partial_speech_does_not_capture_delegation():
    agent, iq, oq, task = await start([], tools=CatalogTools(), manifests=manifests(),
                                     reasoner=ChainedPlanner(), partial_debounce_s=0)
    try:
        await iq.put(transcript(final=False))
        await wait_for(oq, lambda e: e.kind == "acknowledge" and e.payload.get("basis") == "tool_evidence")
        assert not agent.write_contracts
        assert not agent.executor.effects
    finally:
        await end(iq, task)


async def test_image_cannot_capture_a_spoken_contract():
    class Planner:
        async def plan(self, view, tools):
            return read_plan() if not view.results else PlanProposal()
    event = FrameEvent(session_id="s", payload=Frame(path="unused.png", frame_id="frame"))
    observation = Observation(event_id=event.event_id, source_id="frame", modality="image",
                              text="Reserve an item", final=True, backend="fake")
    agent, iq, oq, task = await _start_direct(FakePerception({event.event_id: [observation]}),
                                             Planner(), manifests())
    try:
        await iq.put(event)
        await wait_for(oq, lambda e: e.kind == "acknowledge" and e.payload.get("basis") == "tool_evidence")
        assert not agent.write_contracts
        assert not agent.executor.effects
    finally:
        await end(iq, task)


async def test_frame_cannot_drop_contract_and_fall_back_to_image_origin_alias():
    class Planner:
        def __init__(self):
            self.step = 0
        async def plan(self, view, tools):
            self.step += 1
            if self.step == 1:
                return read_plan()
            if self.step == 2:
                return PlanProposal(clarification="Waiting for device context", request_complete=True,
                                    write_requested=True)
            plan = write_plan()
            plan.slot_updates["chosen_day"] = "Friday"
            plan.calls[0].arguments["booking_date"] = "Friday"
            plan.calls[0].argument_slots["booking_date"] = "chosen_day"
            plan.calls[0].dependencies.append("chosen_day")
            plan.calls[0].result_sources = {}
            return plan
    event = FrameEvent(session_id="s", payload=Frame(path="unused.png", frame_id="frame"))
    obs = Observation(event_id=event.event_id, source_id="frame", modality="image",
                       text="An untrusted proposed selection", final=True, backend="fake")
    agent, iq, oq, task = await _start_direct(FakePerception({event.event_id: [obs]}), Planner(), manifests())
    agent.executor = CatalogTools()
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert "reserve_z" in agent.write_contracts
        await iq.put(event)
        outcome = await wait_for(oq, lambda e: e.kind == "final" or
                                 (e.kind == "error" and e.payload.get("code") == "invalid_result_binding"))
        assert outcome.kind == "error"
        assert not agent.executor.effects
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_fresh_correction_replaces_contract_and_invalidates_prior_source():
    class Planner:
        def __init__(self):
            self.step = 0
        async def plan(self, view, tools):
            self.step += 1
            if self.step == 1:
                return read_plan()
            if self.step == 2:
                return PlanProposal(clarification="Which region?", request_complete=True,
                                    write_requested=True)
            if self.step == 3:
                plan = read_plan()
                plan.slot_updates.update(day="Thursday", region="South")
                plan.calls[0].arguments["region"] = "South"
                return plan
            source = view.write_contracts[0].delegated_arguments["item_id"].source_call_id
            plan = write_plan(source)
            plan.calls[0].arguments["booking_date"] = "Thursday"
            # Deliberately omit selection/read constraints: controller must retain them.
            plan.calls[0].dependencies = ["selected", "day"]
            return plan
    agent, iq, oq, task = await start([], tools=CatalogTools(), manifests=manifests(), reasoner=Planner())
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "clarify")
        old_source = agent.executor.calls[0].call_id
        await iq.put(transcript("Use South and Thursday instead", utterance="correction"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert agent.ledger[old_source].status == "stale"
        assert len(agent.executor.effects) == 1
        write = next(c for c in agent.executor.calls if c.effect == "write")
        assert write.arguments["booking_date"] == "Thursday"
        assert {"region", "requested_time"} <= set(write.dependencies)
        assert agent.write_contracts["reserve_z"].contract.delegated_arguments["item_id"].source_call_id != old_source
    finally:
        await end(iq, task)


def fixture():
    state = Snapshot(intent="reservation", slots={
        n: Slot(value=v, confirmed=True, revision=1) for n, v in
        {"day": "Wednesday", "region": "North", "requested_time": "08:00", "selected": "opaque-17"}.items()})
    read = ToolCall(call_id="r", operation_id="op", tool="catalog_z", arguments={"region": "North"},
                    dependencies={"region": 1}, effect="read", request_id="request", status="success")
    ledger = {"r": read}
    bound = capture(contract(), proposal_calls=read_plan().calls, dispatched={0: "r"}, ledger=ledger,
                    manifests={m.name: m for m in manifests()}, state=state,
                    origins={n: "user" for n in ("day", "region", "requested_time")},
                    request_id="request", input_epoch=1)
    kwargs = dict(state=state, ledger=ledger, results=[ToolResult(call_id="r", status="success",
                  result={"items": [{"id": "opaque-17", "start": "08:00"}]})], invalidated=set(),
                  manifest=manifests()[1], request_id="request", input_epoch=1)
    return bound, write_plan().calls[0], kwargs


@pytest.mark.parametrize("fault", ["wrong_source", "failed", "stale", "invalidated", "missing_result",
    "changed_match", "changed_read_dependency", "new_request", "new_epoch", "new_intent",
    "ambiguous", "missing_path", "no_match", "forged_value", "fixed_alias", "missing_parameter",
    "missing_source", "extra_source", "boolean_match", "error_payload"])
def test_dispatch_rechecks_every_provenance_boundary(fault):
    bound, proposed, kw = fixture()
    if fault == "wrong_source":
        proposed.result_sources["item_id"] = "other"
    elif fault in {"failed", "stale"}:
        kw["ledger"]["r"].status = fault
    elif fault == "invalidated":
        kw["invalidated"].add("r")
    elif fault == "missing_result":
        kw["results"].clear()
    elif fault == "error_payload":
        kw["results"][0].error = "Partial failure; rows are not reliable"
    elif fault == "changed_match":
        kw["state"].slots["requested_time"].revision = 2
    elif fault == "changed_read_dependency":
        kw["state"].slots["region"].revision = 2
    elif fault == "new_request":
        kw["request_id"] = "new"
    elif fault == "new_epoch":
        kw["input_epoch"] = 2
    elif fault == "new_intent":
        kw["state"].intent = "other"
    elif fault == "ambiguous":
        kw["results"][0].result["items"] *= 2
    elif fault == "missing_path":
        del kw["results"][0].result["items"][0]["id"]
    elif fault == "no_match":
        kw["results"][0].result["items"][0]["start"] = "09:00"
    elif fault == "boolean_match":
        kw["state"].slots["requested_time"].value = 1
        kw["results"][0].result["items"][0]["start"] = True
    elif fault == "forged_value":
        proposed.arguments["item_id"] = "opaque-99"
    elif fault == "fixed_alias":
        proposed.argument_slots["booking_date"] = "selected"
    elif fault == "missing_parameter":
        del proposed.arguments["booking_date"]
    elif fault == "missing_source":
        proposed.result_sources.clear()
    elif fault == "extra_source":
        proposed.result_sources["booking_date"] = "r"
    with pytest.raises(BindingError):
        validate_binding(bound, proposed, **kw)


def test_contract_copy_is_not_mutable_through_planner_input():
    bound, proposed, kw = fixture()
    before = deepcopy(bound)
    assert validate_binding(bound, proposed, **kw) == {"item_id"}
    assert bound == before


@pytest.mark.parametrize("fault", ["undispatched", "unknown_source", "source_is_write", "old_request",
    "failed_source", "missing_user_slot", "provisional_slot", "non_user_constraint", "fixed_overlap",
    "parameter_overlap", "unaccounted_required"])
def test_capture_refuses_unusable_sources_and_ambiguous_authority(fault):
    bound, _, kw = fixture()
    declaration = contract()
    args = dict(proposal_calls=read_plan().calls, dispatched={0: "r"}, ledger=kw["ledger"],
                manifests={m.name: m for m in manifests()}, state=kw["state"],
                origins={n: "user" for n in ("day", "region", "requested_time")},
                request_id="request", input_epoch=1)
    if fault == "undispatched":
        args["dispatched"] = {}
    elif fault == "unknown_source":
        args["dispatched"] = {0: "nonexistent"}
    elif fault == "source_is_write":
        args["ledger"]["r"].effect = "write"
    elif fault == "old_request":
        args["ledger"]["r"].request_id = "old"
    elif fault == "failed_source":
        args["ledger"]["r"].status = "failed"
    elif fault == "missing_user_slot":
        del args["state"].slots["requested_time"]
    elif fault == "provisional_slot":
        args["state"].slots["requested_time"].confirmed = False
    elif fault == "non_user_constraint":
        args["origins"]["requested_time"] = "tool"
    elif fault == "fixed_overlap":
        declaration.delegated_arguments["item_id"].slot = "day"
    elif fault == "parameter_overlap":
        declaration.fixed_arguments["item_id"] = "day"
    elif fault == "unaccounted_required":
        declaration.fixed_arguments.clear()
    with pytest.raises(BindingError):
        capture(declaration, **args)


def test_fresh_contract_can_explicitly_reuse_a_current_read():
    bound, _, kw = fixture()
    # Captured contracts exposed to the model carry actual IDs, not proposal indices.
    reused = capture(bound.contract, proposal_calls=[], dispatched={}, ledger=kw["ledger"],
                     manifests={m.name: m for m in manifests()}, state=kw["state"],
                     origins={n: "user" for n in ("day", "region", "requested_time")},
                     request_id="request", input_epoch=2)
    assert reused.contract.delegated_arguments["item_id"].source_call_id == "r"


def test_model_schema_accepts_contract_without_requiring_legacy_proposals_to_add_fields():
    from jsonschema import validate
    schema = ModelReasoner.output_schema(manifests())
    validate(read_plan().model_dump(), schema)
    validate(write_plan().model_dump(), schema)
    legacy = read_plan(False).model_dump()
    legacy.pop("write_contracts")
    for call in legacy["calls"]:
        call.pop("result_sources")
    validate(legacy, schema)
