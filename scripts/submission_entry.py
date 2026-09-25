"""Template copied to agent/agent.py in a locally assembled Samsung package."""

import json
import os
from pathlib import Path

from accessflow.adapters.samsung import ParticipantAgent as QueueParticipant
from accessflow.adapters.prompt_profile import PROMPT_PROFILES
from accessflow.adapters.configured_agent import PERCEPTION_ENV_KEYS, PerceptionConfig
from accessflow.read_answer import READ_ANSWER_MODES


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROFILE_KEYS = {
    "ACCESSFLOW_SAMSUNG_BACKEND", "ACCESSFLOW_GROQ_MODEL", "ACCESSFLOW_GROQ_URL",
    "ACCESSFLOW_GROQ_STRUCTURED", "ACCESSFLOW_MAX_OUTPUT_TOKENS",
    "ACCESSFLOW_MAX_CONTEXT_CHARS", "ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S",
    "ACCESSFLOW_SAMSUNG_FAST_READ_RETRY", "ACCESSFLOW_SAMSUNG_PROMPT_PROFILE",
    "ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE",
    "ACCESSFLOW_SAMSUNG_PERCEPTION",
}


def configure_profile(profile, environment, *, root=None):
    """Validate before mutation; configuration is shared, conversation state is not."""
    if not isinstance(profile, dict):
        raise ValueError("Package runtime profile has an invalid shape")
    expected = set(PROFILE_KEYS)
    native = profile.get("ACCESSFLOW_SAMSUNG_PERCEPTION") == "process"
    if native:
        expected.update({"ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH", "ACCESSFLOW_SAMSUNG_WARMUP_AUDIO",
                         "ACCESSFLOW_SAMSUNG_PERCEPTION_TIMEOUT_S", "ACCESSFLOW_SAMSUNG_VISION_PROVIDER"})
        if profile.get("ACCESSFLOW_SAMSUNG_VISION_PROVIDER") == "ollama":
            expected.update({"ACCESSFLOW_SAMSUNG_VISION_MODEL", "ACCESSFLOW_SAMSUNG_VISION_URL",
                             "ACCESSFLOW_SAMSUNG_WARMUP_IMAGE"})
    if (set(profile) != expected
            or any(not isinstance(value, str) or not value.strip() for value in profile.values())):
        raise ValueError("Package runtime profile has an invalid shape")
    if (profile["ACCESSFLOW_SAMSUNG_BACKEND"] != "groq"
            or profile["ACCESSFLOW_GROQ_URL"] != "https://api.groq.com/openai/v1"):
        raise ValueError("This package profile requires the declared Groq endpoint")
    if (profile["ACCESSFLOW_SAMSUNG_PROMPT_PROFILE"] not in PROMPT_PROFILES
            or profile["ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE"] not in READ_ANSWER_MODES):
        raise ValueError("Unsupported package prompt profile or read answer mode")
    if native:
        fixed_paths = {"ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH": "assets/asr",
                       "ACCESSFLOW_SAMSUNG_WARMUP_AUDIO": "assets/warmup.wav"}
        if "ACCESSFLOW_SAMSUNG_WARMUP_IMAGE" in profile:
            fixed_paths["ACCESSFLOW_SAMSUNG_WARMUP_IMAGE"] = "assets/warmup.png"
        if any(profile[name] != value for name, value in fixed_paths.items()):
            raise ValueError("Native profile must use packaged installation assets")
        base = (PACKAGE_ROOT if root is None else Path(root)).resolve()
        if any(not (base / path).resolve().is_relative_to(base) for path in fixed_paths.values()):
            raise ValueError("Packaged installation assets escape their boundary")
    PerceptionConfig.from_environment(PACKAGE_ROOT if root is None else Path(root), profile)
    undeclared = sorted((PERCEPTION_ENV_KEYS - expected) & environment.keys())
    if undeclared:
        raise ValueError(f"Environment contains undeclared perception setting: {undeclared[0]}")
    for name, value in profile.items():
        if name in environment and environment[name] != value:
            raise ValueError(f"Environment conflicts with package profile: {name}")
    portal_key = environment.get("SECRET_GROQ_API_KEY")
    local_key = environment.get("ACCESSFLOW_GROQ_API_KEY")
    if portal_key and local_key and portal_key != local_key:
        raise ValueError("Portal and local key settings conflict")
    key = portal_key or local_key
    if not key or not key.strip():
        raise ValueError("Supply SECRET_GROQ_API_KEY; no credential is included in the package")
    environment.update(profile)
    environment["ACCESSFLOW_GROQ_API_KEY"] = key


class ParticipantAgent(QueueParticipant):
    def __init__(self, in_queue, out_queue):
        super().__init__(in_queue, out_queue, media_root=PACKAGE_ROOT,
                         tool_documentation="docs/TOOLS.md")

    async def setup(self):
        profile = json.loads((PACKAGE_ROOT / "runtime_profile.json").read_text(encoding="utf-8"))
        configure_profile(profile, os.environ)
        await super().setup()
