from accessflow.evaluation.trace_metrics import evaluate_trace


def row(row_type, kind, at, *, event_id=None, payload=None, speech_ended_at=None, **fields):
    event = {"kind": kind, "session_id": fields.pop("session_id", "s1"), **fields}
    if event_id is not None:
        event["event_id"] = event_id
    if payload is not None:
        event["payload"] = payload
    result = {"type": row_type, "event": event, "observed_at": at}
    if speech_ended_at is not None:
        result["speech_ended_at"] = speech_ended_at
    return result


def test_metrics_keep_retries_distinct_and_count_only_explicit_effect_outcomes():
    trace = [
        {"type": "run_metadata", "backend": "offline-fake", "config": {"model": "test"}},
        row("output", "tool_call", 1.0, event_id="call-event-1", call_id="call-1", operation_id="op-retry"),
        row("output", "tool_call", 1.1, event_id="call-event-2", call_id="call-2", operation_id="op-retry"),
        row("output", "tool_call", 1.2, event_id="call-event-3", call_id="call-3", operation_id="op-distinct"),
        row("output", "tool_call", 1.3, event_id="call-event-3-delivery", call_id="call-3", operation_id="op-distinct"),
        row("input", "tool_result", 2.0, call_id="call-1", payload={
            "status": "unknown", "committed": False, "result": {},
        }),
        row("input", "tool_result", 2.1, call_id="call-2", payload={
            "status": "success", "committed": True, "result": {},
        }),
        row("input", "tool_result", 2.2, call_id="call-3", payload={
            "status": "failed", "committed": False, "result": {},
        }),
    ]

    result = evaluate_trace(trace)

    assert result["backend"] == "offline-fake"
    assert result["config"] == {"model": "test"}
    assert result["event_counts"]["output"]["tool_call"] == 4
    assert result["operation_ids"]["unique"] == 2
    assert result["operation_ids"]["distinct_call_ids"] == 3
    assert result["operation_ids"]["repeated_operation_values"] == 1
    assert result["operation_ids"]["repeated_operation_attempts"] == 1
    assert result["operation_ids"]["duplicate_delivery_events"] == 1
    assert result["committed_effect_outcomes"]["sample_count"] == 2
    assert result["committed_effect_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 1, "unknown": 0,
    }
    assert result["attempt_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 1, "unknown": 1,
    }


def test_committed_evidence_resolves_unknown_and_conflicting_terminal_evidence_is_reported():
    trace = [
        row("output", "tool_call", 1.0, call_id="call-1", operation_id="op-1"),
        row("input", "tool_result", 1.1, call_id="call-1", payload={
            "status": "unknown", "committed": False,
        }),
        row("output", "final", 1.2, call_id="call-1", payload={
            "basis": "confirmed_tool_effect",
        }),
        row("output", "tool_call", 2.0, call_id="call-2", operation_id="op-2"),
        row("input", "tool_result", 2.1, call_id="call-2", payload={
            "status": "failed", "committed": False,
        }),
        row("output", "final", 2.2, call_id="call-2", operation_id="op-2", payload={
            "basis": "confirmed_tool_effect",
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"]["counts"] == {
        "committed": 2, "not_committed": 0, "unknown": 0,
    }
    assert result["conflicting_terminal_evidence"] == {"op-2": ["committed", "not_committed"]}


def test_latency_requires_explicit_causality_and_reports_quantile_samples():
    trace = [
        {"type": "run_metadata", "labels": {"expected_slots": {"day": "Wednesday"}}},
        row("input", "correction", 10.0, event_id="corr-1", payload={"correlation_id": "corr-1"}),
        row("output", "cancel_call", 10.4, event_id="cancel-1",
            payload={"correlation_id": "corr-1", "call_id": "call-1", "operation_id": "op-1"}),
        row("input", "transcript", 20.0, event_id="speech-1",
            payload={"final": True, "correlation_id": "turn-1"}, speech_ended_at=19.7),
        row("output", "acknowledge", 20.2, event_id="ack-1",
            payload={"in_response_to_event_id": "speech-1", "text": "I'll check that."}),
        row("output", "final", 20.8, event_id="final-1",
            payload={"in_response_to_event_id": "speech-1", "basis": "informational"},
            state={"slots": {"day": {"value": "Wednesday"}}}),
    ]

    result = evaluate_trace(trace)

    assert result["latency"]["correction_to_cancellation_s"] == {
        "sample_count": 1, "min_s": 0.4, "p50_s": 0.4, "p95_s": 0.4, "p99_s": 0.4, "max_s": 0.4,
    }
    assert result["latency"]["acknowledgment_from_input_receipt_s"]["sample_count"] == 1
    assert result["latency"]["acknowledgment_from_input_receipt_s"]["p50_s"] == 0.2
    assert result["latency"]["substantive_response_from_input_receipt_s"]["sample_count"] == 1
    assert result["latency"]["substantive_response_from_input_receipt_s"]["p50_s"] == 0.8
    assert result["latency"]["acknowledgment_from_speech_end_s"]["p50_s"] == 0.5
    assert result["latency"]["substantive_response_from_speech_end_s"]["p50_s"] == 1.1
    assert result["slot_accuracy"] == 1.0


def test_missing_labels_and_causal_ids_are_missing_evidence_not_zeroes():
    trace = [
        row("input", "transcript", 1.0, event_id="speech-1", payload={"final": True}),
        row("output", "acknowledge", 1.1, event_id="ack-1", payload={"text": "okay"}),
        row("output", "final", 1.2, event_id="final-1", payload={"text": "done"}),
    ]

    result = evaluate_trace(trace)

    assert result["slot_accuracy"] is None
    assert result["latency"]["correction_to_cancellation_s"] is None
    assert result["latency"]["acknowledgment_from_input_receipt_s"] is None
    assert result["latency"]["substantive_response_from_input_receipt_s"] is None
    assert result["latency"]["acknowledgment_from_speech_end_s"] is None
    assert result["latency"]["substantive_response_from_speech_end_s"] is None
    assert result["committed_effect_outcomes"] is None
    assert result["trace_quality"]["ignored_rows"] == 0


def test_correction_event_id_can_be_explicit_causal_evidence_but_unknown_semantics_cannot():
    trace = [
        row("input", "correction", 5.0, event_id="corr-event", payload={}),
        row("output", "cancel_call", 5.3, payload={
            "caused_by_event_id": "corr-event",
        }),
        row("input", "transcript", 6.0, event_id="unknown-event", payload={"text": "actually Wednesday"}),
        row("output", "cancel_call", 6.3, payload={
            "caused_by_event_id": "unknown-event",
        }),
    ]

    result = evaluate_trace(trace)

    assert result["latency"]["correction_to_cancellation_s"]["p50_s"] == 0.3


def test_response_latency_uses_first_response_per_source_and_keeps_sessions_separate():
    trace = [
        row("input", "transcript", 10.0, event_id="same-id", payload={"final": True}, session_id="s1"),
        row("output", "acknowledge", 10.4, payload={"caused_by_event_id": "same-id"}, session_id="s2"),
        row("output", "acknowledge", 10.3, payload={"caused_by_event_id": "same-id"}, session_id="s1"),
        row("output", "acknowledge", 10.5, payload={"caused_by_event_id": "same-id"}, session_id="s1"),
        row("output", "error", 10.6, payload={"caused_by_event_id": "same-id"}, session_id="s1"),
        row("output", "clarify", 10.8, payload={"caused_by_event_id": "same-id"}, session_id="s1"),
        row("output", "final", 10.9, payload={"caused_by_event_id": "same-id"}, session_id="s1"),
    ]

    result = evaluate_trace(trace)

    assert result["latency"]["acknowledgment_from_input_receipt_s"]["sample_count"] == 1
    assert result["latency"]["acknowledgment_from_input_receipt_s"]["p50_s"] == 0.3
    assert result["latency"]["substantive_response_from_input_receipt_s"]["sample_count"] == 1
    assert result["latency"]["substantive_response_from_input_receipt_s"]["p50_s"] == 0.8


def test_retry_no_effect_then_commit_is_logical_commit_without_conflict():
    trace = [
        row("output", "tool_call", 1.0, call_id="attempt-1", operation_id="op-retry", effect="write"),
        row("input", "tool_result", 1.1, call_id="attempt-1", payload={
            "status": "success", "committed": False,
            "result": {"operation_id": "op-retry", "outcome": "no_effect"},
        }),
        row("output", "tool_call", 2.0, call_id="attempt-2", operation_id="op-retry", effect="write"),
        row("input", "tool_result", 2.1, call_id="attempt-2", payload={
            "status": "success", "committed": True,
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 0, "unknown": 0,
    }
    assert result["attempt_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 1, "unknown": 0,
    }
    assert result["conflicting_terminal_evidence"] is None


def test_same_call_no_effect_and_commit_is_conflicting_terminal_evidence():
    trace = [
        row("output", "tool_call", 1.0, call_id="attempt-1", operation_id="op-same", effect="write"),
        row("input", "tool_result", 1.1, call_id="attempt-1", payload={
            "status": "success", "committed": False,
            "result": {"operation_id": "op-same", "outcome": "no_effect"},
        }),
        row("output", "final", 1.2, call_id="attempt-1", operation_id="op-same", payload={
            "basis": "confirmed_tool_effect",
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 0, "unknown": 0,
    }
    assert result["conflicting_terminal_evidence"] == {
        "op-same": ["committed", "not_committed"],
    }


def test_failed_read_result_is_not_a_write_outcome():
    trace = [
        row("output", "tool_call", 1.0, call_id="read-1", operation_id="lookup-1", effect="read"),
        row("input", "tool_result", 1.1, call_id="read-1", payload={
            "status": "failed", "committed": False, "result": {},
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"] is None


def test_normalized_status_read_is_evidence_for_queried_write():
    trace = [
        row("output", "tool_call", 1.0, call_id="write-1", operation_id="op-status", effect="write"),
        row("input", "tool_result", 1.1, call_id="write-1", payload={
            "status": "unknown", "committed": False, "result": {},
        }),
        row("output", "tool_call", 2.0, call_id="status-1", operation_id="status-call", effect="read"),
        row("input", "tool_result", 2.1, call_id="status-1", payload={
            "status": "success", "committed": False,
            "result": {"operation_id": "op-status", "outcome": "committed"},
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"]["counts"] == {
        "committed": 1, "not_committed": 0, "unknown": 0,
    }


def test_failed_status_read_does_not_turn_incidental_normalized_fields_into_evidence():
    trace = [
        row("output", "tool_call", 1.0, call_id="status-1", operation_id="status-call", effect="read"),
        row("input", "tool_result", 1.1, call_id="status-1", payload={
            "status": "failed", "committed": False,
            "result": {"operation_id": "op-status", "outcome": "committed"},
        }),
    ]

    result = evaluate_trace(trace)

    assert result["committed_effect_outcomes"] is None


def test_distinct_call_ids_are_scoped_to_the_session():
    trace = [
        row("output", "tool_call", 1.0, call_id="same-call", operation_id="op-1", effect="write", session_id="s1"),
        row("output", "tool_call", 1.0, call_id="same-call", operation_id="op-1", effect="write", session_id="s2"),
    ]

    result = evaluate_trace(trace)

    assert result["operation_ids"]["distinct_call_ids"] == 2
