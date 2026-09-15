import math

import pytest

from accessflow.perception import (
    EditCounts,
    interval_iou,
    modality_coverage,
    normalize_words,
    realtime_factor,
    word_error_counts,
    word_error_rate,
)


def test_word_metrics_normalize_without_deleting_repetitions():
    assert normalize_words("Tuesday, Tuesday... actually Wednesday!") == (
        "tuesday",
        "tuesday",
        "actually",
        "wednesday",
    )
    assert word_error_counts("Book Tuesday", "book tuesday") == EditCounts(0, 0, 0, 2, 2)


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected"),
    [
        ("a b", "a c", EditCounts(1, 0, 0, 2, 2)),
        ("a", "a b", EditCounts(0, 1, 0, 1, 2)),
        ("a b", "a", EditCounts(0, 0, 1, 2, 1)),
    ],
)
def test_word_error_counts_classify_edits(reference, hypothesis, expected):
    assert word_error_counts(reference, hypothesis) == expected


def test_word_error_rate_handles_empty_reference_explicitly():
    assert word_error_rate("", "") == 0
    assert math.isinf(word_error_rate("", "unexpected words"))
    assert word_error_rate("a b", "a c") == 0.5


@pytest.mark.parametrize(
    ("elapsed", "duration", "expected"),
    [(3, 6, 0.5), (0, 2, 0.0)],
)
def test_realtime_factor(elapsed, duration, expected):
    assert realtime_factor(elapsed, duration) == expected


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1])
def test_realtime_factor_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        realtime_factor(value, 1)


def test_interval_iou_and_zero_length_boundary():
    assert interval_iou(1, 3, 2, 4) == pytest.approx(1 / 3)
    assert interval_iou(2, 2, 2, 2) == 1


def test_interval_iou_rejects_inverted_intervals():
    with pytest.raises(ValueError, match="ends"):
        interval_iou(3, 2, 0, 1)


def test_modality_coverage_reports_missing_and_complete_modalities():
    observations = [type("Observation", (), {"modality": "image"})()]
    coverage = modality_coverage(observations, required=("audio", "image", "audio"))

    assert coverage.required == ("audio", "image")
    assert coverage.observed == ("image",)
    assert coverage.missing == ("audio",)
    assert coverage.complete is False
    assert modality_coverage(observations, required=("image",)).complete is True
