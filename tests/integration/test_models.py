"""Integration tests against a real PostgreSQL database (docker compose
up db, then alembic upgrade head, before running these) — external
services are mocked in unit tests, but the database itself is real
infrastructure per AI.md NFR5, not something worth faking here.

Each test runs inside a transaction that's rolled back afterward, so
tests don't leave rows behind or depend on run order.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ascent.shared.db import make_engine
from ascent.shared.models import Tenant, User


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


def test_create_tenant(db_session: Session) -> None:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.commit()

    assert tenant.id is not None
    assert tenant.created_at is not None


def test_user_belongs_to_tenant(db_session: Session) -> None:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    user = User(tenant_id=tenant.id, email="reviewer@acme.test", role="reviewer")
    db_session.add(user)
    db_session.commit()

    assert user.tenant_id == tenant.id
    assert user.tenant is tenant
    assert user in tenant.users


def test_duplicate_email_rejected(db_session: Session) -> None:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    db_session.add(User(tenant_id=tenant.id, email="dup@acme.test", role="reviewer"))
    db_session.commit()

    db_session.add(User(tenant_id=tenant.id, email="dup@acme.test", role="admin"))
    with pytest.raises(IntegrityError):
        db_session.commit()