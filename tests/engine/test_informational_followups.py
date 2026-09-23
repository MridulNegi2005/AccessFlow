"""Final replies have request scope; historical unknown effects remain protected."""
import asyncio

import pytest

from accessflow.contracts import PlanProposal
from accessflow.fakes import FakeTools, ScriptedReasoner
from test_safety import end, proposal, start, transcript, wait_for


async def test_first_write_proposal_cannot_claim_completion_without_dispatch():
    reasoner = ScriptedReasoner([
        PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                     write_requested=True, request_complete=True, response="Booked Wednesday"),
        PlanProposal(clarification="Which service location?", write_requested=True)])
    agent, iq, oq, task = await start([], reasoner=reasoner)
    try:
        await iq.put(transcript())
        seen = []
        async with asyncio.timeout(2):
            while True:
                event = await oq.get()
                seen.append(event)
                if event.kind in {"final", "clarify"}:
                    break
        assert not any(event.kind == "final" for event in seen)
        assert seen[-1].kind == "clarify"
        assert not agent.executor.calls
        assert agent.write_intent_retained
    finally:
        await end(iq, task)


async def test_information_after_a_confirmed_failed_write_can_finish():
    reasoner = ScriptedReasoner([proposal(), PlanProposal(response="Support opens at nine.", request_complete=True)])
    agent, iq, oq, task = await start([], tools=FakeTools(outcome="failed"), reasoner=reasoner)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.payload.get("code") == "tool_failed")
        old_request = agent.request_id
        assert agent.last_request_finished
        await iq.put(transcript("What time does support open?", utterance="question"))
        answer = await wait_for(oq, lambda e: e.kind == "final")
        assert answer.payload["basis"] == "informational"
        assert agent.request_id != old_request
        assert not agent.executor.effects
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)


async def test_each_answered_information_turn_rotates_request_on_next_input():
    reasoner = ScriptedReasoner([PlanProposal(response=text, request_complete=True)
                                for text in ["First answer", "Second answer", "Third answer"]])
    agent, iq, oq, task = await start([], reasoner=reasoner)
    requests = []
    try:
        for number in range(3):
            event = transcript(f"Question {number}", utterance=f"turn-{number}")
            await iq.put(event)
            answer = await wait_for(oq, lambda e: e.kind == "final")
            assert answer.payload["caused_by_event_id"] == event.event_id
            assert answer.state.status == "listening"
            assert agent.last_request_finished
            requests.append(agent.request_id)
        assert len(set(requests)) == 3
        assert not agent.executor.calls
        assert [v.active_request_id for v in reasoner.views] == requests
    finally:
        await end(iq, task)


async def test_empty_followup_after_resolved_write_uses_bounded_recovery():
    reasoner = ScriptedReasoner([proposal(), PlanProposal(request_complete=True),
                                PlanProposal(clarification="Which support topic?")])
    agent, iq, oq, task = await start([], reasoner=reasoner)
    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        await iq.put(transcript("Explain the support hours", utterance="question"))
        await wait_for(oq, lambda e: e.payload.get("code") == "no_progress")
        clarification = await wait_for(oq, lambda e: e.kind == "clarify")
        assert clarification.payload["text"] == "Which support topic?"
        assert list(agent.recovery_budget.values()) == [1]
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


@pytest.mark.parametrize("uncertain_status", ["unknown", "cancelled"])
async def test_historical_uncertainty_blocks_model_prose_even_after_request_rotation(uncertain_status):
    # Fault-inject a historical ledger status to independently exercise the guard
    # when another request is active. This is not a real cancellation/rollback test.
    reasoner = ScriptedReasoner([proposal(), PlanProposal(response="Everything is done", request_complete=True)])
    agent, iq, oq, task = await start([], reasoner=reasoner)
    applied = asyncio.Event()
    original_apply = agent._apply

    async def observed_apply(plan, source=None):
        await original_apply(plan, source)
        applied.set()

    try:
        await iq.put(transcript())
        await wait_for(oq, lambda e: e.kind == "final")
        old_call = next(iter(agent.ledger.values()))
        old_call.status = uncertain_status
        agent._apply = observed_apply
        await iq.put(transcript("Is everything done?", utterance="question"))
        await asyncio.wait_for(applied.wait(), 2)
        emitted = []
        while not oq.empty():
            emitted.append(oq.get_nowait())
        assert agent.request_id != old_call.request_id
        assert not any(e.kind == "final" for e in emitted)
        assert not agent.last_request_finished
        assert old_call.status == uncertain_status
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)
