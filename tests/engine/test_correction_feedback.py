"""Accepted corrections are spoken with current state, without effect claims."""
import asyncio

import pytest

from accessflow.fakes import FakeTools
from accessflow.fakes import ScriptedReasoner
from accessflow.contracts import TurnDecision
from accessflow.clock import RealClock
from test_safety import end, manifest, proposal, start, transcript, wait_for
from test_samsung_protocol import output
from accessflow.adapters.samsung_protocol import SamsungProtocol


@pytest.mark.parametrize("final", [True, False])
async def test_updated_speech_is_acknowledged_only_when_complete(final):
    tools = FakeTools(gate=asyncio.Event())
    plans = [proposal("Wednesday"), proposal("Friday")]
    for plan in plans:
        plan.write_requested = False
    agent, iq, oq, task = await start(plans, tools=tools,
                                     manifests=[manifest(effect="read")], partial_debounce_s=0)
    try:
        await iq.put(transcript("Look up Wednesday"))
        first = await wait_for(oq, lambda e: e.kind == "tool_call")
        await iq.put(transcript("Actually Friday", utterance="corrected", final=final))
        seen = []
        async with asyncio.timeout(2):
            while True:
                item = await oq.get()
                seen.append(item)
                if item.kind == "tool_call":
                    break
        spoken = [e for e in seen if e.payload.get("basis") == "accepted_user_correction"]
        assert len(spoken) == int(final)
        if final:
            assert "Friday" in spoken[0].payload["text"]
            assert "completed" not in spoken[0].payload["text"]
            assert spoken[0].state.slots["day"].value == "Friday"
            assert first.payload["call_id"] not in spoken[0].state.pending_call_ids
            assert spoken[0].state.slots["day"].confirmed
        assert not tools.effects
        assert agent.state.slots["day"].value == "Friday"
    finally:
        await end(iq, task)


def test_samsung_repeated_fillers_are_suppressed_but_stops_are_not(tmp_path):
    protocol = SamsungProtocol(tmp_path)
    filler = output("acknowledge", {"text": "I'll check that."})
    assert protocol.translate_output(filler)["action"] == "filler_speech"
    assert protocol.translate_output(filler) is None
    stop = output("acknowledge", {"text": "Stopped.", "stop_output": True})
    assert protocol.translate_output(stop) is not None
    assert protocol.translate_output(stop) is not None
    assert SamsungProtocol(tmp_path).translate_output(filler) is not None


@pytest.mark.parametrize("code", ["backend_failure", "no_progress_exhausted"])
def test_samsung_known_failures_get_bounded_honest_speech_with_current_state(tmp_path, code):
    protocol = SamsungProtocol(tmp_path)
    event = output("error", {"code": code, "detail": "UNTRUSTED PRIVATE BACKEND TEXT",
                             "caused_by_event_id": "source-1"}, slots={"destination": "New York"})
    action = protocol.translate_output(event)
    assert action["action"] == "clarification_request"
    assert "may still be pending" in action["payload"]["text"]
    assert "UNTRUSTED" not in action["payload"]["text"]
    assert action["state_snapshot"]["slots"]["destination"] == "New York"
    assert protocol.translate_output(event) is None
    event.payload["caused_by_event_id"] = "source-2"
    assert protocol.translate_output(event) is not None


def test_samsung_unknown_diagnostics_do_not_become_speech(tmp_path):
    protocol = SamsungProtocol(tmp_path)
    assert protocol.translate_output(output("error", {"code": "unknown_future_code"})) is None


@pytest.mark.parametrize("final", [True, False])
async def test_only_finished_correction_skips_partial_debounce(final):
    class Clock(RealClock):
        def __init__(self):
            self.debounce_entered = asyncio.Event()
            self.release = asyncio.Event()

        async def sleep(self, seconds):
            if seconds == 5:
                self.debounce_entered.set()
                await self.release.wait()
            else:
                await super().sleep(seconds)

    class Reasoner(ScriptedReasoner):
        async def plan(self, view, manifests):
            if self.views:
                called.set()
            return await super().plan(view, manifests)

    class PossibleCorrection:
        def update(self, observation, view):
            return TurnDecision(kind="possible_correction")

    called = asyncio.Event()
    clock = Clock()
    plans = [proposal("Wednesday"), proposal("Friday")]
    for plan in plans:
        plan.write_requested = False
    reasoner = Reasoner(plans)
    agent, iq, oq, task = await start([], reasoner=reasoner,
                                     tools=FakeTools(gate=asyncio.Event()),
                                     manifests=[manifest(effect="read")], partial_debounce_s=5)
    waiters = []
    try:
        await iq.put(transcript("Look up Wednesday"))
        await wait_for(oq, lambda e: e.kind == "tool_call")
        agent.clock = clock
        agent.turn_policy = PossibleCorrection()
        await iq.put(transcript("Actually Friday", utterance="corrected", final=final))
        waiters = [asyncio.create_task(called.wait()),
                   asyncio.create_task(clock.debounce_entered.wait())]
        async with asyncio.timeout(2):
            await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        assert called.is_set() == final
        assert clock.debounce_entered.is_set() != final
        if not final:
            assert agent.state.correction_pending
            assert not agent.speech_ready
            clock.release.set()
            await asyncio.wait_for(called.wait(), 2)
            assert not agent.write_intent_retained
    finally:
        for waiter in waiters:
            waiter.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
        await end(iq, task)
