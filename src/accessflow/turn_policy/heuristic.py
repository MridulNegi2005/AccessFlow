"""Small, deterministic turn policy for the first perception checkpoint."""

from __future__ import annotations

import re

from ..contracts import Observation, SessionView, TurnDecision
from ..perception.timing import ActivitySummary

_CORRECTION = re.compile(r"\b(actually|rather|correction|sorry|i mean)\b|^\s*(no|wait)\s*[,.-]", re.I)
_OUTPUT_STOP_REQUEST = re.compile(r"^\s*stop\s+(?:speaking|talking)\b", re.I)
_TASK_CANCEL_REQUEST = re.compile(
    r"^\s*(?:stop\s+(?:the\s+whole\s+task|this\s+task|everything)"
    r"|cancel\s+(?:this\s+booking|the\s+task|this\s+task|everything))\b",
    re.I,
)
_BACKCHANNELS = frozenset({"mm", "mm-hmm", "mhm", "uh huh", "uh-huh", "right", "okay", "ok"})


class HeuristicTurnPolicy:
    """Classify obvious conversational cues without blocking or calling a model."""

    def update(
        self,
        observation: Observation,
        view: SessionView,
        *,
        timing: ActivitySummary | None = None,
    ) -> TurnDecision:
        text = " ".join(observation.text.split())
        normalized = text.casefold().strip(" .,!?")

        if observation.revision < self._latest_revision(view, observation.source_id):
            return TurnDecision(kind="continue", uncertainty=1.0)
        if observation.modality == "image":
            return TurnDecision(kind="continue", uncertainty=1.0)
        if _OUTPUT_STOP_REQUEST.search(text):
            # The shared decision has no output-only stop scope. Never map it to
            # task cancellation; the typed speech interrupt needs A's contract.
            return TurnDecision(kind="continue", uncertainty=1.0)
        if _TASK_CANCEL_REQUEST.search(text):
            if not observation.final:
                return TurnDecision(kind="continue", uncertainty=0.3)
            return TurnDecision(kind="stop", uncertainty=0.1)
        if timing is not None and timing.pause_detected and not observation.final:
            return TurnDecision(kind="continue", uncertainty=0.25)
        if normalized in _BACKCHANNELS and observation.final:
            return TurnDecision(kind="backchannel", uncertainty=0.05)
        if _CORRECTION.search(text):
            return TurnDecision(
                kind="possible_correction",
                uncertainty=0.15 if observation.final else 0.35,
            )
        if not observation.final:
            return TurnDecision(kind="continue", uncertainty=0.25)
        return TurnDecision(kind="complete", uncertainty=0.0)

    @staticmethod
    def _latest_revision(view: SessionView, source_id: str) -> int:
        revisions = [item.revision for item in view.observations if item.source_id == source_id]
        return max(revisions, default=-1)
