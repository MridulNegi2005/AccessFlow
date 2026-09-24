"""Common real-agent composition for queue and user-interface adapters.

Adapters retain ownership of input translation and tool manifests. This factory
never substitutes fake inference and warms explicitly configured media before use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import asyncio
import math
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from accessflow.contracts import Audio, AudioEvent, Frame, FrameEvent
from accessflow.engine import Agent
from accessflow.perception.local import LocalPerception
from accessflow.turn_policy import HeuristicTurnPolicy

from . import models
from .process_perception import ProcessPerception

SETUP_TIMEOUT_S = 290.0  # Leave room for worker cleanup before the kit's 300-second limit.

PERCEPTION_ENV_KEYS = frozenset({
    "ACCESSFLOW_SAMSUNG_PERCEPTION", "ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH",
    "ACCESSFLOW_SAMSUNG_PERCEPTION_TIMEOUT_S", "ACCESSFLOW_SAMSUNG_WARMUP_AUDIO",
    "ACCESSFLOW_SAMSUNG_WARMUP_IMAGE", "ACCESSFLOW_SAMSUNG_VISION_PROVIDER",
    "ACCESSFLOW_SAMSUNG_VISION_MODEL", "ACCESSFLOW_SAMSUNG_VISION_URL",
})


@dataclass(frozen=True)
class PerceptionConfig:
    mode: str = "text"
    model_path: Path | None = None
    timeout_s: float = 30.0
    warmup_audio: Path | None = None
    warmup_image: Path | None = None
    vision_provider: str = "none"
    vision_model: str | None = None
    vision_url: str | None = None

    @classmethod
    def from_environment(cls, root: Path, environment: Mapping[str, str] | None = None):
        env = os.environ if environment is None else environment

        def value(name, default=""):
            result = env.get("ACCESSFLOW_SAMSUNG_" + name, default)
            if not isinstance(result, str) or not result.strip():
                raise ValueError(f"Invalid perception setting: {name}")
            return result.strip()

        mode = value("PERCEPTION", "text")
        if mode not in {"text", "process"}:
            raise ValueError("PERCEPTION must be text or process")
        native_keys = PERCEPTION_ENV_KEYS - {"ACCESSFLOW_SAMSUNG_PERCEPTION"}
        if mode == "text":
            if any(name in env for name in native_keys):
                raise ValueError("Native perception settings require PERCEPTION=process")
            return cls()

        try:
            timeout = float(value("PERCEPTION_TIMEOUT_S", "30"))
        except ValueError as error:
            raise ValueError("Invalid PERCEPTION_TIMEOUT_S") from error
        if not math.isfinite(timeout) or not 0 < timeout <= 110:
            raise ValueError("PERCEPTION_TIMEOUT_S must be finite and within (0, 110]")

        def installed_path(name, *, directory=False, suffix=None):
            path = Path(value(name))
            path = (root / path).resolve() if not path.is_absolute() else path.resolve()
            if not (path.is_dir() if directory else path.is_file()):
                raise ValueError(f"Configured {name} is not installed")
            if suffix is not None and path.suffix.lower() != suffix:
                raise ValueError(f"Configured {name} must be {suffix}")
            return path

        model = installed_path("ASR_MODEL_PATH", directory=True)
        audio = installed_path("WARMUP_AUDIO", suffix=".wav")
        provider = value("VISION_PROVIDER", "none")
        image = vision_model = vision_url = None
        if provider == "ollama":
            vision_model = value("VISION_MODEL")
            vision_url = value("VISION_URL", "http://127.0.0.1:11434").rstrip("/")
            parsed = urlsplit(vision_url)
            if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment
                    or parsed.path or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
                raise ValueError("VISION_URL must be a loopback HTTP(S) origin without credentials")
            image = installed_path("WARMUP_IMAGE", suffix=".png")
        elif provider != "none":
            raise ValueError("VISION_PROVIDER must be none or ollama")
        elif any("ACCESSFLOW_SAMSUNG_" + name in env for name in
                 ("VISION_MODEL", "VISION_URL", "WARMUP_IMAGE")):
            raise ValueError("Vision settings require VISION_PROVIDER=ollama")
        return cls(mode, model, timeout, audio, image, provider, vision_model, vision_url)

    def create(self):
        if self.mode == "text":
            return LocalPerception()
        arguments = []
        if self.vision_provider == "ollama":
            arguments = ["--vision-provider", "ollama", "--vision-model", self.vision_model,
                         "--vision-url", self.vision_url, "--vision-timeout", str(self.timeout_s)]
        return ProcessPerception(self.model_path, observation_timeout_s=self.timeout_s,
                                 worker_args=arguments)

    async def warmup(self, perception):
        """Use declared installation fixtures, never scenario labels or user history.

        The fixture must contain recognizable speech: silence would only prove
        error handling, not successful ASR loading. Results are discarded here.
        """
        if self.mode == "text":
            return {}
        session = "installation-warmup-" + str(uuid4())
        events = [AudioEvent(session_id=session, payload=Audio(
            path=str(self.warmup_audio), utterance_id="installation-audio"))]
        if self.warmup_image is not None:
            events.append(FrameEvent(session_id=session, payload=Frame(
                path=str(self.warmup_image), frame_id="installation-image")))
        observed = {}
        for event in events:
            results = [item async for item in perception.observe(event)]
            modality = "audio" if event.kind == "audio" else "image"
            source = event.payload.utterance_id if event.kind == "audio" else event.payload.frame_id
            matching = [item for item in results if item.event_id == event.event_id
                        and item.source_id == source and item.modality == modality
                        and item.revision == 0 and item.final and item.text.strip()]
            if len(matching) != 1:
                raise RuntimeError(f"Configured {modality} warm-up did not produce a final observation")
            observed[modality] = matching[0].backend
        return observed


async def build_configured_agent(*, root, authorization, executor=None,
                                 tool_documentation=None, prompt_profile="full",
                                 read_answer_mode="prose", partial_debounce_s=0.08,
                                 fast_read_retry=True):
    """Return one fresh session composition; external adapters provide authority."""
    config = PerceptionConfig.from_environment(Path(root))
    backend_name = os.getenv("ACCESSFLOW_SAMSUNG_BACKEND")
    if not backend_name:
        raise ValueError("Set ACCESSFLOW_SAMSUNG_BACKEND explicitly; no model fallback is enabled")
    perception = config.create()
    try:
        async with asyncio.timeout(SETUP_TIMEOUT_S):
            observed = await config.warmup(perception)
            backend = models.JsonBackend(backend_name)
            await backend.warmup()
        agent = Agent(perception, HeuristicTurnPolicy(),
                      models.ModelReasoner(backend, tool_documentation=tool_documentation,
                                    prompt_profile=prompt_profile, read_answer_mode=read_answer_mode),
                      executor=executor, authorization=authorization,
                      partial_debounce_s=partial_debounce_s, fast_read_retry=fast_read_retry,
                      read_answer_mode=read_answer_mode,
                      **({"inference_timeout": config.timeout_s} if config.mode == "process" else {}))
        agent.perception_configuration = config
        agent.perception_warmup_backends = observed
        return agent
    except BaseException:
        await perception.aclose()
        raise
