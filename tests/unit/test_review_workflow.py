"""Unit tests for the approval/rejection workflow.

Uses a fake Session (add()/flush() only, no real database) rather than
the integration db_session fixture -- workflow.py's functions only
mutate the in-memory Document object and construct an AuditEvent to
hand to session.add(), neither of which needs a real Postgres
connection to verify. Exhaustive coverage of every non-in_review status
(the parametrized test below) is only practical to run this fast
without one.
"""

import uuid

import pytest

from ascent.documents.models import AuditEvent, Document, DocumentStatus, DocumentType
from ascent.documents.repository import InvalidTransitionError
from ascent.documents.workflow import (
    MissingRejectionCommentError,
    approve_document,
    reject_document,
)


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        pass


def _make_document(*, status: DocumentStatus = DocumentStatus.IN_REVIEW) -> Document:
    return Document(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        uploaded_by_user_id=uuid.uuid4(),
        original_filename="invoice.pdf",
        storage_key="tenant/doc.pdf",
        document_type=DocumentType.INVOICE,
        status=status,
    )


def test_approve_document_sets_status_and_records_audit_event() -> None:
    session = _FakeSession()
    document = _make_document(status=DocumentStatus.IN_REVIEW)
    reviewer_id = uuid.uuid4()

    result = approve_document(session, document, user_id=reviewer_id)  # type: ignore[arg-type]

    assert result is document
    assert document.status == DocumentStatus.APPROVED
    audit_events = [obj for obj in session.added if isinstance(obj, AuditEvent)]
    assert len(audit_events) == 1
    assert audit_events[0].event_type == "approved"
    assert audit_events[0].user_id == reviewer_id


def test_reject_document_sets_status_and_records_comment() -> None:
    session = _FakeSession()
    document = _make_document(status=DocumentStatus.IN_REVIEW)
    reviewer_id = uuid.uuid4()

    result = reject_document(
        session,  # type: ignore[arg-type]
        document,
        user_id=reviewer_id,
        comment="Missing PO number",
    )

    assert result is document
    assert document.status == DocumentStatus.REJECTED
    audit_events = [obj for obj in session.added if isinstance(obj, AuditEvent)]
    assert len(audit_events) == 1
    assert audit_events[0].event_type == "rejected"
    assert audit_events[0].event_data["comment"] == "Missing PO number"
    assert audit_events[0].user_id == reviewer_id


def test_reject_document_requires_a_comment() -> None:
    session = _FakeSession()
    document = _make_document(status=DocumentStatus.IN_REVIEW)

    with pytest.raises(MissingRejectionCommentError):
        reject_document(session, document, user_id=uuid.uuid4(), comment="")  # type: ignore[arg-type]

    assert document.status == DocumentStatus.IN_REVIEW
    assert session.added == []


def test_reject_document_rejects_a_whitespace_only_comment() -> None:
    session = _FakeSession()
    document = _make_document(status=DocumentStatus.IN_REVIEW)

    with pytest.raises(MissingRejectionCommentError):
        reject_document(
            session,  # type: ignore[arg-type]
            document,
            user_id=uuid.uuid4(),
            comment="   ",
        )

    assert document.status == DocumentStatus.IN_REVIEW


@pytest.mark.parametrize("status", [s for s in DocumentStatus if s != DocumentStatus.IN_REVIEW])
def test_approve_document_rejects_every_non_in_review_status(status: DocumentStatus) -> None:
    session = _FakeSession()
    document = _make_document(status=status)

    with pytest.raises(InvalidTransitionError):
        approve_document(session, document, user_id=uuid.uuid4())  # type: ignore[arg-type]

    assert document.status == status
    assert session.added == []


@pytest.mark.parametrize("status", [s for s in DocumentStatus if s != DocumentStatus.IN_REVIEW])
def test_reject_document_rejects_every_non_in_review_status(status: DocumentStatus) -> None:
    session = _FakeSession()
    document = _make_document(status=status)

    with pytest.raises(InvalidTransitionError):
        reject_document(
            session,  # type: ignore[arg-type]
            document,
            user_id=uuid.uuid4(),
            comment="a real comment",
        )

    assert document.status == status
    assert session.added == []
