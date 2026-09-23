"""Read failures must reach planning without authorizing or endlessly retrying writes."""

from accessflow.contracts import PlanProposal, ToolResult
from accessflow.fakes import ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


class FailThenRead:
    def __init__(self, always_fail=False):
        self.calls = []
        self.always_fail = always_fail

    async def execute(self, call):
        self.calls.append(call)
        if self.always_fail or len(self.calls) == 1:
            return ToolResult(call_id=call.call_id, status="failed", error="temporary_unavailable",
                              result={"untrusted_ticket_id": "NOT-A-CONFIRMED-RESULT"})
        return ToolResult(call_id=call.call_id, status="success", result={"available": True})

    async def cancel(self, call_id):
        return "unknown"


async def test_read_failure_replans_with_failure_evidence_and_retries_once():
    tools = FailThenRead()
    reasoner = ScriptedReasoner([
        proposal().model_copy(update={"write_requested": False}),
        proposal().model_copy(update={"write_requested": False}),
        PlanProposal(response="Wednesday is available.", request_complete=True),
    ])
    agent, incoming, outgoing, task = await start([], tools=tools, reasoner=reasoner,
                                                manifests=[manifest(effect="read")])
    try:
        await incoming.put(transcript("Check Wednesday"))
        final = await wait_for(outgoing, lambda e: e.kind == "final")
        assert "available" in final.payload["text"]
        assert len(tools.calls) == 2
        failure = reasoner.views[1].tool_failures[-1]
        assert failure.status == "failed" and failure.error == "temporary_unavailable"
        assert failure.result == {} and not failure.committed
        assert not reasoner.views[1].results
        assert agent._results_admitted == 2
    finally:
        await end(incoming, task)


async def test_second_read_failure_can_be_explained_without_third_dispatch():
    tools = FailThenRead(always_fail=True)
    reasoner = ScriptedReasoner([
        proposal().model_copy(update={"write_requested": False}),
        proposal().model_copy(update={"write_requested": False}),
        PlanProposal(clarification="The lookup is unavailable. Try later?"),
    ])
    _, incoming, outgoing, task = await start([], tools=tools, reasoner=reasoner,
                                            manifests=[manifest(effect="read")])
    try:
        await incoming.put(transcript("Check Wednesday"))
        clarification = await wait_for(outgoing, lambda e: e.kind == "clarify")
        assert "lookup is unavailable" in clarification.payload["text"]
        assert len(tools.calls) == 2
        assert not reasoner.views[-1].results
        assert [r.status for r in reasoner.views[-1].tool_failures] == ["failed", "failed"]
    finally:
        await end(incoming, task)


async def test_repeated_failed_read_is_not_dispatched_a_third_time():
    tools = FailThenRead(always_fail=True)
    read = proposal().model_copy(update={"write_requested": False})
    reasoner = ScriptedReasoner([read, read, read, PlanProposal(clarification="Lookup still unavailable.")])
    _, incoming, outgoing, task = await start([], tools=tools, reasoner=reasoner,
                                            manifests=[manifest(effect="read")])
    try:
        await incoming.put(transcript("Check Wednesday"))
        await wait_for(outgoing, lambda e: e.kind == "clarify")
        assert len(tools.calls) == 2
    finally:
        await end(incoming, task)


async def test_failed_read_replan_cannot_create_write_permission():
    tools = FailThenRead(always_fail=True)
    reasoner = ScriptedReasoner([
        proposal().model_copy(update={"write_requested": False}),
        proposal(name="write_service"),
    ])
    _, incoming, outgoing, task = await start([], tools=tools, reasoner=reasoner,
        manifests=[manifest(effect="read"), manifest(name="write_service")])
    try:
        await incoming.put(transcript("Check Wednesday"))
        await wait_for(outgoing, lambda e: e.payload.get("code") == "no_dispatchable_call")
        assert len(tools.calls) == 1
        assert tools.calls[0].effect == "read"
    finally:
        await end(incoming, task)

