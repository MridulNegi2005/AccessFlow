"""FDB room routing tests use the real controller without network or a microphone."""

import asyncio
import json

import pytest

from accessflow.contracts import PlanProposal
from accessflow.engine import Agent
from accessflow.fakes import FakePerception, FinalFlagPolicy, ScriptedReasoner
from accessflow.perception.fdb_v3.bridge import RoomBridge, spoken_results, tts_safe_text


async def test_room_routes_two_distinct_final_turns_and_closes_cleanly():
    reasoner = ScriptedReasoner([
        PlanProposal(response="First answer.", request_complete=True),
        PlanProposal(response="Second answer.", request_complete=True),
    ])
    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), reasoner))
    await bridge.start()
    try:
        await bridge.begin_speech()
        assert await bridge.complete_turn("first question", timeout=5) == "First answer."
        await bridge.begin_speech()
        assert await bridge.complete_turn("second question", timeout=5) == "Second answer."
        assert len(reasoner.views) == 2
        assert reasoner.views[0].observations[-1].text == "first question"
        assert reasoner.views[1].observations[-1].text == "second question"
    finally:
        await bridge.close()


async def test_new_speech_cancels_waiting_reply():
    class SlowReasoner:
        async def plan(self, view, manifests):
            await asyncio.sleep(0.3)
            return PlanProposal(response=view.observations[-1].text, request_complete=True)

    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), SlowReasoner()))
    await bridge.start()
    try:
        first = asyncio.create_task(bridge.complete_turn("outdated", timeout=5))
        await asyncio.sleep(0.02)
        await bridge.begin_speech()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await bridge.complete_turn("corrected", timeout=5) == "corrected"
    finally:
        await bridge.close()


def test_long_spoken_reply_splits_into_provider_sized_sentences():
    text = "A detailed result with verified fields and a long explanation. " * 8
    spoken = tts_safe_text(text)
    assert all(len(sentence) <= 200 for sentence in spoken.split(". "))
    assert spoken.startswith("A detailed result")


def test_parallel_result_speech_uses_each_confirmed_tool_output():
    spoken = spoken_results([
        ("get_exchange_rate", {"status": "success", "converted_amount": 900.0, "rate": 0.9}),
        ("modify_autopay", {"status": "success", "autopay_enabled": True, "source": "savings"}),
        ("get_card_benefits", {"status": "success", "card_type": "premium",
                               "benefits": ["Cashback", "No fee"]}),
    ])
    assert "Conversion: 900.0 at rate 0.9" in spoken
    assert "Autopay now uses savings" in spoken
    assert "Cashback, No fee" in spoken
    assert "status" not in spoken


async def test_schema_rejection_is_not_spoken_before_controller_recovery():
    class RecoveringReasoner:
        def __init__(self):
            self.attempts = 0

        async def plan(self, view, manifests):
            self.attempts += 1
            if self.attempts == 1:
                raise json.JSONDecodeError("invalid first proposal", "{", 0)
            return PlanProposal(response="Recovered answer.", request_complete=True)

    reasoner = RecoveringReasoner()
    bridge = RoomBridge("eval-room", Agent(FakePerception(), FinalFlagPolicy(), reasoner))
    await bridge.start()
    try:
        assert await bridge.complete_turn("question", timeout=5) == "Recovered answer."
        assert reasoner.attempts == 2
    finally:
        await bridge.close()
