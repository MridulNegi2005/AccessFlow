"""The diagnostic runner must retain failed attempts and protect evidence files."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.run_samsung_check import execute, resolve_scenario, write_report


def participant():
    reasoner = SimpleNamespace(evidence=lambda: {"backend": "test-double"}, plans=[])
    return SimpleNamespace(agent=SimpleNamespace(reasoner=reasoner), diagnostics=[])


async def test_setup_failure_does_not_run_scenario():
    class Harness:
        trace = []

        async def prepare(self):
            pass

        async def run(self):
            pytest.fail("Failed setup must not be graded as a completed scenario")

    result = await execute(Harness(), [SimpleNamespace(agent=None, diagnostics=[])])
    assert result["failure"] == "setup_failed"
    assert result["model_evidence"] is None


async def test_scenario_timeout_preserves_partial_trace_and_cancels_run():
    stopped = asyncio.Event()

    class Harness:
        trace = [{"kind": "event", "event_type": "tool_manifest"}]

        async def prepare(self):
            pass

        async def run(self):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()

    result = await execute(Harness(), [participant()], wall_cap=0.01)
    assert result["failure"] == "scenario_timeout"
    assert result["trace"] == Harness.trace
    assert stopped.is_set()


async def test_agent_crash_trace_is_an_incomplete_attempt():
    class Harness:
        async def prepare(self):
            pass

        async def run(self):
            return [{"kind": "agent_crash", "error": "TestFailure"}]

    result = await execute(Harness(), [participant()])
    assert result["failure"] == "agent_crash"


def test_reports_redact_keys_and_never_overwrite_prior_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCESSFLOW_GROQ_API_KEY", "test-token-never-publish")
    target = tmp_path / "report.json"
    write_report(target, {"error": "echo test-token-never-publish"})
    before = target.read_bytes()
    assert json.loads(before)["error"] == "echo [REDACTED]"
    with pytest.raises(FileExistsError):
        write_report(target, {"replacement": True})
    assert target.read_bytes() == before


def test_external_development_input_has_explicit_origin_without_changing_public_rules(tmp_path):
    kit = tmp_path / "kit"
    (kit / "scenarios").mkdir(parents=True)
    public = kit / "scenarios" / "public.json"
    public.write_text('{}')
    generated = tmp_path / "generated.json"
    generated.write_text('{}')
    assert resolve_scenario(kit, name="public.json") == (public.resolve(), "public-development")
    assert resolve_scenario(kit, external_path=generated) == (generated.resolve(), "external-development")
    for bad in ["../generated.json", str(generated), "missing.json", "public.txt"]:
        with pytest.raises(ValueError):
            resolve_scenario(kit, name=bad)
    with pytest.raises(ValueError):
        resolve_scenario(kit, external_path=tmp_path)


@pytest.mark.parametrize("selection", [{}, {"name": "a.json", "external_path": "b.json"}])
def test_scenario_selection_requires_exactly_one_input(tmp_path, selection):
    with pytest.raises(ValueError, match="exactly one"):
        resolve_scenario(tmp_path, **selection)
