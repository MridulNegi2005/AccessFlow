"""Small, deterministic turn policy for the first perception checkpoint."""

from __future__ import annotations

import re

from ..contracts import Observation, SessionView, TurnDecision

_CORRECTION = re.compile(r"\b(actually|rather|correction|sorry|i mean)\b|^\s*(no|wait)\s*[,.-]", re.I)
_BACKCHANNELS = frozenset({"mm", "mm-hmm", "mhm", "uh huh", "uh-huh", "right", "okay", "ok"})


class HeuristicTurnPolicy:
    """Classify obvious conversational cues without blocking or calling a model."""

    def update(self, observation: Observation, view: SessionView) -> TurnDecision:
        text = " ".join(observation.text.split())
        normalized = text.casefold().strip(" .,!?")

        if observation.revision < self._latest_revision(view, observation.source_id):
            return TurnDecision(kind="continue", uncertainty=1.0)
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