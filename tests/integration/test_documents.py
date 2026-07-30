"""Integration tests against a real PostgreSQL database (docker compose
up db, then alembic upgrade head, before running these).

Each test runs inside a transaction that's rolled back afterward, so
tests don't leave rows behind or depend on run order.
"""

import pytest
from sqlalchemy.orm import Session

from ascent.documents.models import DocumentStatus
from ascent.documents.repository import (
    InvalidTransitionError,
    create_document,
    list_audit_events,
    transition_status,
)
from ascent.shared.models import Tenant, User


@pytest.fixture
def uploader(db_session: Session) -> User:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    user = User(tenant_id=tenant.id, email="uploader@acme.test", role="reviewer")
    db_session.add(user)
    db_session.flush()
    return user


def test_create_document_starts_uploaded_with_audit_event(
    db_session: Session, uploader: User
) -> None:
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="invoice.pdf",
        storage_key="documents/invoice.pdf",
    )
    db_session.commit()

    assert document.status == DocumentStatus.UPLOADED
    assert document.tenant_id == uploader.tenant_id

    events = list_audit_events(db_session, document.id)
    assert len(events) == 1
    assert events[0].event_type == "uploaded"
    assert events[0].tenant_id == uploader.tenant_id
    assert events[0].event_data["original_filename"] == "invoice.pdf"


def test_valid_transition_updates_status_and_records_event(
    db_session: Session, uploader: User
) -> None:
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="invoice.pdf",
        storage_key="documents/invoice.pdf",
    )
    db_session.commit()

    transition_status(db_session, document, new_status=DocumentStatus.PROCESSING)
    db_session.commit()

    assert document.status == DocumentStatus.PROCESSING

    events = list_audit_events(db_session, document.id)
    assert [e.event_type for e in events] == ["uploaded", "processing"]
    assert events[1].event_data == {"from": "uploaded", "to": "processing"}


def test_invalid_transition_is_rejected_and_leaves_no_new_event(
    db_session: Session, uploader: User
) -> None:
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="invoice.pdf",
        storage_key="documents/invoice.pdf",
    )
    db_session.commit()

    with pytest.raises(InvalidTransitionError):
        transition_status(db_session, document, new_status=DocumentStatus.APPROVED)

    assert document.status == DocumentStatus.UPLOADED
    events = list_audit_events(db_session, document.id)
    assert len(events) == 1


def test_terminal_statuses_allow_no_further_transitions(
    db_session: Session, uploader: User
) -> None:
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="co.pdf",
        storage_key="documents/co.pdf",
    )
    transition_status(db_session, document, new_status=DocumentStatus.PROCESSING)
    transition_status(db_session, document, new_status=DocumentStatus.EXTRACTED)
    transition_status(db_session, document, new_status=DocumentStatus.IN_REVIEW)
    transition_status(db_session, document, new_status=DocumentStatus.REJECTED)
    db_session.commit()

    with pytest.raises(InvalidTransitionError):
        transition_status(db_session, document, new_status=DocumentStatus.PROCESSING)