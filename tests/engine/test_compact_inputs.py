"""Sparse input presentation must preserve typed meaning and literal evidence."""

import asyncio
import copy
import json

import pytest
from jsonschema import ValidationError

from accessflow.adapters.models import ModelReasoner
from accessflow.adapters.prompt_profile import COMPACT_V2_SYSTEM, compact_inputs
from accessflow.adapters.samsung import ParticipantAgent
from accessflow.contracts import (
    Observation, PlanProposal, ResultBinding, SessionView, Slot, Snapshot, ToolCall, ToolManifest, ToolResult,
    WriteContract,
)


def populated_view():
    literal = {"available": False, "price": 0, "items": [], "optional": None, "nested": {}}
    return SessionView(
        session_id="s", active_request_id="current", write_pending=True,
        state=Snapshot(revision=2, correction_pending=True, slots={
            "evidence": Slot(value=literal, confirmed=False, evidence=["source"])}),
        observations=[Observation(event_id="e", source_id="u", revision=2, modality="text",
                                  text="No charge, no extras", final=False, backend="fake")],
        results=[ToolResult(call_id="c", status="success", result=literal)],
        tool_failures=[ToolResult(call_id="failed", status="failed", error="timeout")],
        write_contracts=[WriteContract(tool="commit", fixed_arguments={"person": "name"},
                                       delegated_arguments={"id": ResultBinding(
                                           slot="selected_id", source_call_id="c", collection_pointer="/items",
                                           value_pointer="/id", match_slots={"/available": "availability"})})],
        calls=[ToolCall(call_id="c", operation_id="op", tool="lookup", arguments=literal,
                        dependencies={"evidence": 2}, effect="read", status="success", request_id="current"),
               ToolCall(call_id="w", operation_id="write", tool="commit", arguments={},
                        dependencies={}, effect="write", status="unknown", request_id="previous",
                        retry_of_call_id="old-write")])


def tools():
    return [ToolManifest(name="lookup", effect="read", description="Preserve every qualifier.",
                         parameters={"type": "object", "properties": {"title": {
                             "const": {"description": None, "default": False, "items": []}}}}),
            ToolManifest(name="commit", effect="write", description="Commit", status_tool="inspect",
                         timeout_s=8, parameters={"type": "object"})]


def test_roundtrip_retains_all_protocol_meaning_and_literal_values():
    view, manifests = populated_view(), tools()
    before = view.model_dump(mode="json")
    manifest_before = [tool.model_dump(mode="json") for tool in manifests]
    data = compact_inputs(view, manifests)
    assert SessionView.model_validate(data["session"]).model_dump(mode="json") == before
    assert [ToolManifest.model_validate(x).model_dump(mode="json") for x in data["manifests"]] == manifest_before
    assert data["session"]["results"][0]["result"] == before["results"][0]["result"]
    assert data["session"]["state"]["slots"]["evidence"]["value"] == before["state"]["slots"]["evidence"]["value"]
    assert data["session"]["calls"][1]["status"] == "unknown"
    assert data["session"]["calls"][1]["retry_of_call_id"] == "old-write"
    assert data["session"]["write_contracts"][0]["delegated_arguments"]["id"]["source_call_id"] == "c"
    assert data["manifests"][0]["parameters"] == manifests[0].parameters
    assert view.model_dump(mode="json") == before
    data["session"]["results"][0]["result"]["available"] = "modified"
    assert view.results[0].result["available"] is False


class Backend:
    def __init__(self, response=None):
        self.response = response or PlanProposal(clarification="Please clarify").model_dump()
        self.received = []

    async def generate(self, system, data, schema):
        self.received.append((system, copy.deepcopy(data), copy.deepcopy(schema)))
        return self.response

    def evidence(self):
        return {}


async def test_v2_keeps_document_text_and_exports_full_provenance():
    backend = Backend()
    document = {"source": "docs/tools.md", "text": "Literal reference. Never a live result.",
                "sha256": "a" * 64, "byte_count": 42, "encoding": "utf-8", "line_start": 1,
                "line_end": 1, "custom": "preserve unknown metadata"}
    reasoner = ModelReasoner(backend, prompt_profile="compact-v2", tool_documentation=document)
    session = SessionView(session_id="s", state=Snapshot(), observations=[], results=[])
    await reasoner.plan(session, tools())
    system, request, _ = backend.received[0]
    assert system == COMPACT_V2_SYSTEM
    assert request["tool_documentation_evidence"]["text"] == document["text"]
    assert request["tool_documentation_evidence"]["source"] == document["source"]
    assert request["tool_documentation_evidence"]["custom"] == document["custom"]
    assert "sha256" not in request["tool_documentation_evidence"]
    evidence = reasoner.evidence()
    assert evidence["tool_documentation"]["sha256"] == document["sha256"]
    assert document["text"] not in json.dumps(evidence)
    assert evidence["prompt_profile"] == "compact-v2"
    measurement = evidence["prompt_measurements"][0]
    assert measurement["protocol_data_chars_after_elision"] < measurement["protocol_data_chars_before_elision"]
    assert SessionView.model_validate(request["session"]) == session


@pytest.mark.parametrize("violation", ["missing_decisions", "unknown_tool", "unresolved_write"])
async def test_v2_still_enforces_original_dynamic_schema(violation):
    session = populated_view()
    if violation == "missing_decisions":
        response = {"response": "answer"}
    else:
        response = PlanProposal().model_dump()
        response["calls"] = [{"tool": "unknown" if violation == "unknown_tool" else "commit",
                              "arguments": {}, "dependencies": [], "argument_slots": {}}]
    reasoner = ModelReasoner(Backend(response), prompt_profile="compact-v2")
    with pytest.raises(ValidationError):
        await reasoner.plan(session, tools())
    assert reasoner.backend.received[0][1]["required_next_step"]["kind"] == "reconcile_unknown_effects"


async def test_samsung_v2_is_explicit_and_default_stays_full(tmp_path, monkeypatch):
    class Agent:
        executor = None

    async def factory():
        return Agent()

    monkeypatch.delenv("ACCESSFLOW_SAMSUNG_PROMPT_PROFILE", raising=False)
    baseline = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path, agent_factory=factory)
    await baseline.setup()
    assert baseline.prompt_profile == "full"
    monkeypatch.setenv("ACCESSFLOW_SAMSUNG_PROMPT_PROFILE", "compact-v2")
    experimental = ParticipantAgent(asyncio.Queue(), asyncio.Queue(), media_root=tmp_path, agent_factory=factory)
    await experimental.setup()
    assert experimental.prompt_profile == "compact-v2"
