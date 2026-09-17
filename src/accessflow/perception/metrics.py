"""Small deterministic metrics for local perception experiments."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

_WORD = re.compile(r"[\w']+", re.UNICODE)


def normalize_words(text: str) -> tuple[str, ...]:
    """Normalize case and punctuation while preserving word repetitions."""
    if not isinstance(text, str):
        raise TypeError("metric text must be a string")
    return tuple(_WORD.findall(text.casefold()))


@dataclass(frozen=True)
class EditCounts:
    substitutions: int
    insertions: int
    deletions: int
    reference_words: int
    hypothesis_words: int

    @property
    def errors(self) -> int:
        return self.substitutions + self.insertions + self.deletions

    @property
    def error_rate(self) -> float:
        if self.reference_words == 0:
            return 0.0 if self.hypothesis_words == 0 else math.inf
        return self.errors / self.reference_words


def word_error_counts(reference: str, hypothesis: str) -> EditCounts:
    """Return deterministic word-level edit counts for an ASR comparison."""
    expected = normalize_words(reference)
    actual = normalize_words(hypothesis)
    rows = len(expected) + 1
    columns = len(actual) + 1
    costs: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(columns)] for _ in range(rows)
    ]
    for row in range(1, rows):
        costs[row][0] = (row, 0, 0, row)
    for column in range(1, columns):
        costs[0][column] = (column, 0, column, 0)

    for row in range(1, rows):
        for column in range(1, columns):
            if expected[row - 1] == actual[column - 1]:
                costs[row][column] = costs[row - 1][column - 1]
                continue
            substitution = costs[row - 1][column - 1]
            insertion = costs[row][column - 1]
            deletion = costs[row - 1][column]
            candidates = (
                (substitution[0] + 1, substitution[1] + 1, substitution[2], substitution[3]),
                (insertion[0] + 1, insertion[1], insertion[2] + 1, insertion[3]),
                (deletion[0] + 1, deletion[1], deletion[2], deletion[3] + 1),
            )
            costs[row][column] = min(candidates, key=lambda value: value[0])

    distance, substitutions, insertions, deletions = costs[-1][-1]
    assert distance == substitutions + insertions + deletions
    return EditCounts(
        substitutions=substitutions,
        insertions=insertions,
        deletions=deletions,
        reference_words=len(expected),
        hypothesis_words=len(actual),
    )


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Return word error rate, with infinity for insertions without a reference."""
    return word_error_counts(reference, hypothesis).error_rate


def _finite_nonnegative(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be a finite non-negative number")
    return float(value)


def realtime_factor(elapsed_s: float, media_duration_s: float) -> float:
    """Return elapsed wall time divided by the duration of the media input."""
    elapsed = _finite_nonnegative(elapsed_s, "elapsed_s")
    duration = _finite_nonnegative(media_duration_s, "media_duration_s")
    if duration <= 0:
        raise ValueError("media_duration_s must be positive")
    return elapsed / duration


def interval_iou(
    first_start_s: float,
    first_end_s: float,
    second_start_s: float,
    second_end_s: float,
) -> float:
    """Return intersection-over-union for two non-negative time intervals."""
    first_start = _finite_nonnegative(first_start_s, "first_start_s")
    first_end = _finite_nonnegative(first_end_s, "first_end_s")
    second_start = _finite_nonnegative(second_start_s, "second_start_s")
    second_end = _finite_nonnegative(second_end_s, "second_end_s")
    if first_end < first_start or second_end < second_start:
        raise ValueError("interval ends must be at least their starts")
    intersection = max(0.0, min(first_end, second_end) - max(first_start, second_start))
    union = max(first_end, second_end) - min(first_start, second_start)
    return 1.0 if union == 0 else intersection / union


@dataclass(frozen=True)
class ModalityCoverage:
    required: tuple[str, ...]
    observed: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing


def modality_coverage(
    observations: Iterable[Any],
    required: Iterable[str] = ("audio", "image"),
) -> ModalityCoverage:
    """Report which required modalities are present in an observation collection."""
    required_values = tuple(dict.fromkeys(required))
    if any(not isinstance(value, str) or not value.strip() for value in required_values):
        raise ValueError("required modalities must be non-empty strings")
    observed_modalities = tuple(getattr(item, "modality", None) for item in observations)
    if any(not isinstance(value, str) or not value.strip() for value in observed_modalities):
        raise ValueError("observation modalities must be non-empty strings")
    observed_values = tuple(sorted(set(observed_modalities)))
    missing = tuple(value for value in required_values if value not in observed_values)
    return ModalityCoverage(required_values, observed_values, missing)
