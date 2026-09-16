import asyncio
import json
from pathlib import Path

from accessflow.contracts import PlanProposal, ToolResult
from accessflow.evaluation.replay import metrics, replay
from accessflow.fakes import FakeTools
from test_safety import end, proposal, start, transcript, wait_for


async def test_corrected_request_resumes_after_cancellation_is_confirmed():
    cancellation_confirmed = asyncio.Event()
    hold_first = asyncio.Event()

    class Executor(FakeTools):
        async def execute(self, call):
            if not self.calls:
                self.calls.append(call)
                await hold_first.wait()
                return ToolResult(call_id=call.call_id, status="cancelled")
            return await super().execute(call)

        async def cancel(self, call_id):
            await cancellation_confirmed.wait()
            return await super().cancel(call_id)

    class Planner:
        async def plan(self, view, manifests):
            day = "Wednesday" if "Wednesday" in view.observations[-1].text else "Tuesday"
            return proposal(day)

    agent, iq, oq, task = await start([], tools=Executor(), reasoner=Planner())
    try:
        await iq.put(transcript("Book Tuesday"))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(transcript("Actually Wednesday", revision=1))
        await wait_for(oq, lambda e: e.kind == "clarify")
        cancellation_confirmed.set()
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.state.slots["day"].value == "Wednesday"
        assert len(agent.executor.effects) == 1
    finally:
        cancellation_confirmed.set()
        hold_first.set()
        await end(iq, task)


async def test_replay_keeps_failed_run_and_shutdown_evidence(tmp_path):
    scenario = json.loads((Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json").read_text())
    scenario["completion_timeout_s"] = 0.02
    scenario["event_spacing_s"] = 0
    scenario["proposals"] = [{}, {}]
    source = tmp_path / "scenario.json"
    source.write_text(json.dumps(scenario))
    trace = tmp_path / "trace.jsonl"
    result = await replay(source, trace)
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert result["completion_status"] == "timeout"
    assert rows[0]["completion_status"] == "timeout"
    assert rows[-1]["type"] == "output"
    assert rows[-1]["event"]["state"]["status"] == "ended"
    assert metrics(trace)["slot_accuracy"] is None


async def test_live_replay_does_not_require_scripted_model_answers(tmp_path):
    scenario = json.loads((Path(__file__).resolve().parents[2] / "scenarios/dev/text_correction.json").read_text())
    del scenario["proposals"]
    source = tmp_path / "scenario.json"
    source.write_text(json.dumps(scenario))

    class Provider:
        async def plan(self, view, manifests):
            return PlanProposal(response="Test provider response")

    result = await replay(source, tmp_path / "trace.jsonl", reasoner=Provider(), backend="test-provider-double")
    assert result["completion_status"] == "completed"
    assert result["mock_effects"] == 0
