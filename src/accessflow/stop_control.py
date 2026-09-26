"""Conservative controller controls from complete, direct user utterances only.

This is not general intent extraction: quoted commands, image/tool text, and
requests such as cancelling a booking must continue through normal planning.
"""

import re


def stop_control(text: str, *, held: bool = False) -> str | None:
    normalized = re.sub(r"\s+", " ", text.casefold().strip()).rstrip(".!?,… ")
    normalized = re.sub(r"^(?:please |i meant |i mean )", "", normalized)
    normalized = re.sub(r",? please$", "", normalized)
    if normalized in {"stop speaking", "stop talking", "stop reading aloud"}:
        return "output"
    if normalized in {"stop", "stop right there", "wait", "hold on", "cancel"}:
        return "hold"
    if normalized in {"cancel this task", "cancel the task", "stop this task", "stop the task"}:
        return "task"
    if held and normalized in {"continue", "continue the task", "resume", "resume the task",
                               "go ahead with the task"}:
        return "resume"
    if held and re.fullmatch(r"cancel (?:this|the|my|that) .+", normalized):
        # The user has resolved task-vs-output ambiguity in favour of an action.
        # Normal planning must still identify/clarify its target and authorize it.
        return "action"
    return None
