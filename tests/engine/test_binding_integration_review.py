"""Deterministic model boundary and controller integration for spoken bindings."""

import pytest
from pydantic import ValidationError

from accessflow.adapters.models import ModelReasoner
from accessflow.contracts import PlanProposal, SessionView, Snapshot
from test_safety import end, start, transcript, wait_for
from test_write_binding import CatalogTools, contract, manifests, read_plan, write_plan


class JsonChainBackend:
    """Return model-shaped JSON, exercising ModelReasoner rather than bypassing it."""

    def __init__(self):
        self.requests = []

    async def generate(self, system, data, schema):
        self.requests.append((data, schema))
        session = data["session"]
        if not session["results"]:
            return read_plan().model_dump()
        rule = session["write_contracts"][0]["delegated_arguments"]["item_id"]
        return write_plan(rule["source_call_id"]).model_dump()


@pytest.mark.parametrize("authorized", [True, False])
async def test_json_model_boundary_preserves_bound_chain_and_environment_permission(authorized):
    backend = JsonChainBackend()
    tools = CatalogTools()
    agent, iq, oq, task = await start(
        [], tools=tools, manifests=manifests(), auth=authorized,
        reasoner=ModelReasoner(backend),
    )
    try:
        await iq.put(transcript("Reserve the 08:00 item in North for Wednesday"))
        await wait_for(oq, lambda e: e.kind == ("final" if authorized else "clarify"))
        assert len(tools.effects) == int(authorized)
        assert len(tools.calls) == 1 + int(authorized)
        continuation = backend.requests[1][0]
        rule = continuation["session"]["write_contracts"][0]["delegated_arguments"]["item_id"]
        assert rule["source_call_id"] == tools.calls[0].call_id
        assert rule["source_call_index"] is None
        assert continuation["manifests"][1]["parameters"] == manifests()[1].parameters
        assert continuation["required_next_step"]["kind"] == "complete_requested_write"
        assert backend.requests[1][1]["properties"]["response"]["type"] == "null"
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_fresh_selection_correction_can_explicitly_reuse_accepted_read_end_to_end():
    class CorrectedBackend:
        def __init__(self):
            self.step = 0

        async def generate(self, system, data, schema):
            self.step += 1
            if self.step == 1:
                return read_plan().model_dump()
            if self.step == 2:
                return PlanProposal(
                    clarification="Please confirm the time before reservation.",
                    request_complete=True, write_requested=True,
                ).model_dump()
            if self.step == 3:
                replacement = contract()
                replacement.delegated_arguments["item_id"].source_call_index = None
                replacement.delegated_arguments["item_id"].source_call_id = (
                    data["session"]["results"][0]["call_id"]
                )
                return PlanProposal(
                    intent="reservation", slot_updates={"requested_time": "09:00"},
                    request_complete=True, write_requested=True,
                    write_contracts=[replacement],
                ).model_dump()
            source = data["session"]["write_contracts"][0]["delegated_arguments"]["item_id"]
            plan = write_plan(source["source_call_id"])
            plan.slot_updates["selected"] = "opaque-99"
            plan.calls[0].arguments["item_id"] = "opaque-99"
            return plan.model_dump()

    tools = CatalogTools()
    agent, iq, oq, task = await start(
        [], tools=tools, manifests=manifests(), reasoner=ModelReasoner(CorrectedBackend()),
    )
    try:
        await iq.put(transcript("Reserve the 08:00 item in North for Wednesday"))
        await wait_for(oq, lambda e: e.kind == "clarify")
        source = tools.calls[0].call_id
        await iq.put(transcript("Use 09:00 instead", utterance="correction"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert [c.effect for c in tools.calls] == ["read", "write"]
        assert agent.ledger[source].status == "success"
        assert tools.calls[1].arguments == {"item_id": "opaque-99", "booking_date": "Wednesday"}
        assert tools.calls[1].dependencies["requested_time"] == agent.state.slots["requested_time"].revision
    finally:
        await end(iq, task)


@pytest.mark.parametrize("fault", ["both_sources", "no_source", "empty_constraints"])
async def test_model_boundary_rejects_invalid_binding_semantics(fault):
    malformed = read_plan().model_dump()
    rule = malformed["write_contracts"][0]["delegated_arguments"]["item_id"]
    if fault == "both_sources":
        rule["source_call_id"] = "unrelated"
    elif fault == "no_source":
        rule["source_call_index"] = None
    else:
        rule["match_slots"] = {}

    class Backend:
        async def generate(self, system, data, schema):
            return malformed

    view = SessionView(session_id="s", state=Snapshot(), observations=[], results=[])
    with pytest.raises(ValidationError):
        await ModelReasoner(Backend()).plan(view, manifests())
