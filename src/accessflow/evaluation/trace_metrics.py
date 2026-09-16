"""Evidence-aware metrics for typed AccessFlow JSONL traces.

The evaluator consumes rows of the following shape::

    {"type": "input", "event": {"kind": "transcript", ...},
     "observed_at": 12.5}
    {"type": "output", "event": {"kind": "acknowledge", ...},
     "observed_at": 12.7}
    {"type": "run_metadata", "backend": "...", "config": {...}}

``observed_at`` is the measurement clock.  Envelope timestamps are retained as
event data, but are not used as wall-clock timing evidence.  Latencies require
an explicit input/output causal or correlation identifier; nearby rows are not
treated as causally related.  Input-receipt timing is separate from speech-end
timing: the latter is emitted only when the row has an explicit, calibrated
``speech_ended_at`` value.  This module measures orchestration evidence only and
makes no clinical or real-world outcome claim.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


_ROW_TYPES = {"input", "output"}
_CORRELATION_KEYS = (
    "correlation_id",
    "correction_id",
    "correction_event_id",
    "interrupt_id",
)
_CAUSAL_KEYS = (
    "caused_by_event_id",
    "caused_by",
    "in_response_to_event_id",
    "in_response_to",
    "source_event_id",
    "input_event_id",
    "causation_id",
)
_COMMITTED_BASIS = {"confirmed_tool_effect", "reconciled_tool_effect"}
_SUBSTANTIVE_OUTPUTS = {"final", "clarify"}


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _event_value(event: Mapping[str, Any], key: str) -> Any:
    """Read an envelope field, then its extensible payload field."""

    if key in event:
        return event[key]
    payload = _as_mapping(event.get("payload"))
    return payload.get(key) if payload is not None else None


def _event_kind(event: Mapping[str, Any]) -> str | None:
    kind = event.get("kind")
    return kind if isinstance(kind, str) else None


def _event_id(event: Mapping[str, Any]) -> str | None:
    value = event.get("event_id")
    return value if isinstance(value, str) and value else None


def _identifiers(event: Mapping[str, Any], keys: Iterable[str]) -> set[str]:
    values: set[str] = set()
    for key in keys:
        value = _event_value(event, key)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = _as_mapping(event.get("payload"))
    return payload if payload is not None else {}


def _observed_at(row: Mapping[str, Any]) -> float | None:
    value = row.get("observed_at")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _speech_ended_at(row: Mapping[str, Any]) -> float | None:
    """Read only the explicit calibrated row field, never transcript receipt time."""

    value = row.get("speech_ended_at")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _load_rows(source: str | Path | Iterable[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], int]:
    """Load JSONL rows and count malformed rows without fabricating evidence."""

    malformed = 0
    rows: list[Mapping[str, Any]] = []
    if isinstance(source, (str, Path)):
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except (TypeError, ValueError):
                malformed += 1
                continue
            if isinstance(value, Mapping):
                rows.append(value)
            else:
                malformed += 1
        return rows, malformed
    for value in source:
        if isinstance(value, Mapping):
            rows.append(value)
        else:
            malformed += 1
    return rows, malformed


def _quantiles(values: list[float]) -> dict[str, float | int] | None:
    """Return auditable quantiles with their supporting sample count."""

    if not values:
        return None
    ordered = sorted(values)

    def percentile(probability: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        fraction = position - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    # Keep JSON reports readable and deterministic across binary float subtraction.
    def rounded(value: float) -> float:
        return round(value, 9)
    return {
        "sample_count": len(ordered),
        "min_s": rounded(ordered[0]),
        "p50_s": rounded(percentile(0.50)),
        "p95_s": rounded(percentile(0.95)),
        "p99_s": rounded(percentile(0.99)),
        "max_s": rounded(ordered[-1]),
    }


def _is_end_of_speech(event: Mapping[str, Any]) -> bool:
    kind = _event_kind(event)
    if kind in {"speech_end", "turn_end", "end_of_speech"}:
        return True
    payload = _payload(event)
    return kind in {"transcript", "audio"} and payload.get("final") is True


def _is_correction(event: Mapping[str, Any]) -> bool:
    kind = _event_kind(event)
    payload = _payload(event)
    if kind in {"correction", "user_correction"}:
        return True
    if payload.get("is_correction") is True or payload.get("correction") is True:
        return True
    return payload.get("event_role") == "correction"


def _same_session(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    first_session = first.get("session_id")
    second_session = second.get("session_id")
    return isinstance(first_session, str) and isinstance(second_session, str) and first_session == second_session


def _output_causally_matches(output: Mapping[str, Any], source: Mapping[str, Any]) -> bool:
    if not _same_session(output, source):
        return False
    source_event_id = _event_id(source)
    source_correlations = _identifiers(source, _CORRELATION_KEYS)
    output_causal = _identifiers(output, _CAUSAL_KEYS)
    if source_event_id and source_event_id in output_causal:
        return True
    output_correlations = _identifiers(output, _CORRELATION_KEYS)
    return bool(source_correlations and source_correlations.intersection(output_correlations))


def _correction_cancel_latencies(
    records: list[tuple[str, Mapping[str, Any], float | None, Mapping[str, Any]]]
) -> list[float]:
    corrections: list[tuple[Mapping[str, Any], float, set[str]]] = []
    latencies: list[float] = []
    for row_type, event, observed_at, _ in records:
        if row_type == "input" and observed_at is not None and _is_correction(event):
            explicit_ids = _identifiers(event, _CORRELATION_KEYS)
            if _event_id(event):
                explicit_ids.add(_event_id(event))
            # A correction without an explicit identity cannot establish causality.
            if explicit_ids:
                corrections.append((event, observed_at, explicit_ids))
            continue
        if row_type != "output" or _event_kind(event) != "cancel_call" or observed_at is None:
            continue
        cancel_ids = _identifiers(event, _CORRELATION_KEYS)
        cancel_ids.update(_identifiers(event, _CAUSAL_KEYS))
        if not cancel_ids:
            continue
        candidates = [
            item for item in corrections
            if item[1] <= observed_at and item[2].intersection(cancel_ids) and _same_session(event, item[0])
        ]
        if candidates:
            _, correction_at, _ = max(candidates, key=lambda item: item[1])
            latencies.append(observed_at - correction_at)
    return latencies


def _response_latencies(
    records: list[tuple[str, Mapping[str, Any], float | None, Mapping[str, Any]]],
    output_kinds: set[str],
    source_clock: str,
) -> list[float]:
    inputs = [
        (event, observed_at if source_clock == "input_receipt" else _speech_ended_at(row))
        for row_type, event, observed_at, row in records
        if row_type == "input" and observed_at is not None and _is_end_of_speech(event)
    ]
    inputs = [(event, source_at) for event, source_at in inputs if source_at is not None]
    values: list[float] = []
    first_outputs: dict[tuple[str, str], tuple[float, float]] = {}
    for row_type, event, observed_at, _ in records:
        if row_type != "output" or _event_kind(event) not in output_kinds or observed_at is None:
            continue
        for input_event, input_at in inputs:
            if input_at > observed_at or not _output_causally_matches(event, input_event):
                continue
            source_identity = _event_id(input_event) or next(iter(_identifiers(input_event, _CORRELATION_KEYS)), None)
            session_id = input_event.get("session_id")
            if source_identity is None or not isinstance(session_id, str):
                continue
            source_key = (session_id, source_identity)
            latency = observed_at - input_at
            current = first_outputs.get(source_key)
            if current is None or observed_at < current[0]:
                first_outputs[source_key] = (observed_at, latency)
    values.extend(latency for _, latency in first_outputs.values())
    return values


def _expected_slots(metadata: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for candidate in (
        metadata.get("expected_slots"),
        _as_mapping(metadata.get("labels")) and _as_mapping(metadata["labels"]).get("expected_slots"),
        _as_mapping(metadata.get("labels")) and _as_mapping(metadata["labels"]).get("slots"),
    ):
        if isinstance(candidate, Mapping) and candidate:
            return candidate
    return None


def _final_slot_accuracy(
    records: list[tuple[str, Mapping[str, Any], float | None, Mapping[str, Any]]], metadata: Mapping[str, Any]
) -> tuple[float | None, dict[str, int] | None]:
    expected = _expected_slots(metadata)
    if expected is None:
        return None, None
    finals = [event for row_type, event, _, _ in records if row_type == "output" and _event_kind(event) == "final"]
    if not finals:
        return None, {"correct": 0, "labeled": 0, "sample_count": 0}
    final = finals[-1]
    state = _as_mapping(final.get("state")) or _as_mapping(_payload(final).get("state")) or {}
    slots = _as_mapping(state.get("slots")) or {}
    correct = 0
    for name, expected_value in expected.items():
        actual = _as_mapping(slots.get(name))
        actual_value = actual.get("value") if actual is not None else slots.get(name)
        if actual_value == expected_value:
            correct += 1
    labeled = len(expected)
    return correct / labeled, {"correct": correct, "labeled": labeled, "sample_count": 1}


def evaluate_trace(source: str | Path | Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute evidence-aware metrics from a typed trace or JSONL path.

    The result intentionally distinguishes absent evidence (``None``) from a
    measured zero.  Invalid rows are reported in ``trace_quality`` and do not
    become synthetic events.
    """

    rows, malformed = _load_rows(source)
    metadata: dict[str, Any] = {}
    records: list[tuple[str, Mapping[str, Any], float | None, Mapping[str, Any]]] = []
    ignored_rows = malformed
    for row in rows:
        row_type = row.get("type")
        if row_type == "run_metadata":
            nested = _as_mapping(row.get("metadata"))
            if nested:
                metadata.update(nested)
            metadata.update({key: value for key, value in row.items() if key != "type"})
            continue
        if row_type not in _ROW_TYPES or not isinstance(row.get("event"), Mapping):
            ignored_rows += 1
            continue
        records.append((row_type, row["event"], _observed_at(row), row))

    input_counts = Counter(_event_kind(event) or "unknown" for typ, event, _, _ in records if typ == "input")
    output_counts = Counter(_event_kind(event) or "unknown" for typ, event, _, _ in records if typ == "output")

    operation_calls: defaultdict[tuple[str | None, str], list[tuple[str, str]]] = defaultdict(list)
    call_to_operation: dict[tuple[str | None, str], tuple[str | None, str]] = {}
    call_to_effect: dict[tuple[str | None, str], str] = {}
    operation_display: dict[tuple[str | None, str], str] = {}
    operation_sessions: defaultdict[str, set[str | None]] = defaultdict(set)
    manifest_effects: defaultdict[str | None, dict[str, str]] = defaultdict(dict)
    for typ, event, _, _ in records:
        if typ != "input" or _event_kind(event) != "session_start":
            continue
        for tool in _payload(event).get("tools", []):
            if not isinstance(tool, Mapping):
                continue
            name = tool.get("name")
            effect = tool.get("effect")
            if isinstance(name, str) and effect in {"read", "write"}:
                manifest_effects[event.get("session_id")][name] = effect
    for typ, event, _, _ in records:
        if typ != "output" or _event_kind(event) != "tool_call":
            continue
        operation_id = _event_value(event, "operation_id")
        if not isinstance(operation_id, str) or not operation_id:
            continue
        call_id = _event_value(event, "call_id")
        if not isinstance(call_id, str) or not call_id:
            call_id = _event_id(event) or f"event:{len(operation_calls[(event.get('session_id'), operation_id)])}"
        event_id = _event_id(event) or call_id
        operation_key = (event.get("session_id"), operation_id)
        operation_calls[operation_key].append((call_id, event_id))
        call_to_operation[(event.get("session_id"), call_id)] = operation_key
        effect = _event_value(event, "effect")
        if effect not in {"read", "write"}:
            tool = _event_value(event, "tool")
            effect = manifest_effects[event.get("session_id")].get(tool) if isinstance(tool, str) else None
        if effect in {"read", "write"}:
            call_to_effect[(event.get("session_id"), call_id)] = effect
        operation_display[operation_key] = operation_id
        operation_sessions[operation_id].add(event.get("session_id"))

    def display_operation(operation_key: tuple[str | None, str]) -> str:
        operation_id = operation_display[operation_key]
        if len(operation_sessions[operation_id]) == 1:
            return operation_id
        return f"{operation_key[0]}:{operation_id}"

    repeated_operations = {
        display_operation(operation_key): len({call_id for call_id, _ in attempts})
        for operation_key, attempts in operation_calls.items()
        if len({call_id for call_id, _ in attempts}) > 1
    }
    operation_id_observations = sum(len(attempts) for attempts in operation_calls.values())
    distinct_call_count = len({
        (operation_key[0], call_id)
        for operation_key, attempts in operation_calls.items()
        for call_id, _ in attempts
    })
    repeated_operation_attempts = sum(count - 1 for count in repeated_operations.values())
    duplicate_delivery_events = sum(
        len(attempts) - len({call_id for call_id, _ in attempts}) for attempts in operation_calls.values()
    )

    outcome_history: defaultdict[tuple[str | None, str], list[tuple[str, str, str]]] = defaultdict(list)
    unknown_effect_outcomes = 0
    for typ, event, _, _ in records:
        kind = _event_kind(event)
        payload = _payload(event)
        outcome: str | None = None
        if typ == "input" and kind == "tool_result":
            result = _as_mapping(payload.get("result")) or {}
            if result.get("outcome") == "committed" or payload.get("committed") is True:
                outcome = "committed"
            elif result.get("outcome") == "no_effect":
                outcome = "not_committed"
            elif result.get("outcome") == "unknown" or payload.get("status") == "unknown":
                outcome = "unknown"
            elif payload.get("committed") is False and payload.get("status") in {"failed", "cancelled"}:
                outcome = "not_committed"
        elif typ == "output" and kind == "final" and payload.get("basis") in _COMMITTED_BASIS:
            outcome = "committed"
        if outcome is None:
            continue
        call_id = _event_value(event, "call_id")
        operation_id = _event_value(event, "operation_id")
        result = _as_mapping(payload.get("result")) or {}
        normalized_outcome = result.get("outcome")
        normalized_operation_id = result.get("operation_id")
        normalized_status_shape = (
            isinstance(normalized_operation_id, str)
            and bool(normalized_operation_id)
            and normalized_outcome in {"committed", "no_effect", "unknown"}
        )
        if not isinstance(operation_id, str) or not operation_id:
            operation_id = normalized_operation_id if isinstance(normalized_operation_id, str) else ""
        if not isinstance(call_id, str) or not call_id:
            call_id = ""
        session_id = event.get("session_id")
        call_key = (session_id, call_id)
        call_effect = call_to_effect.get(call_key)
        is_normalized_status = normalized_status_shape and (
            call_effect != "read" or payload.get("status") == "success"
        )
        if typ == "input" and kind == "tool_result" and call_effect is None:
            unknown_effect_outcomes += 1
        # Read calls are informational unless the executor returned the
        # normalized operation status used to reconcile a write.  For legacy
        # traces without an effect-bearing tool_call, preserve the old status
        # interpretation and record the evidence limitation below.
        if call_effect == "read" and not is_normalized_status:
            continue
        operation_key = (session_id, operation_id) if operation_id else call_to_operation.get(call_key)
        if operation_key is None:
            operation_key = (session_id, f"call:{call_id}" if call_id else f"event:{_event_id(event) or len(outcome_history)}")
        attempt_key = call_id or _event_id(event) or f"event:{len(outcome_history[operation_key])}"
        outcome_history[operation_key].append((attempt_key, outcome, _event_id(event) or attempt_key))

    def resolve(statuses: set[str]) -> str:
        if "committed" in statuses:
            return "committed"
        if "not_committed" in statuses:
            return "not_committed"
        return "unknown"

    attempt_resolved: dict[tuple[tuple[str | None, str], str], str] = {}
    logical_resolved: dict[tuple[str | None, str], str] = {}
    conflicts: dict[str, list[str]] = {}
    for operation_key, history in outcome_history.items():
        by_attempt: defaultdict[str, set[str]] = defaultdict(set)
        for attempt_key, outcome, _ in history:
            by_attempt[attempt_key].add(outcome)
        for attempt_key, statuses in by_attempt.items():
            attempt_resolved[(operation_key, attempt_key)] = resolve(statuses)
        statuses = set(attempt_resolved[(operation_key, attempt_key)] for attempt_key in by_attempt)
        logical_resolved[operation_key] = resolve(statuses)
        for attempt_key, attempt_statuses in by_attempt.items():
            if {"committed", "not_committed"}.issubset(attempt_statuses):
                display = display_operation(operation_key) if operation_key in operation_display else operation_key[1]
                conflicts[display] = sorted(attempt_statuses)

    outcome_counts = Counter(logical_resolved.values())
    outcomes = None
    if logical_resolved:
        outcomes = {
            "sample_count": len(logical_resolved),
            "counts": {key: outcome_counts.get(key, 0) for key in ("committed", "not_committed", "unknown")},
        }
    attempt_outcome_counts = Counter(attempt_resolved.values())
    attempt_outcomes = None
    if attempt_resolved:
        attempt_outcomes = {
            "sample_count": len(attempt_resolved),
            "counts": {
                key: attempt_outcome_counts.get(key, 0)
                for key in ("committed", "not_committed", "unknown")
            },
        }

    correction_latency = _quantiles(_correction_cancel_latencies(records))
    acknowledgement_receipt_latency = _quantiles(
        _response_latencies(records, {"acknowledge"}, "input_receipt")
    )
    substantive_receipt_latency = _quantiles(
        _response_latencies(records, _SUBSTANTIVE_OUTPUTS, "input_receipt")
    )
    acknowledgement_speech_end_latency = _quantiles(
        _response_latencies(records, {"acknowledge"}, "speech_end")
    )
    substantive_speech_end_latency = _quantiles(
        _response_latencies(records, _SUBSTANTIVE_OUTPUTS, "speech_end")
    )
    slot_accuracy, slot_detail = _final_slot_accuracy(records, metadata)

    event_counts = {
        "input": dict(sorted(input_counts.items())),
        "output": dict(sorted(output_counts.items())),
        "total": len(records),
    }
    result: dict[str, Any] = {
        "schema_version": "trace-metrics.v1",
        "backend": metadata.get("backend"),
        "config": metadata.get("config", metadata.get("configuration")),
        "run_metadata": metadata,
        "event_counts": event_counts,
        "operation_ids": {
            "observed_call_events": operation_id_observations,
            "unique": len(operation_calls),
            "distinct_call_ids": distinct_call_count,
            "repeated_operation_values": len(repeated_operations),
            "repeated_operation_attempts": repeated_operation_attempts,
            "duplicate_delivery_events": duplicate_delivery_events,
            "repeated": repeated_operations,
        },
        "committed_effect_outcomes": outcomes,
        "attempt_outcomes": attempt_outcomes,
        "conflicting_terminal_evidence": conflicts or None,
        "slot_accuracy": slot_accuracy,
        "slot_accuracy_detail": slot_detail,
        "latency": {
            "correction_to_cancellation_s": correction_latency,
            "acknowledgment_from_input_receipt_s": acknowledgement_receipt_latency,
            "substantive_response_from_input_receipt_s": substantive_receipt_latency,
            "acknowledgment_from_speech_end_s": acknowledgement_speech_end_latency,
            "substantive_response_from_speech_end_s": substantive_speech_end_latency,
        },
        "trace_quality": {
            "typed_rows": len(records),
            "ignored_rows": ignored_rows,
            "outcomes_with_unknown_effect": unknown_effect_outcomes,
            "rows_with_observed_at": sum(observed_at is not None for _, _, observed_at, _ in records),
            "rows_with_speech_ended_at": sum(_speech_ended_at(row) is not None for _, _, _, row in records),
        },
        "limitation": "Orchestration evidence only; no clinical, user-benefit, or official-score claim.",
    }
    return result


def metrics(source: str | Path | Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compatibility alias for callers that use the replay evaluator name."""

    return evaluate_trace(source)


__all__ = ["evaluate_trace", "metrics"]
