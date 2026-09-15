"""Acceptance tests for R3: require progress or an explicit bounded outcome.

See docs/reviews/CLAUDE_REVIEW_2026-09-15.md, "R3 -- Require progress or an explicit
bounded outcome". Each test below is written to fail against the pre-fix engine: a
fully expanded PlanProposal() validates cleanly even while a write is outstanding,
invalid-only or mixed proposals leave nothing to wake the loop, and a request that
already used one recovery mechanism's single-shot budget could still draw a second,
independent attempt from a different mechanism forever.
"""
import asyncio

from accessflow.contracts import PlanProposal, ProposedCall
from accessflow.fakes import FakeTools
from test_safety import end, manifest, start, transcript, wait_for


async def test_empty_plan_while_a_write_is_owed_is_diagnosed_and_recovers():
    read_tool = manifest(effect="read", name="availability_check")
    write_tool = manifest(effect="write", name="file_visit_request")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    request_complete=True, write_requested=True,
                                    calls=[ProposedCall(tool="availability_check", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            if self.n == 2:
                # The exact R3 repro: a fully expanded, empty PlanProposal while the
                # write is still owed. Previously this validated against the
                # outstanding-write schema and the controller did nothing at all.
                return PlanProposal()
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                request_complete=True, write_requested=True,
                                calls=[ProposedCall(tool="file_visit_request", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[read_tool, write_tool])
    try:
        await iq.put(transcript("Check availability and book Wednesday"))
        stalled = await wait_for(oq, lambda e: e.payload.get("code") == "write_owed_not_progressed")
        assert "empty" in stalled.payload["message"]
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["basis"] == "confirmed_tool_effect"
        assert len(agent.executor.effects) == 1
    finally:
        await end(iq, task)


async def test_repeated_read_then_successful_repair_dispatches_new_work():
    read_tool = manifest(effect="read", name="check_wednesday")
    other_tool = manifest(effect="read", name="check_thursday")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n in (1, 2):
                # Turn 2 re-proposes the same already-completed read: no progress.
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            # The bounded repair: the reasoner reads the evidence and tries something new.
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                calls=[ProposedCall(tool="check_thursday", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[read_tool, other_tool])
    try:
        await iq.put(transcript("Check Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "repeated_completed_call")
        # Validate the retry's actual OUTCOME, not merely that _start_plan ran: a
        # genuinely different call must land.
        repaired = await wait_for(oq, lambda e: e.kind == "tool_call" and e.payload["tool"] == "check_thursday")
        assert repaired.payload["tool"] == "check_thursday"
        assert len(agent.ledger) == 2
        assert agent.repeat_recoveries[agent.request_id] == 1
        # Drawn from the shared, request/input-revision-scoped budget.
        assert agent.recovery_budget[(agent.request_id, agent.request_input_epoch)] == 1
    finally:
        await end(iq, task)


async def test_repeated_read_then_repeated_read_again_ends_explicitly():
    read_tool = manifest(effect="read", name="check_wednesday")

    class Looping:
        async def plan(self, view, manifests):
            # Always re-proposes the same read: never makes progress, whatever
            # feedback the controller gives it.
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Looping(), manifests=[read_tool])
    try:
        await iq.put(transcript("Check Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "repeated_completed_call")
        # No unlimited model calls, no unexplained wait to the scenario deadline:
        # the second no-progress turn ends the request explicitly instead of
        # granting a third attempt.
        exhausted = await wait_for(oq, lambda e: e.payload.get("code") == "no_progress_exhausted")
        assert exhausted.kind == "error"
        assert agent.last_request_finished
        for _ in range(30):
            await asyncio.sleep(0)
        # Still exactly one dispatch ever: no duplicate effect, no false success.
        assert len(agent.executor.calls) == 1
    finally:
        await end(iq, task)


async def test_malformed_dependency_then_one_correction_dispatches():
    tool = manifest(effect="read", name="lookup")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                # "day" was never established as a slot: an invalid dependency.
                return PlanProposal(calls=[ProposedCall(tool="lookup", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                calls=[ProposedCall(tool="lookup", arguments={"day": "Wednesday"},
                                                    dependencies=["day"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[tool])
    try:
        await iq.put(transcript("Look up Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "missing_dependency")
        recovered = await wait_for(oq, lambda e: e.kind == "tool_call")
        assert recovered.payload["tool"] == "lookup"
        assert len(agent.ledger) == 1
    finally:
        await end(iq, task)


async def test_pending_tool_with_no_new_call_stays_waiting_not_a_stall():
    gate = asyncio.Event()
    read_tool = manifest(effect="read", name="check_wednesday")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            # Nothing new to add while the first read is still in flight.
            return PlanProposal()

    executor = FakeTools(gate=gate)
    agent, iq, oq, task = await start([], reasoner=Planner(), tools=executor, manifests=[read_tool])
    try:
        await iq.put(transcript("Check Wednesday", utterance="u1"))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        # A second, later revision of the same utterance re-triggers planning while
        # the read is still pending.
        await iq.put(transcript("Check Wednesday please", utterance="u1", revision=1))
        for _ in range(30):
            await asyncio.sleep(0)
        drained = []
        while not oq.empty():
            drained.append(oq.get_nowait())
        assert not any(e.kind == "error" for e in drained)
        assert agent.state.status != "no_progress"
        # The shared no-progress budget must never have been touched: this was a
        # legitimate wait, not a stall.
        assert agent.no_progress is False
        assert not agent.recovery_budget
        gate.set()
        result = await wait_for(oq, lambda e: e.payload.get("basis") == "tool_evidence")
        assert result.payload["basis"] == "tool_evidence"
    finally:
        gate.set()
        await end(iq, task)


async def test_partial_speech_with_no_plan_is_not_treated_as_a_stall():
    class Planner:
        async def plan(self, view, manifests):
            return PlanProposal()

    agent, iq, oq, task = await start([], reasoner=Planner())
    try:
        await iq.put(transcript("Book, actually", final=False))
        for _ in range(30):
            await asyncio.sleep(0)
        assert oq.empty()
        assert agent.state.status != "no_progress"
        assert agent.no_progress is False
        assert not agent.recovery_budget
    finally:
        await end(iq, task)


async def test_new_utterance_during_recovery_invalidates_the_stale_repair():
    release = asyncio.Event()
    read_tool = manifest(effect="read", name="check_wednesday")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n in (1, 2):
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            if self.n == 3:
                # The bounded repair attempt: held open until new speech has already
                # been accepted, so this stale result must never be applied.
                await release.wait()
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            return PlanProposal(response="Checking Thursday instead.", request_complete=True)

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[read_tool])
    try:
        await iq.put(transcript("Check Wednesday", utterance="u1"))
        await wait_for(oq, lambda e: e.payload.get("code") == "repeated_completed_call")
        for _ in range(10):
            await asyncio.sleep(0)  # let the held recovery attempt actually start
        await iq.put(transcript("Actually check Thursday", utterance="u1", revision=1))
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["text"] == "Checking Thursday instead."
        release.set()
        for _ in range(30):
            await asyncio.sleep(0)
        # The stale recovery's read must not have landed a second time.
        assert len([c for c in agent.executor.calls if c.tool == "check_wednesday"]) == 1
        # The new utterance earned its own input-revision epoch rather than
        # inheriting the older, already-consumed recovery budget.
        assert agent.request_input_epoch >= 2
    finally:
        release.set()
        await end(iq, task)


async def test_second_request_gets_a_fresh_budget_after_the_first_was_exhausted():
    read_tool = manifest(effect="read", name="check_wednesday")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n <= 3:
                # Request A: repeats the same completed read until its budget runs out.
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            # Request B: an unrelated, answerable informational request.
            return PlanProposal(response="Our hours are nine to five.", request_complete=True)

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[read_tool])
    try:
        await iq.put(transcript("Check Wednesday", utterance="u1"))
        await wait_for(oq, lambda e: e.payload.get("code") == "no_progress_exhausted")
        assert agent.last_request_finished
        exhausted_request = agent.request_id
        await iq.put(transcript("What are your hours", utterance="u2"))
        final = await wait_for(oq, lambda e: e.kind == "final")
        assert final.payload["text"] == "Our hours are nine to five."
        assert agent.request_id != exhausted_request
    finally:
        await end(iq, task)


async def test_mixed_repeated_and_invalid_calls_get_an_accurate_message():
    read_tool = manifest(effect="read", name="check_wednesday")
    other_tool = manifest(effect="read", name="lookup_other")

    class Planner:
        def __init__(self):
            self.n = 0

        async def plan(self, view, manifests):
            self.n += 1
            if self.n == 1:
                return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                        dependencies=["day"])])
            # Mixed: repeats the completed read AND proposes a call with an
            # ungrounded dependency in the same turn.
            return PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                calls=[ProposedCall(tool="check_wednesday", arguments={"day": "Wednesday"},
                                                    dependencies=["day"]),
                                       ProposedCall(tool="lookup_other", arguments={"ref": "x"},
                                                    dependencies=["ref"])])

    agent, iq, oq, task = await start([], reasoner=Planner(), manifests=[read_tool, other_tool])
    try:
        await iq.put(transcript("Check Wednesday"))
        await wait_for(oq, lambda e: e.payload.get("code") == "missing_dependency")
        mixed = await wait_for(oq, lambda e: e.payload.get("code") == "repeated_completed_call")
        message = mixed.payload["message"].lower()
        assert "every proposed call has already completed" not in message
        assert "not every call is done" in message
    finally:
        await end(iq, task)
