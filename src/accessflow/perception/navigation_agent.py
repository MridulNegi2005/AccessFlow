"""LiveKit in-car destination demo using AccessFlow's voice controller.

Run ``python -m accessflow.perception.navigation_agent dev`` with the optional
FDB LiveKit dependencies installed. This is a local simulation, not a real car.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession
from livekit.plugins import groq, silero

from accessflow.adapters.models import ModelReasoner
from accessflow.engine import Agent as AccessFlowAgent
from accessflow.fakes import MockOnlyAuthorization
from accessflow.perception import LocalPerception
from accessflow.perception.fdb_v3.agent import AccessFlowVoiceAgent, _groq_key, _tts_engine
from accessflow.perception.fdb_v3.bridge import RoomBridge
from accessflow.perception.fdb_v3.planner import LiveKitPlannerBackend
from accessflow.perception.navigation import (NavigationExecutor, NavigationStateStore,
                                              navigation_manifests)
from accessflow.turn_policy.heuristic import HeuristicTurnPolicy

_LOG = logging.getLogger(__name__)

if env_file := os.environ.get("NAV_ENV_FILE"):
    load_dotenv(env_file, override=False)

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext) -> None:
    key = _groq_key()
    store_path = Path(os.environ.get("NAV_STATE_DB", str(
        Path(tempfile.gettempdir()) / "accessflow-navigation.sqlite3")))
    executor = NavigationExecutor(room_name=ctx.room.name,
                                  state_store=NavigationStateStore(store_path))
    await executor.initialize()
    backend = LiveKitPlannerBackend(os.environ.get("NAV_LIVEKIT_MODEL", "openai/gpt-5.6-luna"))
    controller = AccessFlowAgent(
        LocalPerception(), HeuristicTurnPolicy(),
        ModelReasoner(backend, prompt_profile="compact-v2"),
        executor, MockOnlyAuthorization(),
    )
    bridge = RoomBridge(ctx.room.name, controller, tool_manifests=navigation_manifests())
    await bridge.start()

    async def close_room() -> None:
        try:
            await bridge.close()
            _LOG.info("Navigation planner request outcomes: %s", backend.evidence()["requests"])
            _LOG.info("Navigation demo final state: destination=%s revision=%s",
                      executor.destination, executor.revision)
        finally:
            await backend.aclose()

    ctx.add_shutdown_callback(close_room)
    voice = AccessFlowVoiceAgent(bridge, executor)
    session = AgentSession(
        stt=groq.STT(api_key=key, model="whisper-large-v3",
                     prompt="Navigation places: Central Station, City Hospital, Airport Terminal 1."),
        vad=silero.VAD.load(min_speech_duration=0.05, min_silence_duration=0.55),
        llm=backend.client,
        tts=_tts_engine(key),
        turn_handling={"turn_detection": "vad", "preemptive_generation": {"enabled": False}},
    )

    @session.on("user_state_changed")
    def on_user_state(event) -> None:
        if event.new_state == "speaking":
            voice.pending_speech_task = asyncio.create_task(bridge.begin_speech())

    await session.start(room=ctx.room, agent=voice)


if __name__ == "__main__":
    agents.cli.run_app(server)
