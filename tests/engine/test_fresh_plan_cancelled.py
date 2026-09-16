"""Security review LOW 1 (2026-09-16): Agent._fresh_plan_cancelled entries are
recorded, per (request_id, request_input_epoch), when a fresh-evidence planner task
is pre-empted before delivering a proposal -- see the comment in Agent._start_plan
(src/accessflow/engine.py). An entry is consumed (popped) once, letting a same-epoch,
non-fresh replan retain the write authority the pre-empted fresh plan would have
established (see the speech_origin block in Agent._apply).

request_input_epoch is a single counter that only ever grows, never reset even
across request_id rotation (see Agent.run()). A non-fresh proposal only ever pops
the entry keyed to the CURRENT epoch, so an entry recorded under any other,
now-superseded epoch can never be popped again: it is dead the instant the epoch
advances past it, not merely stale. Left unpruned, one such entry accumulated for
the life of the session for every fresh plan a later piece of fresh evidence
pre-empted before it could deliver -- the reviewer measured 25 sets against 3
consumes on the engine suite.

The two tests below are the pruning fix's acceptance pair: a long run of exactly
that always-unconsumable pre-emption must not grow the dict, and the one
legitimate same-epoch hand-off it exists for must still work.
"""
import asyncio

from accessflow.contracts import PlanProposal
from test_safety import end, start, transcript


class HangingPlanner:
    """A reasoner whose plan() never resolves on its own -- only ever cancelled by
    the next _start_plan(), so the planner it produces is always still "in flight"
    for the next pre-emption.
    """
    async def plan(self, view, manifests):
        await asyncio.Event().wait()


async def test_long_run_of_preempted_fresh_plans_does_not_grow_fresh_plan_cancelled():
    """Repeated fresh evidence (e.g. a fast talker's partial utterances) that keeps
    pre-empting an in-flight fresh plan before it can ever deliver is exactly the
    always-unconsumable case: request_input_epoch is bumped by the very pre-emption
    that would record the entry, so any such entry is already stale at the moment
    of insertion. Before the fix this left one dead entry behind per pre-emption;
    here 30 of them, well past the review's 25-call sample, must leave none.
    """
    agent, iq, oq, task = await start([], reasoner=HangingPlanner())
    try:
        await iq.put(transcript("Book Wednesday", final=False))
        for _ in range(30):
            await asyncio.sleep(0)
        assert agent.planner is not None and not agent.planner.done()
        # Each call below mirrors what a new partial-speech observation does inside
        # _worker: source is not None, so it is fresh evidence that bumps
        # request_input_epoch and pre-empts whatever fresh plan is still in flight.
        key = ("speech", "u")
        for _ in range(30):
            agent._start_plan(source=key)
        assert agent._fresh_plan_cancelled == {}
    finally:
        await end(iq, task)


async def test_same_epoch_preemption_still_hands_off_write_authority():
    """The one legitimate case _fresh_plan_cancelled exists for: a fresh-evidence
    plan is pre-empted by a SAME-epoch, non-fresh trigger (source=None -- an
    internal retry, not new user evidence, e.g. _offer_recovery or a tool result)
    before it delivers. The replacement plan's own eventual (non-fresh) proposal
    must still be able to retain the write authority that pending fresh plan would
    have established. This exercises the exact mechanics the pruning fix must not
    disturb, complementing the end-to-end
    test_request_scope.py::test_correction_to_the_second_request_does_not_touch_the_first,
    which depends on the same hand-off.
    """
    agent, iq, oq, task = await start([], reasoner=HangingPlanner())
    try:
        await iq.put(transcript("Book Wednesday"))
        for _ in range(30):
            await asyncio.sleep(0)
        assert agent.speech_ready is True
        assert agent.planner is not None and not agent.planner.done()
        epoch = agent.request_input_epoch
        key = ("speech", "u")

        agent._start_plan()  # non-fresh: source=None, same epoch as the fresh plan above
        assert agent.request_input_epoch == epoch  # this pre-emption did not bump it
        assert agent._fresh_plan_cancelled == {(agent.request_id, epoch): True}

        agent._fresh_evidence = False
        proposal_obj = PlanProposal(intent="service", slot_updates={"day": "Wednesday"},
                                    request_complete=True, write_requested=True)
        await agent._apply(proposal_obj, source=key)

        assert agent.write_intent_retained is True
        assert agent._fresh_plan_cancelled == {}  # consumed, not merely still present
    finally:
        await end(iq, task)
