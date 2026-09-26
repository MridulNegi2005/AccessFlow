"""Bounded, session-local history for accepted image frames.

The registry owns attachment identity and ordering. Perception completion order does
not affect that order: a result is written only to the record named by its frame,
event, and processing revision.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from .contracts import FrameEvent, Observation

DEFAULT_IMAGE_CAPACITY = 8
_IMAGE_REFERENCE = re.compile(r"image\s+(\d+)", re.IGNORECASE)


class ImageRegistryError(ValueError):
    """A frame could not be safely admitted or updated in the image registry."""


class ImageReferenceError(ImageRegistryError):
    """A requested image reference is missing or ambiguous."""


@dataclass(frozen=True)
class ImageRecord:
    """Detached view of one accepted image.

    The dataclass itself is immutable. ``observation`` is a validated deep copy, so
    callers may inspect or mutate that copy without changing registry state.
    """

    session_id: str
    frame_id: str
    event_id: str
    ordinal: int
    received_at: float
    capture_timestamp: float | None
    capture_time_provenance: str | None
    processing_revision: int
    status: Literal["pending", "observed", "failed"]
    observation: Observation | None
    failure: str | None


@dataclass
class _MutableImageRecord:
    session_id: str
    frame_id: str
    event_id: str
    ordinal: int
    received_at: float
    capture_timestamp: float | None
    capture_time_provenance: str | None
    processing_revision: int = 0
    status: Literal["pending", "observed", "failed"] = "pending"
    observation: Observation | None = None
    failure: str | None = None


class ImageRegistry:
    """A bounded ordered registry for images accepted in one controller session."""

    def __init__(self, session_id: str, *, capacity: int = DEFAULT_IMAGE_CAPACITY):
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.session_id = session_id
        self.capacity = capacity
        self._records: list[_MutableImageRecord] = []
        self._by_frame_id: dict[str, _MutableImageRecord] = {}
        self._event_ids: set[str] = set()

    def admit(
        self,
        event: FrameEvent,
        *,
        received_at: float,
        capture_timestamp: float | None = None,
        capture_time_provenance: str | None = None,
    ) -> ImageRecord:
        """Admit a frame and assign its permanent one-based ordinal.

        ``received_at`` is the controller's server-side receipt time. Capture time is
        optional and untrusted; its provenance is retained as supplied and never used
        to sort or renumber records.
        """
        if event.session_id != self.session_id:
            raise ImageRegistryError("frame belongs to a different session")
        frame_id = event.payload.frame_id
        if not frame_id.strip():
            raise ImageRegistryError("frame_id must be a non-empty string")
        if event.event_id in self._event_ids:
            raise ImageRegistryError(f"event_id {event.event_id!r} was already admitted")
        if frame_id in self._by_frame_id:
            raise ImageRegistryError(
                f"frame_id {frame_id!r} was already admitted; duplicate frames cannot relabel an image"
            )
        if len(self._records) >= self.capacity:
            raise ImageRegistryError(f"image capacity ({self.capacity}) reached")
        self._validate_timestamp(received_at, "received_at")
        if capture_timestamp is None:
            if capture_time_provenance is not None:
                raise ImageRegistryError("capture time provenance requires a capture timestamp")
        else:
            self._validate_timestamp(capture_timestamp, "capture_timestamp")
            if not isinstance(capture_time_provenance, str) or not capture_time_provenance.strip():
                raise ImageRegistryError("capture timestamp requires non-empty provenance")

        record = _MutableImageRecord(
            session_id=self.session_id,
            frame_id=frame_id,
            event_id=event.event_id,
            ordinal=len(self._records) + 1,
            received_at=float(received_at),
            capture_timestamp=None if capture_timestamp is None else float(capture_timestamp),
            capture_time_provenance=capture_time_provenance,
        )
        self._records.append(record)
        self._by_frame_id[frame_id] = record
        self._event_ids.add(event.event_id)
        return self._copy_record(record)

    def record_observation(self, frame_id: str, observation: Observation) -> ImageRecord:
        """Store a validated observation on its matching pending source record."""
        record = self._get_frame(frame_id)
        if observation.modality != "image":
            raise ImageRegistryError("image registry accepts only image observations")
        if not observation.final:
            raise ImageRegistryError("partial image evidence cannot complete a record")
        if observation.source_id != record.frame_id or observation.event_id != record.event_id:
            raise ImageRegistryError("observation source/event does not match the accepted frame")
        if observation.revision != record.processing_revision:
            raise ImageRegistryError(
                f"stale observation revision {observation.revision}; current revision is "
                f"{record.processing_revision}"
            )
        if record.status != "pending":
            raise ImageRegistryError(f"cannot observe image in {record.status!r} status")
        record.observation = observation.model_copy(deep=True)
        record.status = "observed"
        record.failure = None
        return self._copy_record(record)

    def mark_failed(
        self, frame_id: str, *, event_id: str, revision: int, reason: str
    ) -> ImageRecord:
        """Mark only the matching in-flight image revision unavailable."""
        record = self._get_frame(frame_id)
        if event_id != record.event_id:
            raise ImageRegistryError("failure event_id does not match the accepted frame")
        if revision != record.processing_revision:
            raise ImageRegistryError(
                f"stale failure revision {revision}; current revision is {record.processing_revision}"
            )
        if record.status != "pending":
            raise ImageRegistryError(f"cannot fail image in {record.status!r} status")
        if not isinstance(reason, str) or not reason.strip():
            raise ImageRegistryError("failure reason must be a non-empty string")
        record.status = "failed"
        record.failure = reason
        record.observation = None
        return self._copy_record(record)

    def invalidate(self, frame_id: str, *, expected_revision: int) -> ImageRecord:
        """Invalidate prior processing and reopen this identity at the next revision."""
        record = self._get_frame(frame_id)
        if expected_revision != record.processing_revision:
            raise ImageRegistryError(
                f"cannot invalidate revision {expected_revision}; current revision is "
                f"{record.processing_revision}"
            )
        record.processing_revision += 1
        record.status = "pending"
        record.observation = None
        record.failure = None
        return self._copy_record(record)

    def resolve(self, reference: int | str) -> ImageRecord:
        """Resolve an explicit one-based ordinal or exact frame ID.

        Natural-language references such as ``"old image"`` are intentionally not
        guessed. Callers must clarify and pass a concrete ordinal or frame ID.
        """
        if isinstance(reference, bool):
            raise ImageReferenceError("image ordinal must be a positive integer")
        if isinstance(reference, int):
            ordinal = reference
        elif isinstance(reference, str):
            text = reference.strip()
            match = _IMAGE_REFERENCE.fullmatch(text)
            if match:
                ordinal = int(match.group(1))
            elif text in self._by_frame_id:
                return self._copy_record(self._by_frame_id[text])
            elif text.lower() in {"old", "older", "old image", "latest", "new", "new image", "this"}:
                raise ImageReferenceError(f"reference {reference!r} is contextual and needs clarification")
            else:
                raise ImageReferenceError(f"unknown image reference {reference!r}")
        else:
            raise ImageReferenceError("image reference must be an ordinal or frame ID")
        if ordinal < 1 or ordinal > len(self._records):
            raise ImageReferenceError(f"Image {ordinal} is not present in this session")
        return self._copy_record(self._records[ordinal - 1])

    def latest(self) -> ImageRecord | None:
        """Return the most recently admitted image, if any."""
        return self._copy_record(self._records[-1]) if self._records else None

    def view(self) -> tuple[ImageRecord, ...]:
        """Return a stable ordered tuple of detached records for a session view."""
        return tuple(self._copy_record(record) for record in self._records)

    @staticmethod
    def _validate_timestamp(value: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ImageRegistryError(f"{name} must be a finite non-negative number")
        if not math.isfinite(value) or value < 0:
            raise ImageRegistryError(f"{name} must be a finite non-negative number")

    def _get_frame(self, frame_id: str) -> _MutableImageRecord:
        if not isinstance(frame_id, str) or frame_id not in self._by_frame_id:
            raise ImageRegistryError(f"unknown frame_id {frame_id!r}")
        return self._by_frame_id[frame_id]

    @staticmethod
    def _copy_record(record: _MutableImageRecord) -> ImageRecord:
        return ImageRecord(
            session_id=record.session_id,
            frame_id=record.frame_id,
            event_id=record.event_id,
            ordinal=record.ordinal,
            received_at=record.received_at,
            capture_timestamp=record.capture_timestamp,
            capture_time_provenance=record.capture_time_provenance,
            processing_revision=record.processing_revision,
            status=record.status,
            observation=deepcopy(record.observation),
            failure=record.failure,
        )
