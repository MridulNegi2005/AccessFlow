"""JSON parsing adapter for internal queue protocol, NOT the Samsung wire adapter."""
from pydantic import TypeAdapter

from accessflow.contracts import InputEvent

event_adapter = TypeAdapter(InputEvent)


def parse_event(raw):
    return event_adapter.validate_python(raw)


def official_adapter(*args, **kwargs):
    raise NotImplementedError(
        "Use accessflow.adapters.samsung.ParticipantAgent for the Samsung queue boundary; "
        "internal v0.1 parsing is not official protocol translation. "
        "See docs/SAMSUNG_ADAPTER.md for current integration limits."
    )
