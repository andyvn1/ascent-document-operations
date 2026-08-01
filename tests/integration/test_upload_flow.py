"""Full upload-flow integration tests: unlike test_upload.py (which
checks the HTTP response for each validation rule in isolation), these
verify that a single successful upload produces all three side effects
together -- a Document row, a retrievable file in storage, and an
enqueued processing Job -- and that a rejected (unauthenticated)
request produces none of them.
"""

import shutil
import tempfile
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app
from apps.api.routes.documents import get_storage
from ascent.documents.models import Document, DocumentStatus
from ascent.documents.storage import LocalFileStorage
from ascent.jobs.models import Job, JobStatus
from ascent.shared.db import get_db
from ascent.shared.models import Tenant, User

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def uploader(db_session: Session) -> User:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    user = User(tenant_id=tenant.id, email="flow-test@acme.test", role="reviewer")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def storage_dir() -> Generator[str, None, None]:
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def client(db_session: Session, storage_dir: str) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def override_get_storage() -> LocalFileStorage:
        return LocalFileStorage(storage_dir)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = override_get_storage

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_successful_upload_creates_document_stores_file_and_enqueues_job(
    client: TestClient, db_session: Session, storage_dir: str, uploader: User
) -> None:
    content = (FIXTURES / "sample-invoice.pdf").read_bytes()
    response = client.post(
        "/api/v1/documents",
        files={"file": ("invoice.pdf", content, "application/pdf")},
        headers={"X-User-Id": str(uploader.id)},
    )
    assert response.status_code == 201
    document_id = uuid.UUID(response.json()["id"])

    document = db_session.get(Document, document_id)
    assert document is not None
    assert document.tenant_id == uploader.tenant_id
    assert document.uploaded_by_user_id == uploader.id
    assert document.status == DocumentStatus.UPLOADED

    stored_content = LocalFileStorage(storage_dir).retrieve(key=document.storage_key)
    assert stored_content == content

    job = (
        db_session.query(Job)
        .filter(Job.job_type == "process_document")
        .filter(Job.payload["document_id"].astext == str(document.id))
        .one()
    )
    assert job.status == JobStatus.PENDING


def test_upload_without_auth_creates_no_document_or_job(
    client: TestClient, db_session: Session
) -> None:
    content = (FIXTURES / "sample-invoice.pdf").read_bytes()
    response = client.post(
        "/api/v1/documents",
        files={"file": ("invoice.pdf", content, "application/pdf")},
    )

    assert response.status_code == 401
    assert db_session.query(Document).count() == 0
    assert db_session.query(Job).count() == 0