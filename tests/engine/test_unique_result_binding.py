"""A unique returned identifier never grants new write authority."""

import asyncio

import pytest
from jsonschema import validate

from accessflow.adapters.models import ModelReasoner
from accessflow.contracts import Interrupt, InterruptEvent, PlanProposal, ToolResult
from accessflow.fakes import FakeTools
from accessflow.result_binding import BindingError
from accessflow.write_binding import validate_binding
from test_safety import end, start, transcript, wait_for
from test_write_binding import fixture, manifests, read_plan, write_plan


def unique_read_plan():
    proposal = read_plan()
    proposal.slot_updates.pop("requested_time")
    proposal.write_contracts[0].delegated_arguments["item_id"].match_slots = {}
    return PlanProposal.model_validate(proposal.model_dump())


def test_explicit_empty_matches_survive_typed_model_and_json_schema():
    proposal = unique_read_plan()
    validate(proposal.model_dump(), ModelReasoner.output_schema(manifests()))
    assert proposal.write_contracts[0].delegated_arguments["item_id"].match_slots == {}


@pytest.mark.parametrize("fault", [None, "new_epoch", "new_request", "stale_source",
                                   "changed_dependency", "unconfirmed_dependency", "invalidated",
                                   "failed_result", "duplicate_result", "forged_id",
                                   "wrong_source", "zero_rows", "multiple_rows", "malformed_row"])
def test_unique_result_preserves_dispatch_provenance(fault):
    bound, proposed, kw = fixture()
    bound.contract.delegated_arguments["item_id"].match_slots = {}
    if fault == "new_epoch":
        kw["input_epoch"] += 1
    elif fault == "new_request":
        kw["request_id"] = "another-request"
    elif fault == "stale_source":
        kw["ledger"]["r"].status = "stale"
    elif fault == "changed_dependency":
        kw["state"].slots["region"].revision += 1
    elif fault == "unconfirmed_dependency":
        kw["state"].slots["region"].confirmed = False
    elif fault == "invalidated":
        kw["invalidated"].add("r")
    elif fault == "failed_result":
        kw["results"][0].status = "failed"
    elif fault == "duplicate_result":
        kw["results"].append(kw["results"][0].model_copy())
    elif fault == "forged_id":
        proposed.arguments["item_id"] = "invented"
    elif fault == "wrong_source":
        proposed.result_sources["item_id"] = "other-read"
    elif fault == "zero_rows":
        kw["results"][0].result["items"] = []
    elif fault == "multiple_rows":
        kw["results"][0].result["items"] *= 2
    elif fault == "malformed_row":
        kw["results"][0].result["items"].append(None)
    if fault is None:
        assert validate_binding(bound, proposed, **kw) == {"item_id"}
    else:
        with pytest.raises(BindingError):
            validate_binding(bound, proposed, **kw)


class UniqueCatalog(FakeTools):
    async def execute(self, call):
        if call.effect == "read":
            self.calls.append(call)
            return ToolResult(call_id=call.call_id, status="success",
                              result={"items": [{"id": "opaque-17"}]})
        return await super().execute(call)


class UniqueChainBackend:
    async def generate(self, system, data, schema):
        session = data["session"]
        if not session["results"]:
            return unique_read_plan().model_dump()
        rule = session["write_contracts"][0]["delegated_arguments"]["item_id"]
        plan = write_plan(rule["source_call_id"])
        plan.calls[0].dependencies = ["selected", "day"]
        return plan.model_dump()


@pytest.mark.parametrize("authorized", [True, False])
async def test_unique_chain_through_real_model_boundary_still_requires_environment_authorization(authorized):
    tools = UniqueCatalog()
    agent, iq, oq, task = await start([], tools=tools, manifests=manifests(), auth=authorized,
                                    reasoner=ModelReasoner(UniqueChainBackend()))
    try:
        await iq.put(transcript("Reserve the returned item in North for Wednesday"))
        await wait_for(oq, lambda e: e.kind == ("final" if authorized else "clarify"))
        assert len(tools.effects) == int(authorized)
        assert len(tools.calls) == 1 + int(authorized)
        if authorized:
            write = tools.calls[-1]
            assert write.arguments == {"item_id": "opaque-17", "booking_date": "Wednesday"}
            assert "region" in write.dependencies
        assert agent.state.slots["day"].value == "Wednesday"
    finally:
        await end(iq, task)


async def test_interruption_before_unique_result_write_prevents_dispatch():
    entered, release = asyncio.Event(), asyncio.Event()

    class HeldBackend(UniqueChainBackend):
        async def generate(self, system, data, schema):
            if data["session"]["results"]:
                entered.set()
                await release.wait()
            return await super().generate(system, data, schema)

    tools = UniqueCatalog()
    agent, iq, oq, task = await start([], tools=tools, manifests=manifests(),
                                    reasoner=ModelReasoner(HeldBackend()))
    try:
        await iq.put(transcript("Reserve the returned item in North for Wednesday"))
        await asyncio.wait_for(entered.wait(), 2)
        await iq.put(InterruptEvent(session_id="s", payload=Interrupt(scope="task")))
        await wait_for(oq, lambda e: e.kind == "acknowledge" and e.payload.get("stop_output"))
        release.set()
        await end(iq, task)
        assert not tools.effects
        assert [c.effect for c in tools.calls] == ["read"]
    finally:
        release.set()
        if not task.done():
            await end(iq, task)
