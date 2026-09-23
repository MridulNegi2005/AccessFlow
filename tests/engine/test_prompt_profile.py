"""Compact presentation must preserve schema meaning and full local enforcement."""
import copy
import json

import httpx
from jsonschema import Draft202012Validator, ValidationError
import pytest

from accessflow.adapters.models import JsonBackend, ModelReasoner, SYSTEM
from accessflow.adapters.prompt_profile import COMPACT_SYSTEM, compact_schema
from accessflow.contracts import PlanProposal, SessionView, Snapshot, ToolManifest


def view():
    return SessionView(session_id="s", state=Snapshot(), observations=[], results=[], calls=[])


def test_annotations_are_removed_only_at_schema_positions():
    original = {"title": "Friendly name", "description": "Documentation", "default": {},
                "type": "object", "properties": {
                    "title": {"type": "string", "title": "Title"},
                    "payload": {"const": {"description": "literal", "default": 7, "title": 3}},
                    "choice": {"enum": [{"description": "real data"}]},
                }, "required": ["title"], "additionalProperties": False,
                "x-extension": {"description": "preserved unknown semantics"}}
    before = copy.deepcopy(original)
    compact = compact_schema(original)
    assert "description" not in compact and "title" not in compact
    assert compact["properties"]["title"] == {"type": "string"}
    assert compact["properties"]["payload"] == original["properties"]["payload"]
    assert compact["properties"]["choice"] == original["properties"]["choice"]
    assert compact["x-extension"] == original["x-extension"]
    assert original == before


@pytest.mark.parametrize("require_progress", [True, False])
@pytest.mark.parametrize("allow_write", [True, False])
def test_dynamic_schema_acceptance_is_unchanged(require_progress, allow_write):
    manifests = [ToolManifest(name="opaque_read", description="Read", effect="read", parameters={"type": "object"}),
                 ToolManifest(name="opaque_write", description="Write", effect="write", parameters={"type": "object"})]
    full = ModelReasoner.output_schema(manifests, allow_write_calls=allow_write,
                                      allow_final_response=not require_progress,
                                      require_progress=require_progress)
    small = compact_schema(full)
    samples = [{}, PlanProposal().model_dump(),
               PlanProposal(clarification="Which item?").model_dump(),
               PlanProposal(response="A response", request_complete=True).model_dump()]
    for name in ["opaque_read", "opaque_write", "not_in_manifest"]:
        item = PlanProposal(request_complete=True).model_dump()
        item["calls"] = [{"tool": name, "arguments": {}, "dependencies": [], "argument_slots": {}}]
        samples.append(item)
        broken = copy.deepcopy(item)
        del broken["calls"][0]["dependencies"]
        samples.append(broken)
    for sample in samples:
        assert Draft202012Validator(full).is_valid(sample) == Draft202012Validator(small).is_valid(sample)
    assert len(json.dumps(small)) < len(json.dumps(full)) * .75


@pytest.mark.parametrize("profile", ["full", "compact-v1"])
async def test_profile_preserves_input_evidence_and_records_presentation(profile):
    observed = []

    class Backend:
        async def generate(self, system, data, schema):
            observed.append((system, copy.deepcopy(data), schema))
            return PlanProposal(clarification="Please give more detail").model_dump()

        def evidence(self):
            return {}

    session = view()
    manifest = ToolManifest(name="description", description="Preserve this interface description",
                            effect="read", parameters={"type": "object", "properties": {
                                "title": {"type": "string", "description": "Meaning matters"}}})
    reasoner = ModelReasoner(Backend(), prompt_profile=profile)
    await reasoner.plan(session, [manifest])
    system, data, schema = observed[0]
    assert data["session"] == session.model_dump(mode="json")
    assert data["manifests"] == [manifest.model_dump(mode="json")]
    assert system == (SYSTEM if profile == "full" else COMPACT_SYSTEM)
    evidence = reasoner.evidence()
    assert evidence["prompt_profile"] == profile
    assert evidence["prompt_measurements"][0]["schema_chars"] == len(json.dumps(schema, separators=(",", ":")))
    evidence["prompt_measurements"][0]["schema_chars"] = 0
    assert reasoner.evidence()["prompt_measurements"][0]["schema_chars"] > 0


async def test_compact_http_profile_still_enforces_full_schema(monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "fake-unit-test-key")
    monkeypatch.setenv("ACCESSFLOW_MAX_CONTEXT_CHARS", "32768")
    seen = []

    def reply(request):
        seen.append(json.loads(request.content))
        # Pydantic defaults could fill this, but the full generation contract
        # requires the model to explicitly decide calls and completion.
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(reply)) as client:
        backend = JsonBackend("groq", client)
        reasoner = ModelReasoner(backend, prompt_profile="compact-v1")
        with pytest.raises(ValidationError):
            await reasoner.plan(view(), [])
        assert backend.evidence()["outcome_counts"]["failure"] == 1
        assert seen[0]["messages"][0]["content"] == COMPACT_SYSTEM


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError, match="profile"):
        ModelReasoner(object(), prompt_profile="automatic-fallback")
