"""Integration tests for the review queue endpoint, against a real
PostgreSQL database (docker compose up db, then alembic upgrade head,
before running these).
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app
from ascent.documents.models import Document, DocumentStatus, DocumentType
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
    document_type: DocumentType = DocumentType.UNRECOGNIZED,
    status: DocumentStatus = DocumentStatus.UPLOADED,
    confidence: float | None = None,
) -> Document:
    document = Document(
        tenant_id=tenant_id,
        uploaded_by_user_id=user_id,
        original_filename="doc.pdf",
        storage_key=f"{tenant_id}/{uuid.uuid4()}.pdf",
        document_type=document_type,
        status=status,
        confidence=confidence,
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_review_queue_lists_documents_for_tenant(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = client.get("/api/v1/documents", headers={"X-User-Id": str(reviewer.id)})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_review_queue_filters_by_status(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, status=DocumentStatus.UPLOADED
    )
    in_review = _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, status=DocumentStatus.IN_REVIEW
    )

    response = client.get(
        "/api/v1/documents",
        params={"status": "in_review"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(in_review.id)


def test_review_queue_filters_by_document_type(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, document_type=DocumentType.INVOICE
    )
    _create_document(
        db_session,
        tenant_id=tenant.id,
        user_id=reviewer.id,
        document_type=DocumentType.CHANGE_ORDER,
    )

    response = client.get(
        "/api/v1/documents",
        params={"document_type": "change_order"},
        headers={"X-User-Id": str(reviewer.id)},
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["document_type"] == "change_order"


def test_review_queue_filters_by_confidence_range(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id, confidence=0.2)
    high_confidence = _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, confidence=0.9
    )

    response = client.get(
        "/api/v1/documents",
        params={"min_confidence": 0.5},
        headers={"X-User-Id": str(reviewer.id)},
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(high_confidence.id)


def test_review_queue_excludes_null_confidence_when_filtering(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id, confidence=None)

    response = client.get(
        "/api/v1/documents",
        params={"min_confidence": 0.0},
        headers={"X-User-Id": str(reviewer.id)},
    )

    # A document with no confidence score yet (extraction hasn't
    # populated it) shouldn't silently satisfy ">= 0.0" -- SQL's NULL
    # comparison semantics already exclude it; this pins that behavior.
    assert response.json()["total"] == 0


def test_review_queue_paginates_results(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer
    for _ in range(5):
        _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    first_page = client.get(
        "/api/v1/documents",
        params={"page": 1, "page_size": 2},
        headers={"X-User-Id": str(reviewer.id)},
    ).json()
    second_page = client.get(
        "/api/v1/documents",
        params={"page": 2, "page_size": 2},
        headers={"X-User-Id": str(reviewer.id)},
    ).json()

    assert first_page["total"] == 5
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 2
    first_page_ids = {item["id"] for item in first_page["items"]}
    second_page_ids = {item["id"] for item in second_page["items"]}
    assert first_page_ids.isdisjoint(second_page_ids)


def test_review_queue_does_not_leak_other_tenants_documents(
    client: TestClient, db_session: Session, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    tenant, reviewer = tenant_and_reviewer

    other_tenant = Tenant(name="Other Co")
    db_session.add(other_tenant)
    db_session.flush()
    other_user = User(tenant_id=other_tenant.id, email="other@co.test", role="reviewer")
    db_session.add(other_user)
    db_session.flush()
    _create_document(db_session, tenant_id=other_tenant.id, user_id=other_user.id)

    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = client.get("/api/v1/documents", headers={"X-User-Id": str(reviewer.id)})

    assert response.json()["total"] == 1


def test_review_queue_without_auth_header_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/documents")

    assert response.status_code == 401
