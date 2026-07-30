"""Shared fixtures for integration tests.

db_session's commit()/rollback() calls only affect an inner SAVEPOINT
(nested transaction), never the outer real transaction wrapping the
whole test -- that's what lets code under test (e.g. the worker's
retry/failure path, which calls session.rollback()) commit and roll
back as many times as it needs to, while the test itself still fully
rolls back and leaves no trace in the database afterward.

A naive "just connection.begin() once, never touch it again" fixture
works fine as long as code under test only ever calls session.commit()
-- but breaks the moment it calls session.rollback() too, since there's
no savepoint for that rollback to fall back to. See SQLAlchemy's
"Joining a Session into an External Transaction (such as for test
suites)" recipe, which this fixture implements.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session, sessionmaker

from ascent.shared.db import make_engine


@pytest.fixture(scope="module")
def engine() -> Generator[Engine, None, None]:
    engine = make_engine()
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    if outer_transaction.is_active:
        outer_transaction.rollback()
    connection.close()