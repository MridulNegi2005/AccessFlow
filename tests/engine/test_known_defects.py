"""Reproductions of defects that are understood but not yet fixed.

Each test here fails on purpose. Remove the xfail marker with the fix, never the test.
"""
import asyncio

import pytest

from accessflow.contracts import PlanProposal
from test_component_integration import components, png
from test_safety import proposal, transcript, wait_for


@pytest.mark.xfail(reason="A clarifying question drops the spoken write intent, so a later "
                          "image cannot complete the request. Found 15 September 2026 while "
                          "authoring the first vision scenario.",
                   raises=(TimeoutError, asyncio.TimeoutError), strict=True)
async def test_clarify_then_image_completes_the_write(tmp_path):
    """Speech asks for a write and the planner asks one question first.

    The image that answers the question arrives next. The request should then complete.
    It does not: at the deadlock `speech_write_requested` is False and `latest_complete`
    is False, so the write is never authorized and no error code is emitted.

    `test_image_can_complete_an_existing_spoken_write_request` passes because its first
    proposal carries no clarification. The clarifying turn is what loses the intent.

    This matters for real use. A person speaks first and shows the panel second, so the
    only event order a user would produce is the order that stalls.
    """
    plans = [PlanProposal(intent="service", write_requested=True,
                          clarification="Which date is shown?"),
             proposal()]
    async with components(plans, None) as (agent, iq, oq, applied):
        await iq.put(transcript("Book the date shown in this image"))
        await asyncio.wait_for(applied.get(), 1)
        assert not agent.executor.calls
        await iq.put(png(tmp_path / "pixel.png"))
        await wait_for(oq, lambda event: event.kind == "final")
        assert len(agent.executor.effects) == 1
