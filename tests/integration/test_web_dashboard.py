"""Integration tests for the review dashboard web UI (TASK-025),
against a real PostgreSQL database (docker compose up db, then
alembic upgrade head, before running these).
"""

import shutil
import tempfile
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.main import app
from apps.api.routes.documents import get_storage
from ascent.documents.models import Document, DocumentStatus, DocumentType, ExtractedField
from ascent.documents.storage import LocalFileStorage
from ascent.shared.db import get_db
from ascent.shared.models import Tenant, User

FIXTURES = Path(__file__).parent.parent / "fixtures"


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
    tmp_dir = tempfile.mkdtemp()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_storage() -> LocalFileStorage:
        return LocalFileStorage(tmp_dir)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = override_get_storage
    yield TestClient(app)
    app.dependency_overrides.clear()
    shutil.rmtree(tmp_dir, ignore_errors=True)


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


def test_signup_page_renders(client: TestClient) -> None:
    response = client.get("/signup")

    assert response.status_code == 200
    assert "Sign up" in response.text


def test_signup_creates_tenant_and_user_and_logs_in(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/signup",
        data={"email": "new-reviewer@newco.test", "company_name": "New Co"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/review"

    user = db_session.scalar(select(User).where(User.email == "new-reviewer@newco.test"))
    assert user is not None
    assert client.cookies.get("user_id") == str(user.id)

    tenant = db_session.get(Tenant, user.tenant_id)
    assert tenant is not None
    assert tenant.name == "New Co"


def test_signup_rejects_an_already_registered_email(
    client: TestClient, tenant_and_reviewer: tuple[Tenant, User]
) -> None:
    _tenant, reviewer = tenant_and_reviewer

    response = client.post(
        "/signup",
        # Different case on purpose -- the check is case-insensitive.
        data={"email": reviewer.email.upper(), "company_name": "Another Co"},
    )

    assert response.status_code == 409
    assert "already registered" in response.text


def test_signup_allows_two_tenants_with_the_same_company_name(
    client: TestClient, db_session: Session
) -> None:
    # Tenant.name has nothing keyed off it for identity or security --
    # only the email has to be unique -- so two signups choosing the
    # same company name must both succeed as two separate tenants.
    first = client.post(
        "/signup",
        data={"email": "first@shared-name.test", "company_name": "Shared Name Inc"},
        follow_redirects=False,
    )
    assert first.status_code == 303

    second = client.post(
        "/signup",
        data={"email": "second@shared-name.test", "company_name": "Shared Name Inc"},
        follow_redirects=False,
    )
    assert second.status_code == 303

    tenants = db_session.query(Tenant).filter(Tenant.name == "Shared Name Inc").all()
    assert len(tenants) == 2
    assert tenants[0].id != tenants[1].id


def test_signup_requires_both_fields(client: TestClient) -> None:
    response = client.post("/signup", data={"email": "only-email@x.test", "company_name": ""})

    assert response.status_code == 422


def test_upload_form_requires_auth(client: TestClient) -> None:
    response = client.get("/upload", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_upload_pdf_creates_document_and_redirects_to_detail(
    authenticated_client: TestClient, db_session: Session
) -> None:
    with (FIXTURES / "sample-invoice.pdf").open("rb") as f:
        response = authenticated_client.post(
            "/upload",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            follow_redirects=False,
        )

    assert response.status_code == 303
    document_id = response.headers["location"].removeprefix("/review/")
    document = db_session.get(Document, uuid.UUID(document_id))
    assert document is not None
    assert document.original_filename == "invoice.pdf"
    assert document.status == DocumentStatus.UPLOADED


def test_upload_rejects_content_that_is_not_pdf_or_image(
    authenticated_client: TestClient,
) -> None:
    with (FIXTURES / "sample-not-a-document.txt").open("rb") as f:
        response = authenticated_client.post(
            "/upload",
            # Claims to be a PDF via filename/content-type -- the route
            # must catch this by sniffing actual content, not trust
            # either (same rule as the JSON upload endpoint).
            files={"file": ("fake.pdf", f, "application/pdf")},
        )

    assert response.status_code == 415
    assert "error" in response.text


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


def test_review_detail_preview_points_at_cookie_authenticated_file_route(
    authenticated_client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    # Regression test: the preview <iframe> must point at this cookie-
    # authenticated route, not at the JSON API's header-authenticated
    # /api/v1/documents/{id}/file -- an <iframe> is a browser sub-resource
    # load like a link click, so it sends cookies automatically but can
    # never attach the X-User-Id header the JSON API requires.
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = authenticated_client.get(f"/review/{document.id}")

    assert response.status_code == 200
    assert f'src="/review/{document.id}/file"' in response.text
    assert f"/api/v1/documents/{document.id}/file" not in response.text


def test_review_document_file_serves_uploaded_content_with_cookie_auth(
    authenticated_client: TestClient,
) -> None:
    with (FIXTURES / "sample-invoice.pdf").open("rb") as f:
        content = f.read()
        f.seek(0)
        upload_response = authenticated_client.post(
            "/upload",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            follow_redirects=False,
        )
    document_id = upload_response.headers["location"].removeprefix("/review/")

    response = authenticated_client.get(f"/review/{document_id}/file")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"] == "application/pdf"


def test_review_document_file_without_cookie_redirects_to_login(
    client: TestClient,
    db_session: Session,
    tenant_and_reviewer: tuple[Tenant, User],
) -> None:
    tenant, reviewer = tenant_and_reviewer
    document = _create_document(db_session, tenant_id=tenant.id, user_id=reviewer.id)

    response = client.get(f"/review/{document.id}/file", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_review_document_file_does_not_leak_other_tenants_document(
    authenticated_client: TestClient, db_session: Session
) -> None:
    other_tenant = Tenant(name="Other Co")
    db_session.add(other_tenant)
    db_session.flush()
    other_user = User(tenant_id=other_tenant.id, email="other-file@co.test", role="reviewer")
    db_session.add(other_user)
    db_session.flush()
    other_document = _create_document(db_session, tenant_id=other_tenant.id, user_id=other_user.id)

    response = authenticated_client.get(f"/review/{other_document.id}/file")

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
