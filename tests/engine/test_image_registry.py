import pytest

from accessflow.contracts import Frame, FrameEvent, Observation
from accessflow.image_registry import ImageReferenceError, ImageRegistry, ImageRegistryError


def frame(frame_id, event_id, timestamp=0, *, session="session"):
    return FrameEvent(session_id=session, event_id=event_id, timestamp=timestamp,
                      payload=Frame(path=f"{frame_id}.png", frame_id=frame_id))


def image_observation(item, text, *, revision=0):
    return Observation(event_id=item.event_id, source_id=item.frame_id, revision=revision,
                        modality="image", text=text, final=True, backend="fixture")


def test_partial_image_cannot_become_available_evidence():
    registry = ImageRegistry("session")
    item = registry.admit(frame("f1", "e1"), received_at=1)
    partial = image_observation(item, "tentative").model_copy(update={"final": False})
    with pytest.raises(ImageRegistryError, match="partial image"):
        registry.record_observation("f1", partial)
    assert registry.resolve(1).status == "pending"
    assert registry.resolve(1).observation is None


def test_delayed_older_image_result_stays_on_its_own_record():
    registry = ImageRegistry("session", capacity=3)
    first = registry.admit(frame("f1", "e1", timestamp=50), received_at=1.0,
                           capture_timestamp=900, capture_time_provenance="camera metadata")
    second = registry.admit(frame("f2", "e2", timestamp=10), received_at=2.0,
                            capture_timestamp=100, capture_time_provenance="camera metadata")

    registry.record_observation("f2", image_observation(second, "second arrived first"))
    registry.record_observation("f1", image_observation(first, "first arrived late"))

    view = registry.view()
    assert [(item.ordinal, item.frame_id) for item in view] == [(1, "f1"), (2, "f2")]
    assert view[0].observation.text == "first arrived late"
    assert view[1].observation.text == "second arrived first"
    assert view[0].received_at == 1.0 and view[1].received_at == 2.0
    assert view[0].capture_timestamp == 900 and view[1].capture_timestamp == 100


def test_duplicate_frame_id_cannot_relabel_or_replace_existing_image():
    registry = ImageRegistry("session")
    original = registry.admit(frame("same", "e1"), received_at=1)

    with pytest.raises(ImageRegistryError, match="duplicate frames cannot relabel"):
        registry.admit(frame("same", "e2"), received_at=2)

    assert registry.view() == (original,)
    assert registry.latest().event_id == "e1"


def test_invalidation_advances_revision_and_rejects_late_prior_result():
    registry = ImageRegistry("session")
    accepted = registry.admit(frame("f1", "e1"), received_at=1)
    invalidated = registry.invalidate("f1", expected_revision=0)
    assert invalidated.processing_revision == 1
    assert invalidated.status == "pending"

    with pytest.raises(ImageRegistryError, match="stale observation revision"):
        registry.record_observation("f1", image_observation(accepted, "stale", revision=0))

    registry.record_observation("f1", image_observation(accepted, "current", revision=1))
    assert registry.resolve("Image 1").observation.text == "current"


def test_failed_image_keeps_identity_and_rejects_result_until_invalidated():
    registry = ImageRegistry("session")
    accepted = registry.admit(frame("f1", "e1"), received_at=1)
    failed = registry.mark_failed("f1", event_id="e1", revision=0, reason="decode failed")
    assert failed.ordinal == 1 and failed.status == "failed"
    assert failed.failure == "decode failed"
    with pytest.raises(ImageRegistryError, match="cannot observe image in 'failed' status"):
        registry.record_observation("f1", image_observation(accepted, "late result"))

    reopened = registry.invalidate("f1", expected_revision=0)
    assert reopened.ordinal == 1 and reopened.status == "pending"
    assert reopened.failure is None


def test_capacity_rejects_instead_of_evicting_and_ordinals_are_stable():
    registry = ImageRegistry("session", capacity=1)
    registry.admit(frame("f1", "e1"), received_at=1)

    with pytest.raises(ImageRegistryError, match=r"capacity \(1\) reached"):
        registry.admit(frame("f2", "e2"), received_at=2)

    assert [item.frame_id for item in registry.view()] == ["f1"]
    assert registry.resolve(1).ordinal == 1


def test_ambiguous_contextual_reference_requires_clarification():
    registry = ImageRegistry("session")
    registry.admit(frame("f1", "e1"), received_at=1)
    registry.admit(frame("f2", "e2"), received_at=2)

    with pytest.raises(ImageReferenceError, match="needs clarification"):
        registry.resolve("old image")
    assert registry.resolve("f1").ordinal == 1
    assert registry.resolve(2).frame_id == "f2"


def test_view_is_detached_and_record_fields_are_frozen():
    registry = ImageRegistry("session")
    accepted = registry.admit(frame("f1", "e1"), received_at=1)
    observed = registry.record_observation("f1", image_observation(accepted, "grounded"))
    observed.observation.text = "caller mutation"

    assert registry.resolve("f1").observation.text == "grounded"
    with pytest.raises((AttributeError, TypeError)):
        registry.resolve("f1").ordinal = 9
