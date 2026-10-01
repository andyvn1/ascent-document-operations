"""Integration tests for the review dashboard web UI (TASK-025),
against a real PostgreSQL database (docker compose up db, then
alembic upgrade head, before running these).
"""

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app
from ascent.documents.models import Document, DocumentStatus, DocumentType, ExtractedField
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


@pytest.fixture
def authenticated_client(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> TestClient:
    _tenant, reviewer = tenant_and_reviewer
    response = client.post("/login", data={"user_id": str(reviewer.id)}, follow_redirects=False)
    assert response.status_code == 303
    # TestClient persists cookies across requests on the same instance,
    # same as a real browser -- every subsequent call on `client` now
    # carries the user_id cookie automatically.
    return client


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
    confidence: float = 0.95,
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


def test_login_page_lists_users(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    _tenant, reviewer = tenant_and_reviewer

    response = client.get("/login")

    assert response.status_code == 200
    assert reviewer.email in response.text


def test_login_submit_sets_cookie_and_redirects(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    _tenant, reviewer = tenant_and_reviewer

    response = client.post("/login", data={"user_id": str(reviewer.id)}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/review"
    assert client.cookies.get("user_id") == str(reviewer.id)


def test_review_queue_without_cookie_redirects_to_login(client: TestClient) -> None:
    response = client.get("/review", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_review_queue_lists_documents_for_tenant(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = authenticated_client.get("/review")

    assert response.status_code == 200
    assert "invoice.pdf" in response.text


def test_review_detail_shows_document_and_fields(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
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

    response = authenticated_client.get(f"/review/{document.id}")

    assert response.status_code == 200
    assert "Acme Corp" in response.text
    assert "vendor_name" in response.text


def test_review_detail_highlights_low_confidence_field(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session,
        tenant_id=tenant.id,
        document_id=document.id,
        field_name="total",
        extracted_value="1080.0",
        confidence=0.4,
    )

    response = authenticated_client.get(f"/review/{document.id}")

    assert 'class="low-confidence"' in response.text


def test_review_detail_returns_404_for_unknown_document(authenticated_client: TestClient) -> None:
    response = authenticated_client.get(f"/review/{uuid.uuid4()}")

    assert response.status_code == 404


def test_review_detail_does_not_leak_other_tenants_document(
    authenticated_client: TestClient, db_session: Session
) -> None:
    other_tenant = Tenant(name="Other Co")
    db_session.add(other_tenant)
    db_session.flush()
    other_user = User(tenant_id=other_tenant.id, email="other@co.test", role="reviewer")
    db_session.add(other_user)
    db_session.flush()
    other_document = _create_document(db_session, tenant_id=other_tenant.id, user_id=other_user.id)

    response = authenticated_client.get(f"/review/{other_document.id}")

    assert response.status_code == 404


def test_review_correct_field_updates_value_and_returns_row_fragment(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)
    _create_extracted_field(
        db_session, tenant_id=tenant.id, document_id=document.id, extracted_value="1080.0"
    )

    response = authenticated_client.patch(
        f"/review/{document.id}/fields/total", data={"corrected_value": "1200.00"}
    )

    assert response.status_code == 200
    assert "1200.00" in response.text
    assert "was: 1080.0" in response.text
    assert 'id="field-row-total"' in response.text


def test_review_correct_field_rejects_when_document_not_in_review(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, status=DocumentStatus.APPROVED
    )
    _create_extracted_field(db_session, tenant_id=tenant.id, document_id=document.id)

    response = authenticated_client.patch(
        f"/review/{document.id}/fields/total", data={"corrected_value": "1200.00"}
    )

    assert response.status_code == 409
    assert "error" in response.text


def test_review_approve_transitions_status_and_redirects(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = authenticated_client.post(f"/review/{document.id}/approve", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/review"
    db_session.refresh(document)
    assert document.status == DocumentStatus.APPROVED


def test_review_approve_rejects_when_not_in_review(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(
        db_session, tenant_id=tenant.id, user_id=reviewer.id, status=DocumentStatus.UPLOADED
    )

    response = authenticated_client.post(f"/review/{document.id}/approve")

    assert response.status_code == 409
    db_session.refresh(document)
    assert document.status == DocumentStatus.UPLOADED


def test_review_reject_transitions_status_and_redirects(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = authenticated_client.post(
        f"/review/{document.id}/reject",
        data={"comment": "Missing PO number"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/review"
    db_session.refresh(document)
    assert document.status == DocumentStatus.REJECTED


def test_review_reject_requires_a_comment(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    # A blank comment still reaches the server (the HTML form's
    # `required` attribute is client-side only -- the same "never
    # trust client-side validation" rule workflow.py's own tests cover).
    response = authenticated_client.post(f"/review/{document.id}/reject", data={"comment": ""})

    assert response.status_code == 409
    db_session.refresh(document)
    assert document.status == DocumentStatus.IN_REVIEW
