"""Transient read retry saves inference without bypassing lifecycle or write guards."""
import asyncio

import pytest

from accessflow.contracts import PlanProposal, ToolResult
from accessflow.fakes import FakeTools, ScriptedReasoner
from test_read_failure_recovery import FailThenRead
from test_safety import end, manifest, proposal, start, transcript, wait_for
from test_write_binding import CatalogTools, ChainedPlanner, manifests


def read():
    return proposal().model_copy(update={"write_requested": False})


async def test_fast_retry_preserves_identity_and_needs_no_failure_reasoning():
    tools = FailThenRead()
    reasoner = ScriptedReasoner([read(), PlanProposal(response="Available", request_complete=True)])
    agent, iq, oq, task = await start([], tools=tools, reasoner=reasoner,
                                     manifests=[manifest(effect="read")], fast_read_retry=True)
    try:
        await iq.put(transcript("Check Wednesday"))
        await wait_for(oq, lambda e: e.kind == "final")
        assert len(tools.calls) == len(reasoner.views) == 2
        first, retry = tools.calls
        assert retry.call_id != first.call_id
        assert retry.retry_of_call_id == first.call_id
        assert retry.operation_id == first.operation_id
        assert retry.arguments == first.arguments
        assert retry.dependencies == first.dependencies
        assert agent.call_causes[retry.call_id] == agent.call_causes[first.call_id]
        assert reasoner.views[-1].tool_failures[0].result == {}
        assert len(reasoner.views[-1].results) == 1
        assert agent._results_admitted == 2
    finally:
        await end(iq, task)


async def test_fast_and_model_retry_share_two_attempt_limit():
    tools = FailThenRead(always_fail=True)
    reasoner = ScriptedReasoner([read(), read(), PlanProposal(clarification="Lookup remains unavailable")])
    agent, iq, oq, task = await start([], tools=tools, reasoner=reasoner,
                                     manifests=[manifest(effect="read")], fast_read_retry=True)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert len(tools.calls) == 2
        assert list(agent.attempt_counts.values()) == [2]
        assert len(agent.tool_failures) == 2
    finally:
        await end(iq, task)


@pytest.mark.parametrize("error", ["invalid_args", "not_found", "corpus_unavailable", "unknown_tool"])
async def test_non_transient_failure_goes_to_planner_without_automatic_retry(error):
    class Tools(FailThenRead):
        async def execute(self, call):
            self.calls.append(call)
            return ToolResult(call_id=call.call_id, status="failed", error=error)
    tools = Tools()
    reasoner = ScriptedReasoner([read(), PlanProposal(clarification="Please correct the request")])
    _, iq, oq, task = await start([], tools=tools, reasoner=reasoner,
                                 manifests=[manifest(effect="read")], fast_read_retry=True)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "clarify")
        assert len(tools.calls) == 1
        assert reasoner.views[-1].tool_failures[0].error == error
    finally:
        await end(iq, task)


@pytest.mark.parametrize("fault", ["new_request", "new_epoch", "invalidated", "changed_dependency",
    "partial", "speech_not_ready", "correction", "finished", "stopped", "attempts_used",
    "replaced_call", "write", "pending", "invalid_arguments", "committed", "non_transient"])
async def test_retry_refuses_invalid_source_or_execution_state(fault):
    tools = FakeTools(gate=asyncio.Event())
    agent, iq, oq, task = await start([read()], tools=tools, manifests=[manifest(effect="read")],
                                     fast_read_retry=True)
    try:
        await iq.put(transcript())
        output = await wait_for(oq, lambda e: e.kind == "tool_call")
        call = agent.ledger[output.payload["call_id"]]
        call.status = "failed"
        result = ToolResult(call_id=call.call_id, status="failed", error="timeout")
        if fault == "new_request":
            agent.request_id = "different"
        elif fault == "new_epoch":
            agent.request_input_epoch += 1
        elif fault == "invalidated":
            agent.invalidated.add(call.call_id)
        elif fault == "changed_dependency":
            agent.state.slots["day"].revision += 1
        elif fault == "partial":
            agent.latest_complete = False
        elif fault == "speech_not_ready":
            agent.speech_ready = False
        elif fault == "correction":
            agent.state.correction_pending = True
        elif fault == "finished":
            agent.last_request_finished = True
        elif fault == "stopped":
            agent.state.status = "stopped"
        elif fault == "attempts_used":
            agent.attempt_counts[agent.call_signatures[call.call_id]] = 2
        elif fault == "replaced_call":
            agent.dispatched[agent.call_signatures[call.call_id]] = "another"
        elif fault == "write":
            call.effect = "write"
        elif fault == "pending":
            call.status = "pending"
        elif fault == "invalid_arguments":
            call.arguments["day"] = ["wrong type"]
        elif fault == "committed":
            result.committed = True
        elif fault == "non_transient":
            result.error = "invalid_args"
        assert not await agent._retry_read(call, result)
        assert len(agent.ledger) == 1
    finally:
        await end(iq, task)


async def test_retry_transfers_only_same_operation_binding_and_chain_completes():
    class Tools(CatalogTools):
        async def execute(self, call):
            if not self.calls:
                self.calls.append(call)
                return ToolResult(call_id=call.call_id, status="failed", error="timeout",
                                  result={"items": [{"id": "forged", "start": "08:00"}]})
            return await super().execute(call)
    planner = ChainedPlanner()
    tools = Tools()
    agent, iq, oq, task = await start([], tools=tools, manifests=manifests(), reasoner=planner,
                                     fast_read_retry=True)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        first, retry, write = tools.calls
        assert retry.retry_of_call_id == first.call_id
        assert retry.operation_id == first.operation_id
        assert agent.ledger[first.call_id].status == "failed"
        assert write.arguments["item_id"] == "opaque-17"
        rule = planner.views[-1].write_contracts[0].delegated_arguments["item_id"]
        assert rule.source_call_id == retry.call_id
        assert len(tools.effects) == 1
        assert len(planner.views) == 2
    finally:
        await end(iq, task)


@pytest.mark.parametrize("status", ["failed", "success"])
async def test_late_original_response_does_not_trigger_another_retry(status):
    tools = FailThenRead()
    reasoner = ScriptedReasoner([read(), PlanProposal(response="Available", request_complete=True)])
    agent, iq, oq, task = await start([], tools=tools, reasoner=reasoner,
                                     manifests=[manifest(effect="read")], fast_read_retry=True)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        await agent._result(ToolResult(call_id=tools.calls[0].call_id, status=status,
                                      result={"forged": "obsolete"}, error="timeout" if status == "failed" else None))
        assert len(agent.ledger) == 2
        assert len(reasoner.views) == 2
        assert all(r.call_id != tools.calls[0].call_id for r in agent.results)
    finally:
        await end(iq, task)
