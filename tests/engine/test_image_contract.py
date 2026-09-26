import pytest
from pydantic import ValidationError

from accessflow.contracts import (
    ImageRecordView,
    ImageSlotBinding,
    Observation,
    PlanProposal,
    SessionView,
    Snapshot,
)


def _observation(*, frame_id="frame-1", event_id="event-1", revision=0):
    return Observation(
        event_id=event_id,
        source_id=frame_id,
        revision=revision,
        modality="image",
        text="The receipt total is $18.20.",
        final=True,
        backend="vision",
    )


def _record(*, ordinal=1, frame_id="frame-1", event_id="event-1", revision=0):
    return ImageRecordView(
        ordinal=ordinal,
        frame_id=frame_id,
        event_id=event_id,
        received_at=12.5,
        capture_timestamp=10.0,
        capture_time_provenance="camera metadata",
        processing_revision=revision,
        status="observed",
        observation=_observation(frame_id=frame_id, event_id=event_id, revision=revision),
    )


def _legacy_session_view():
    # These are the pre-D4 required fields. New additive projections must default.
    return SessionView(session_id="session-1", state=Snapshot(), observations=[], results=[])


def test_legacy_session_and_plan_proposals_omit_additive_image_fields():
    view = _legacy_session_view()
    proposal = PlanProposal()

    assert view.image_history == []
    assert "image_history" not in view.model_fields_set
    assert proposal.image_bindings == {}
    assert "image_bindings" not in proposal.model_fields_set
    assert view.model_dump(mode="json")["image_history"] == []
    assert proposal.model_dump(mode="json")["image_bindings"] == {}
    assert Snapshot().slot_image_sources == {}


def test_image_history_and_slot_bindings_round_trip_without_paths():
    binding = ImageSlotBinding(
        image_reference="Image 2",
        event_id="event-2",
        processing_revision=3,
        evidence_quote="Total: $18.20",
    )
    view = SessionView(
        session_id="session-1",
        state=Snapshot(slot_image_sources={"total": binding}),
        observations=[],
        results=[],
        image_history=[_record(), _record(ordinal=2, frame_id="frame-2", event_id="event-2", revision=3)],
    )
    proposal = PlanProposal(image_bindings={"total": binding})

    restored_view = SessionView.model_validate_json(view.model_dump_json())
    restored_proposal = PlanProposal.model_validate_json(proposal.model_dump_json())
    dumped = view.model_dump(mode="json")

    assert [(image.ordinal, image.frame_id) for image in restored_view.image_history] == [
        (1, "frame-1"), (2, "frame-2")
    ]
    assert restored_view.image_history[1].observation.event_id == "event-2"
    assert restored_proposal.image_bindings["total"].event_id == "event-2"
    assert restored_proposal.image_bindings["total"].processing_revision == 3
    assert restored_view.state.slot_image_sources["total"] == binding
    assert "path" not in str(dumped).lower()


def test_image_contract_rejects_unknown_fields_and_oversized_collections_or_quotes():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ImageRecordView.model_validate({**_record().model_dump(), "path": "private/local.png"})

    with pytest.raises(ValidationError, match="extra_forbidden"):
        ImageSlotBinding.model_validate({
            "image_reference": "frame-1",
            "event_id": "event-1",
            "processing_revision": 0,
            "evidence_quote": "total",
            "local_path": "private/local.png",
        })

    with pytest.raises(ValidationError):
        SessionView(
            session_id="session-1",
            state=Snapshot(),
            observations=[],
            results=[],
            image_history=[_record(ordinal=index + 1, frame_id=f"f{index}", event_id=f"e{index}")
                           for index in range(9)],
        )

    with pytest.raises(ValidationError):
        ImageSlotBinding(
            image_reference="frame-1",
            event_id="event-1",
            processing_revision=0,
            evidence_quote="x" * 513,
        )


def test_image_binding_requires_explicit_non_path_source_and_matching_evidence_shape():
    for invalid_reference in ("", "latest", "Image 0", "C:\\private\\image.png", "../image.png"):
        with pytest.raises(ValidationError):
            ImageSlotBinding(
                image_reference=invalid_reference,
                event_id="event-1",
                processing_revision=0,
                evidence_quote="Total: $18.20",
            )

    with pytest.raises(ValidationError, match="must match its accepted record"):
        ImageRecordView(
            ordinal=1,
            frame_id="frame-1",
            event_id="event-1",
            received_at=1,
            processing_revision=1,
            status="observed",
            observation=_observation(revision=0),
        )
