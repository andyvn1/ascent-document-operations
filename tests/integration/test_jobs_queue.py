"""Integration tests for the Postgres-backed job queue itself (generic
mechanics: claim, complete, fail-with-backoff, SKIP LOCKED concurrency)
-- independent of any specific job handler. See test_worker.py for
tests using the real document-processing handler.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ascent.jobs.models import Job, JobStatus
from ascent.jobs.queue import claim_next_job, complete_job, enqueue, fail_job


def test_enqueue_creates_pending_job(db_session: Session) -> None:
    job = enqueue(db_session, job_type="noop", payload={"x": 1})
    db_session.commit()

    assert job.status == JobStatus.PENDING
    assert job.attempts == 0
    assert job.payload == {"x": 1}


def test_claim_marks_in_progress_and_increments_attempts(db_session: Session) -> None:
    enqueue(db_session, job_type="noop", payload={})
    db_session.commit()

    job = claim_next_job(db_session, job_types=["noop"])
    db_session.commit()

    assert job is not None
    assert job.status == JobStatus.IN_PROGRESS
    assert job.attempts == 1


def test_claim_ignores_jobs_not_yet_available(db_session: Session) -> None:
    job = enqueue(db_session, job_type="noop", payload={})
    job.available_at = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    assert claim_next_job(db_session, job_types=["noop"]) is None


def test_claim_returns_none_when_queue_empty(db_session: Session) -> None:
    assert claim_next_job(db_session, job_types=["noop"]) is None


def test_claim_filters_by_job_type(db_session: Session) -> None:
    enqueue(db_session, job_type="other_type", payload={})
    db_session.commit()

    assert claim_next_job(db_session, job_types=["noop"]) is None


def test_complete_job_marks_succeeded(db_session: Session) -> None:
    job = enqueue(db_session, job_type="noop", payload={})
    db_session.commit()
    claimed = claim_next_job(db_session, job_types=["noop"])
    assert claimed is not None

    complete_job(db_session, claimed)
    db_session.commit()

    refreshed = db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.SUCCEEDED


def test_fail_job_retries_with_backoff_before_exhausting_attempts(
    db_session: Session,
) -> None:
    job = enqueue(db_session, job_type="noop", payload={}, max_attempts=3)
    db_session.commit()
    claimed = claim_next_job(db_session, job_types=["noop"])
    assert claimed is not None
    assert claimed.attempts == 1

    before = datetime.now(UTC)
    fail_job(db_session, claimed, error="boom")
    db_session.commit()

    refreshed = db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.PENDING
    assert refreshed.last_error == "boom"
    assert refreshed.available_at.replace(tzinfo=UTC) > before


def test_fail_job_marks_failed_after_max_attempts(db_session: Session) -> None:
    job = enqueue(db_session, job_type="noop", payload={}, max_attempts=1)
    db_session.commit()
    claimed = claim_next_job(db_session, job_types=["noop"])
    assert claimed is not None
    assert claimed.attempts == 1

    fail_job(db_session, claimed, error="permanent failure")
    db_session.commit()

    refreshed = db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.FAILED


def test_skip_locked_prevents_double_claiming(engine: Engine) -> None:
    """Proves the whole point of FOR UPDATE SKIP LOCKED: two separate
    connections polling concurrently never claim the same job.
    """
    connection_a = engine.connect()
    connection_a.begin()
    session_a = sessionmaker(bind=connection_a)()

    connection_b = engine.connect()
    transaction_b = connection_b.begin()
    session_b = sessionmaker(bind=connection_b)()

    try:
        job = enqueue(session_a, job_type="noop", payload={})
        session_a.commit()
        # The connection auto-begins a fresh transaction on the next
        # statement (claim_next_job below) -- no need to call
        # connection_a.begin() again ourselves.

        claimed_by_a = claim_next_job(session_a, job_types=["noop"])
        assert claimed_by_a is not None
        assert claimed_by_a.id == job.id

        # Session B's query skips the row A is holding a lock on,
        # rather than blocking or claiming it too.
        claimed_by_b = claim_next_job(session_b, job_types=["noop"])
        assert claimed_by_b is None
    finally:
        session_a.close()
        connection_a.close()

        session_b.close()
        if transaction_b.is_active:
            transaction_b.rollback()
        connection_b.close()
