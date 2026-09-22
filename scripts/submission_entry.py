"""Template copied to agent/agent.py in a locally assembled Samsung package."""

import json
import os
from pathlib import Path

from accessflow.adapters.samsung import ParticipantAgent as QueueParticipant


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROFILE_KEYS = {
    "ACCESSFLOW_SAMSUNG_BACKEND", "ACCESSFLOW_GROQ_MODEL", "ACCESSFLOW_GROQ_URL",
    "ACCESSFLOW_GROQ_STRUCTURED", "ACCESSFLOW_MAX_OUTPUT_TOKENS",
    "ACCESSFLOW_MAX_CONTEXT_CHARS", "ACCESSFLOW_SAMSUNG_PARTIAL_DEBOUNCE_S",
    "ACCESSFLOW_SAMSUNG_FAST_READ_RETRY", "ACCESSFLOW_SAMSUNG_PROMPT_PROFILE",
}


def configure_profile(profile, environment):
    """Validate before mutation; configuration is shared, conversation state is not."""
    if (not isinstance(profile, dict) or set(profile) != PROFILE_KEYS
            or any(not isinstance(value, str) or not value.strip() for value in profile.values())):
        raise ValueError("Package runtime profile has an invalid shape")
    if (profile["ACCESSFLOW_SAMSUNG_BACKEND"] != "groq"
            or profile["ACCESSFLOW_GROQ_URL"] != "https://api.groq.com/openai/v1"):
        raise ValueError("This package profile requires the declared Groq endpoint")
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
