"""LiveKit voice entrypoint for the official FDB-v3 mock benchmark.

Run from the repository root with ``python -m accessflow.perception.fdb_v3.agent dev``.
The official ``v3`` directory must be supplied through FDB_V3_ROOT.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from accessflow.adapters.models import JsonBackend, ModelReasoner
from accessflow.engine import Agent as AccessFlowAgent
from accessflow.fakes import MockOnlyAuthorization
from accessflow.perception import LocalPerception
from accessflow.turn_policy.heuristic import HeuristicTurnPolicy
from livekit import agents
from livekit.agents import Agent as LiveKitAgent
from livekit.agents import AgentServer, AgentSession, inference, tokenize, tts
from livekit.plugins import groq, silero

from .bridge import RoomBridge, spoken_results, tts_safe_text
from .planner import LiveKitPlannerBackend
from .tools import FDBMockExecutor, validate_official_registry

_LOG = logging.getLogger(__name__)


def _official_registry_class():
    root = _official_root()
    if not (root / "mock_apis.py").is_file() or not (root / "latency_injector.py").is_file():
        raise RuntimeError("FDB_V3_ROOT must point to the official benchmark's v3 directory")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    registry_class = importlib.import_module("mock_apis").MockAPIRegistry
    validate_official_registry(registry_class)
    return registry_class


def _official_root() -> Path:
    return Path(os.environ.get("FDB_V3_ROOT", "third_party/Full-Duplex-Bench/v3")).resolve()


load_dotenv(_official_root() / ".env.local", override=False)


def _telemetry_path() -> Path:
    if configured := os.environ.get("FDB_TOOL_LOG"):
        return Path(configured)
    # The official runner reads Path('/tmp/...'). On Windows that is rooted
    # on the runner's current drive, which may differ from this checkout's.
    root = _official_root()
    return (Path(root.anchor) / "tmp" / "agent_tool_calls.log") if os.name == "nt" else Path(
        "/tmp/agent_tool_calls.log")


def _groq_key() -> str:
    key = (os.environ.get("ACCESSFLOW_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
           or os.environ.get("SECRET_GROQ_API_KEY"))
    if not key:
        raise RuntimeError("Set ACCESSFLOW_GROQ_API_KEY or GROQ_API_KEY privately")
    os.environ.setdefault("ACCESSFLOW_GROQ_API_KEY", key)
    return key


def _fdb_model() -> str:
    # The browser demo may configure a vision-capable model at User scope.
    # This voice-only worker chooses its text model explicitly.
    model = os.environ.get("FDB_GROQ_MODEL", "qwen/qwen3.8-27b")
    os.environ["ACCESSFLOW_GROQ_MODEL"] = model
    return model


def _tts_engine(key: str):
    provider = os.environ.get("FDB_TTS_PROVIDER", "livekit")
    if provider == "livekit":
        return inference.TTS(model="deepgram/aura-2", voice="athena")
    if provider == "groq":
        return tts.StreamAdapter(
            tts=groq.TTS(api_key=key, model="canopylabs/orpheus-v1-english", voice="autumn"),
            sentence_tokenizer=tokenize.blingfire.SentenceTokenizer(
                retain_format=True, max_token_len=190),
        )
    raise ValueError("FDB_TTS_PROVIDER must be livekit or groq")


def _stt_engine(key: str):
    vocabulary = ("Currency names: US dollars, euros, pounds, rupees, yen. "
                  "Other terms: autopay, savings, credit card, flights, "
                  "apartments, orders, shopping cart.")
    return groq.STT(api_key=key, model=os.environ.get(
        "FDB_GROQ_STT_MODEL", "whisper-large-v3"), prompt=vocabulary)


def check_configuration() -> None:
    _official_registry_class()
    _groq_key()
    if os.environ.get("FDB_PLANNER_PROVIDER", "livekit") not in {"groq", "livekit"}:
        raise RuntimeError("FDB_PLANNER_PROVIDER must be groq or livekit")
    if os.environ.get("FDB_TTS_PROVIDER", "livekit") not in {"livekit", "groq"}:
        raise RuntimeError("FDB_TTS_PROVIDER must be livekit or groq")
    missing = [name for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
               if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing LiveKit project settings: " + ", ".join(missing))
    print("FDB-v3 registry, dependencies, and credential presence: ready; live audio unverified")


class AccessFlowVoiceAgent(LiveKitAgent):
    def __init__(self, bridge: RoomBridge, executor):
        super().__init__(instructions="Speak the verified AccessFlow response concisely.")
        self.bridge = bridge
        self.executor = executor
        self._pending_text = ""
        self.pending_speech_task: asyncio.Task | None = None

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        if self.pending_speech_task is not None:
            await self.pending_speech_task
            self.pending_speech_task = None
        self._pending_text = new_message.text_content or ""

    async def llm_node(self, chat_ctx, tools, model_settings) -> str:
        text, self._pending_text = self._pending_text, ""
        if not text:
            text = next((message.text_content or "" for message in reversed(chat_ctx.messages())
                         if message.role == "user"), "")
        existing_operations = self.executor.operation_ids()
        reply = await self.bridge.complete_turn(text)
        unresolved = await self.executor.drain()
        if unresolved:
            _LOG.warning("Executor operations remain unresolved after turn: %s", unresolved)
        confirmed = self.executor.confirmed_results(excluding=existing_operations)
        if self.bridge.last_reply_kind == "final" and (len(confirmed) > 1 or any(
                tool in {"set_navigation_destination", "get_navigation_state"}
                for tool, _ in confirmed)):
            reply = spoken_results(confirmed)
        return tts_safe_text(reply)


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext) -> None:
    registry_class = _official_registry_class()
    key = _groq_key()
    # Each room gets fresh mock API state, tool operation ledger, and controller.
    registry = registry_class(latency_profile=os.getenv("FDB_LATENCY_PROFILE", "instant"))
    executor = FDBMockExecutor(registry, ctx.room.name, telemetry_path=_telemetry_path())
    provider = os.environ.get("FDB_PLANNER_PROVIDER", "livekit")
    if provider == "livekit":
        backend = LiveKitPlannerBackend(os.environ.get("FDB_LIVEKIT_MODEL", "openai/gpt-5.6-luna"))
        scheduling_llm = backend.client
    else:
        os.environ.setdefault("ACCESSFLOW_MAX_OUTPUT_TOKENS", "950")
        model = _fdb_model()
        backend = JsonBackend("groq")
        scheduling_llm = groq.LLM(api_key=key, model=model)
    controller = AccessFlowAgent(
        LocalPerception(), HeuristicTurnPolicy(),
        ModelReasoner(backend, prompt_profile=os.getenv(
            "FDB_PROMPT_PROFILE", "compact-v2")), executor, MockOnlyAuthorization(),
    )
    bridge = RoomBridge(ctx.room.name, controller)
    await bridge.start()

    async def close_room() -> None:
        try:
            await bridge.close()
            await executor.drain()
            _LOG.info("FDB planner request outcomes: %s", backend.evidence()["requests"])
        finally:
            if isinstance(backend, LiveKitPlannerBackend):
                await backend.aclose()

    ctx.add_shutdown_callback(close_room)
    voice = AccessFlowVoiceAgent(bridge, executor)
    speech = _tts_engine(key)
    session = AgentSession(
        stt=_stt_engine(key),
        vad=silero.VAD.load(min_speech_duration=0.05, min_silence_duration=0.55),
        # LiveKit requires an LLM object to schedule replies even when llm_node
        # supplies every response through the AccessFlow controller.
        llm=scheduling_llm,
        tts=speech,
        turn_handling={"turn_detection": "vad", "preemptive_generation": {"enabled": False}},
    )

    @session.on("user_state_changed")
    def on_user_state(event) -> None:
        if event.new_state == "speaking":
            voice.pending_speech_task = asyncio.create_task(bridge.begin_speech())

    await session.start(room=ctx.room, agent=voice)


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        try:
            check_configuration()
        except RuntimeError as error:
            raise SystemExit(str(error)) from None
    else:
        agents.cli.run_app(server)
