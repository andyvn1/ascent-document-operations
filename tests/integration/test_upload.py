"""Integration tests for the document upload endpoint, against a real
PostgreSQL database and a temporary local storage directory (docker
compose up db, then alembic upgrade head, before running these).
"""

import shutil
import tempfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from apps.api.main import app
from apps.api.routes.documents import get_storage
from ascent.documents.storage import LocalFileStorage
from ascent.shared.db import get_db, make_engine
from ascent.shared.models import Tenant, User

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def engine() -> Generator[Engine, None, None]:
    engine = make_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def uploader(db_session: Session) -> User:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    user = User(tenant_id=tenant.id, email="uploader@acme.test", role="reviewer")
    db_session.add(user)
    db_session.flush()
    return user


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


def test_upload_pdf_succeeds(client: TestClient, uploader: User) -> None:
    with (FIXTURES / "sample-invoice.pdf").open("rb") as f:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("invoice.pdf", f, "application/pdf")},
            data={
                "tenant_id": str(uploader.tenant_id),
                "uploaded_by_user_id": str(uploader.id),
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"


def test_upload_image_succeeds(client: TestClient, uploader: User) -> None:
    with (FIXTURES / "sample-photo.png").open("rb") as f:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("photo.png", f, "image/png")},
            data={
                "tenant_id": str(uploader.tenant_id),
                "uploaded_by_user_id": str(uploader.id),
            },
        )

    assert response.status_code == 201


def test_upload_rejects_content_that_is_not_pdf_or_image(
    client: TestClient, uploader: User
) -> None:
    with (FIXTURES / "sample-not-a-document.txt").open("rb") as f:
        response = client.post(
            "/api/v1/documents",
            # Claims to be a PDF via filename/content-type — the endpoint
            # must catch this by sniffing actual content, not trust either.
            files={"file": ("fake.pdf", f, "application/pdf")},
            data={
                "tenant_id": str(uploader.tenant_id),
                "uploaded_by_user_id": str(uploader.id),
            },
        )

    assert response.status_code == 415


def test_upload_rejects_oversized_file(client: TestClient, uploader: User) -> None:
    oversized_content = _PDF_MAGIC_FOR_TEST + b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", BytesIO(oversized_content), "application/pdf")},
        data={
            "tenant_id": str(uploader.tenant_id),
            "uploaded_by_user_id": str(uploader.id),
        },
    )

    assert response.status_code == 413


_PDF_MAGIC_FOR_TEST = b"%PDF-"