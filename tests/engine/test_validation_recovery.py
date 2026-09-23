"""Rejected model outputs may retry once without changing evidence authority."""
import json

import pytest

from accessflow.contracts import PlanProposal
from test_safety import end, start, transcript, wait_for
from test_write_binding import CatalogTools, manifests, read_plan, write_plan


def reject(kind):
    if kind == "pydantic":
        PlanProposal.model_validate({"calls": "malicious secret raw content"})
    elif kind == "json":
        json.loads("malicious secret raw content")
    else:
        from jsonschema import validate
        validate({"request_complete": "malicious secret raw content"},
                 {"properties": {"request_complete": {"type": "boolean"}}})


@pytest.mark.parametrize("kind", ["pydantic", "json", "schema"])
async def test_rejected_fresh_plan_retries_same_speech_and_can_capture_contract(kind):
    class Planner:
        count = 0
        async def plan(self, view, tools):
            self.count += 1
            if self.count == 1:
                reject(kind)
            if not view.results:
                return read_plan()
            return write_plan(view.results[-1].call_id)
    planner = Planner()
    agent, iq, oq, task = await start([], reasoner=planner, tools=CatalogTools(), manifests=manifests())
    try:
        await iq.put(transcript())
        error = await wait_for(oq, lambda e: e.payload.get("code") == "plan_schema_rejected")
        assert "malicious secret" not in str(error.payload)
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(agent.executor.effects) == 1
        assert planner.count == 3
        assert agent.request_input_epoch == 1
        assert sum(agent.recovery_budget.values()) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("kind", ["pydantic", "json", "schema"])
async def test_malformed_model_outputs_share_one_bounded_retry(kind):
    class Planner:
        count = 0
        async def plan(self, view, tools):
            self.count += 1
            reject(kind)
    planner = Planner()
    agent, iq, oq, task = await start([], reasoner=planner)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.payload.get("code") == "no_progress_exhausted")
        assert planner.count == 2
        assert not agent.executor.effects
        assert agent.request_input_epoch == 1
    finally:
        await end(iq, task)


async def test_tool_triggered_validation_retry_cannot_create_spoken_write_authority():
    class Planner:
        count = 0
        async def plan(self, view, tools):
            self.count += 1
            if self.count == 1:
                proposal = read_plan(False)
                proposal.write_requested = False
                return proposal
            if self.count == 2:
                reject("pydantic")
            return write_plan(view.results[-1].call_id)
    planner = Planner()
    agent, iq, oq, task = await start([], reasoner=planner, tools=CatalogTools(), manifests=manifests())
    try:
        await iq.put(transcript("Just search"))
        await wait_for(oq, lambda e: e.payload.get("code") == "no_progress_exhausted")
        assert not agent.write_intent_retained
        assert not agent.write_contracts
        assert not agent.executor.effects
        assert planner.count == 3
    finally:
        await end(iq, task)


@pytest.mark.parametrize("source", [{}, {"source_call_id": "r", "source_call_index": 0}])
def test_binding_json_schema_exposes_exclusive_source_requirement(source):
    from jsonschema import ValidationError, validate
    from accessflow.contracts import ResultBinding
    with pytest.raises(ValidationError):
        validate({"slot": "id", "collection_pointer": "/items", "value_pointer": "/id",
                  "match_slots": {"/time": "requested_time"}, **source}, ResultBinding.model_json_schema())
