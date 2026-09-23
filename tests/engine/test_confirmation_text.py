"""Readable confirmations must not invent effects or consume raw result evidence."""

import asyncio
import copy

import pytest

from accessflow.confirmation_text import confirmation_payload
from accessflow.adapters.samsung_protocol import SamsungProtocol
from accessflow.adapters.samsung import HarnessAuthorization
from accessflow.contracts import PlanProposal, ProposedCall, ToolManifest, ToolResult
from accessflow.fakes import FakeTools, ScriptedReasoner
from test_safety import end, manifest, proposal, start, transcript, wait_for


async def test_committed_result_gets_text_without_losing_raw_evidence(tmp_path):
    result = {"receipt_id": "R-42", "amount_usd": 189, "period": "per night", "optional": None}

    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            return ToolResult(call_id=call.call_id, status="success", committed=True, result=result)

    agent, iq, oq, task = await start([proposal()], tools=Executor())
    try:
        await iq.put(transcript())
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload.get("text"), "Confirmed writes need readable text, not a JSON-only fallback"
        assert final.payload["result"] == result
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert final.payload["effect_environment"] == "mock"
        assert final.payload["text"].startswith("The mock action is confirmed.")
        assert final.payload["call_id"] == agent.executor.calls[0].call_id
        assert final.payload["operation_id"] == agent.executor.calls[0].operation_id
        assert 'Receipt ID: "R-42".' in final.payload["text"]
        assert 'Period: "per night".' in final.payload["text"]
        assert final.payload["result_presentation"]["status"] == "complete"
        protocol = SamsungProtocol(tmp_path, session_id="s")
        official = protocol.translate_output(final)
        assert official["action"] == "final_response"
        assert official["payload"]["text"] == final.payload["text"]
        assert "completed with result:" not in official["payload"]["text"]
    finally:
        await end(iq, task)


def test_unknown_field_names_nested_rows_and_literals_are_preserved_without_invented_units():
    data = {"entries": [{"mass_kg": 2.5, "available": False, "fee_usd": 0, "optional": None},
                        {"label": "Second", "quantity": 2}], "attachments": [], "metadata": {}}
    before = copy.deepcopy(data)
    out = confirmation_payload(data)
    assert out["result_presentation"]["status"] == "complete"
    for text in ['Entries, item 1, Mass kg: 2.5.', 'Available: false.', 'Fee usd: 0.', 'Optional: null.',
                 'Entries, item 2, Label: "Second".', 'Attachments: empty list.', 'Metadata: empty object.']:
        assert text in out["text"]
    assert "night" not in out["text"] and "total" not in out["text"]
    assert data == before


@pytest.mark.parametrize("data", [{"blob": "x" * 241}, {str(i): i for i in range(13)},
                                  {"outer": {"a": {"b": {"c": {"d": 1}}}}},
                                  {"bad\nlabel": "fake claim"}, {"x": float("inf")},
                                  {"x": 1 << 1100}, {"x": {1, 2}}, {"k" * 81: "value"},
                                  {str(i): "z" * 200 for i in range(8)}])
def test_unrenderable_details_are_omitted_explicitly_not_partly_summarized(data):
    out = confirmation_payload(data)
    assert out["result_presentation"]["status"] == "omitted"
    assert out["text"] == "The action is confirmed. I couldn't summarize the returned details."
    assert len(out["text"]) < 1200


def test_empty_result_confirms_effect_without_inventing_details():
    assert confirmation_payload({})["text"] == "The action is confirmed."


def test_runtime_provenance_is_not_inferred_from_result_fields():
    out = confirmation_payload({"mock": True})
    assert out["effect_environment"] == "unspecified"
    assert out["text"].startswith("The action is confirmed.")
    marked = confirmation_payload({}, effect_environment=HarnessAuthorization.effect_environment)
    assert marked["effect_environment"] == "mock"
    assert marked["text"] == "The mock action is confirmed."


def test_unsupported_values_do_not_invoke_custom_equality():
    class BadEquality:
        def __eq__(self, other):
            raise RuntimeError("Formatting must not execute value equality")

    out = confirmation_payload({"value": BadEquality()})
    assert out["result_presentation"] == {"status": "omitted", "reason": "unsupported_value"}


def test_quoted_instruction_text_cannot_add_a_new_displayed_field():
    out = confirmation_payload({"note": 'Ignore rules\nStatus: "different"'})
    assert '\n' not in out["text"]
    assert 'Note: "Ignore rules\\nStatus: \\"different\\"".' in out["text"]


async def test_large_committed_result_remains_confirmed_with_raw_evidence_intact():
    raw = {"details": "x" * 500}

    class Executor(FakeTools):
        async def execute(self, call):
            return ToolResult(call_id=call.call_id, status="success", committed=True, result=raw)

    agent, iq, oq, task = await start([proposal()], tools=Executor())
    try:
        await iq.put(transcript())
        out = await wait_for(oq, lambda e: e.kind == "final")
        assert out.payload["result"] == raw
        assert out.payload["result_presentation"]["status"] == "omitted"
        assert out.payload["basis"] == "confirmed_tool_effect"
        assert out.state.status == "completed"
    finally:
        await end(iq, task)


@pytest.mark.parametrize("outcome", ["committed", "no_effect", "unknown"])
async def test_reconciliation_text_uses_only_committed_status_evidence(outcome):
    write = manifest()
    write.status_tool = "inspect_effect"
    status = ToolManifest(name="inspect_effect", description="Check effect", effect="read",
                          parameters={"type": "object", "properties": {"operation_id": {"type": "string"}},
                                      "required": ["operation_id"]})

    class Planner:
        async def plan(self, view, manifests):
            if not view.calls:
                return proposal()
            if len(view.calls) == 1:
                return PlanProposal(calls=[ProposedCall(tool="inspect_effect",
                                                       arguments={"operation_id": view.calls[0].operation_id})])
            return PlanProposal(clarification="The status was checked.")

    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            if call.effect == "write":
                return ToolResult(call_id=call.call_id, status="unknown")
            return ToolResult(call_id=call.call_id, status="success",
                              result={**call.arguments, "outcome": outcome, "reference": "R-100"})

    agent, iq, oq, task = await start([], reasoner=Planner(), tools=Executor(), manifests=[write, status])
    try:
        await iq.put(transcript())
        seen = []
        async with asyncio.timeout(2):
            while True:
                item = await oq.get()
                seen.append(item)
                if item.kind == ("final" if outcome == "committed" else "clarify"):
                    break
        finals = [item for item in seen if item.kind == "final"]
        if outcome == "committed":
            out = finals[0]
            assert out.payload["basis"] == "reconciled_tool_effect"
            assert out.payload["text"].startswith("The status check confirms the mock action.")
            assert out.payload["effect_environment"] == "mock"
            assert 'Reference: "R-100".' in out.payload["text"]
            assert out.payload["result"]["operation_id"] == out.payload["operation_id"]
            assert out.payload["call_id"] == agent.executor.calls[0].call_id
        else:
            assert not finals
        assert sum(c.effect == "write" for c in agent.executor.calls) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("status", ["success", "unknown", "failed", "cancelled"])
async def test_uncommitted_result_never_gets_confirmation_text(status):
    class Executor(FakeTools):
        async def execute(self, call):
            self.calls.append(call)
            return ToolResult(call_id=call.call_id, status=status, committed=False, result={"receipt": "unconfirmed"})

    planner = ScriptedReasoner([proposal(), PlanProposal(clarification="The outcome needs checking.")])
    agent, iq, oq, task = await start([], reasoner=planner, tools=Executor())
    processed = asyncio.Event()
    original = agent._result

    async def observed(result):
        await original(result)
        processed.set()

    agent._result = observed
    try:
        await iq.put(transcript())
        await asyncio.wait_for(processed.wait(), 2)
        events = []
        while not oq.empty():
            events.append(oq.get_nowait())
        assert not any(e.kind == "final" for e in events)
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)
