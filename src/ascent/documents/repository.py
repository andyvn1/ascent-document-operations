"""Repository layer for documents and audit events.

Workflow rules (which status transitions are valid, and always writing
an audit event alongside a status change) live here, not scattered
across API route handlers, so there is exactly one place that can move
a document between states.

Audit events are append-only by omission: this module deliberately does
not expose any update or delete function for AuditEvent. Nothing here
enforces that at the database level (no trigger) — the guarantee is
"the only code path that writes an event is _record_event, and nothing
calls session.merge/update on an existing one," which is enough for the
MVP. A database-level trigger is a possible future hardening step if
that guarantee ever needs to hold even against a bug, not just against
following the API.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ascent.documents.models import AuditEvent, Document, DocumentStatus, DocumentType

_ALLOWED_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.UPLOADED: frozenset({DocumentStatus.PROCESSING}),
    DocumentStatus.PROCESSING: frozenset({DocumentStatus.EXTRACTED}),
    DocumentStatus.EXTRACTED: frozenset({DocumentStatus.IN_REVIEW}),
    DocumentStatus.IN_REVIEW: frozenset({DocumentStatus.APPROVED, DocumentStatus.REJECTED}),
    DocumentStatus.APPROVED: frozenset({DocumentStatus.EXPORTED}),
    DocumentStatus.REJECTED: frozenset(),
    DocumentStatus.EXPORTED: frozenset(),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: DocumentStatus, requested: DocumentStatus) -> None:
        self.current = current
        self.requested = requested
        super().__init__(f"cannot transition document from {current!s} to {requested!s}")


def create_document(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    uploaded_by_user_id: uuid.UUID,
    original_filename: str,
    storage_key: str,
) -> Document:
    document = Document(
        tenant_id=tenant_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=original_filename,
        storage_key=storage_key,
        document_type=DocumentType.UNRECOGNIZED,
        status=DocumentStatus.UPLOADED,
    )
    session.add(document)
    session.flush()

    _record_event(
        session,
        document=document,
        event_type="uploaded",
        user_id=uploaded_by_user_id,
        event_data={"original_filename": original_filename},
    )
    return document


def transition_status(
    session: Session,
    document: Document,
    *,
    new_status: DocumentStatus,
    user_id: uuid.UUID | None = None,
    event_data: dict[str, Any] | None = None,
) -> Document:
    allowed = _ALLOWED_TRANSITIONS[document.status]
    if new_status not in allowed:
        raise InvalidTransitionError(document.status, new_status)

    previous_status = document.status
    document.status = new_status
    session.flush()

    _record_event(
        session,
        document=document,
        event_type=new_status.value,
        user_id=user_id,
        event_data={
            "from": previous_status.value,
            "to": new_status.value,
            **(event_data or {}),
        },
    )
    return document


def list_audit_events(
    session: Session, *, tenant_id: uuid.UUID, document_id: uuid.UUID
) -> list[AuditEvent]:
    return list(
        session.query(AuditEvent)
        .filter(AuditEvent.tenant_id == tenant_id, AuditEvent.document_id == document_id)
        .order_by(AuditEvent.created_at)
        .all()
    )


def _record_event(
    session: Session,
    *,
    document: Document,
    event_type: str,
    user_id: uuid.UUID | None,
    event_data: dict[str, Any],
) -> AuditEvent:
    event = AuditEvent(
        tenant_id=document.tenant_id,
        document_id=document.id,
        user_id=user_id,
        event_type=event_type,
        event_data=event_data,
    )
    session.add(event)
    session.flush()
    return event