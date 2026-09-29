"""Integration tests for the document detail and field-correction
endpoints, against a real PostgreSQL database (docker compose up db,
then alembic upgrade head, before running these).
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app
from ascent.documents.models import (
    AuditEvent,
    Document,
    DocumentStatus,
    DocumentType,
    ExtractedField,
)
from ascent.shared.db import get_db
from ascent.shared.models import Tenant, User


@pytest.fixture
def tenant_and_reviewer(db_session: Session) -> tuple[Tenant, User]:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    reviewer = User(tenant_id=tenant.id, email="reviewer@acme.test", role="reviewer")
    db_session.add(reviewer)
    db_session.flush()
    return tenant, reviewer


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_document(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    status: DocumentStatus = DocumentStatus.IN_REVIEW,
) -> Document:
    document = Document(
        tenant_id=tenant_id,
        uploaded_by_user_id=user_id,
        original_filename="invoice.pdf",
        storage_key=f"{tenant_id}/{uuid.uuid4()}.pdf",
        document_type=DocumentType.INVOICE,
        status=status,
    )
    db_session.add(document)
    db_session.flush()
    return document


def _create_extracted_field(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    field_name: str = "total",
    extracted_value: str | None = "1080.0",
    confidence: float = 0.4,
) -> ExtractedField:
    field = ExtractedField(
        tenant_id=tenant_id,
        document_id=document_id,
        field_name=field_name,
        extracted_value=extracted_value,
        confidence=confidence,
    )
    db_session.add(field)
    db_session.flush()
    return field


def test_get_document_detail_returns_fields_with_confidence(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session,
        tenant_id=tenant.id,
        document_id=document.id,
        field_name="vendor_name",
        extracted_value="Acme Corp",
        confidence=0.95,
    )

    response = client.get(
        f"/api/v1/documents/{document.id}", headers={"X-User-Id": str(reviewer.id)}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(document.id)
    assert body["document_type"] == "invoice"
    assert len(body["fields"]) == 1
    assert body["fields"][0] == {
        "field_name": "vendor_name",
        "extracted_value": "Acme Corp",
        "confidence": 0.95,
        "corrected_value": None,
        "is_corrected": False,
    }


def test_get_document_detail_returns_404_for_unknown_document(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    _tenant, reviewer = tenant_and_reviewer

    response = client.get(
        f"/api/v1/documents/{uuid.uuid4()}", headers={"X-User-Id": str(reviewer.id)}
    )

    assert response.status_code == 404


def test_get_document_detail_does_not_leak_other_tenants_document(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer

    other_tenant = Tenant(name="Other Co")
    db_session.add(other_tenant)
    db_session.flush()
    other_user = User(tenant_id=other_tenant.id, email="other@co.test", role="reviewer")
    db_session.add(other_user)
    db_session.flush()
    other_document = _create_document(db_session, tenant_id=other_tenant.id, user_id=other_user.id)

    response = client.get(
        f"/api/v1/documents/{other_document.id}", headers={"X-User-Id": str(reviewer.id)}
    )

    # 404, never 403 -- doesn't confirm the document exists at all.
    assert response.status_code == 404


def test_get_document_detail_without_auth_is_rejected(client: TestClient) -> None:
    response = client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 401


def test_correct_field_sets_corrected_value_and_preserves_original(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session, tenant_id=tenant.id, document_id=document.id, extracted_value="1080.0"
    )

    response = client.patch(
        f"/api/v1/documents/{document.id}/fields/total",
        json={"corrected_value": "1200.00"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extracted_value"] == "1080.0"  # original, untouched
    assert body["corrected_value"] == "1200.00"
    assert body["is_corrected"] is True


def test_correct_field_writes_audit_event_with_old_and_new_value(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session, tenant_id=tenant.id, document_id=document.id, extracted_value="1080.0"
    )

    client.patch(
        f"/api/v1/documents/{document.id}/fields/total",
        json={"corrected_value": "1200.00"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.document_id == document.id, AuditEvent.event_type == "field_corrected")
        .all()
    )
    assert len(events) == 1
    assert events[0].event_data == {
        "field_name": "total",
        "old_value": "1080.0",
        "new_value": "1200.00",
    }
    assert events[0].user_id == reviewer.id


def test_correct_field_twice_uses_previous_correction_as_old_value(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session, tenant_id=tenant.id, document_id=document.id, extracted_value="1080.0"
    )

    client.patch(
        f"/api/v1/documents/{document.id}/fields/total",
        json={"corrected_value": "1200.00"},
        headers={"X-User-Id": str(reviewer.id)},
    )
    client.patch(
        f"/api/v1/documents/{document.id}/fields/total",
        json={"corrected_value": "1300.00"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    events = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.document_id == document.id, AuditEvent.event_type == "field_corrected")
        .all()
    )
    # AuditEvent.id is a random UUID, not a sequence, and both events
    # share the same created_at (Postgres's now() is fixed for the
    # whole transaction) -- there's no reliable "first"/"second" order
    # to sort by, so check both pairs showed up rather than indexing
    # into a sorted list.
    old_new_pairs = {(e.event_data["old_value"], e.event_data["new_value"]) for e in events}
    assert old_new_pairs == {("1080.0", "1200.00"), ("1200.00", "1300.00")}


def test_correct_field_rejects_when_document_not_in_review(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, status=DocumentStatus.APPROVED
    )
    _create_extracted_field(db_session, tenant_id=tenant.id, document_id=document.id)

    response = client.patch(
        f"/api/v1/documents/{document.id}/fields/total",
        json={"corrected_value": "1200.00"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    assert response.status_code == 409


def test_correct_field_returns_404_for_unknown_field(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = client.patch(
        f"/api/v1/documents/{document.id}/fields/nonexistent_field",
        json={"corrected_value": "x"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    assert response.status_code == 404


def test_correct_field_returns_404_for_unknown_document(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    _tenant, reviewer = tenant_and_reviewer

    response = client.patch(
        f"/api/v1/documents/{uuid.uuid4()}/fields/total",
        json={"corrected_value": "x"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    assert response.status_code == 404
