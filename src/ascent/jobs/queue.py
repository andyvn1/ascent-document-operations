"""Postgres-backed job queue.

claim_next_job uses SELECT ... FOR UPDATE SKIP LOCKED so multiple
worker processes can poll the same table concurrently without ever
claiming the same job twice — Postgres itself provides the mutual
exclusion here, no separate locking service needed.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ascent.jobs.models import Job, JobStatus

_BASE_BACKOFF_SECONDS = 2
_MAX_BACKOFF_SECONDS = 300


def enqueue(
    session: Session,
    *,
    job_type: str,
    payload: dict[str, Any],
    max_attempts: int = 5,
) -> Job:
    job = Job(job_type=job_type, payload=payload, max_attempts=max_attempts)
    session.add(job)
    session.flush()
    return job


def claim_next_job(session: Session, *, job_types: list[str] | None = None) -> Job | None:
    """Atomically claim the oldest available pending job, if any.

    FOR UPDATE SKIP LOCKED means a concurrent caller running this same
    query never blocks on, or claims, a row another worker already has
    locked — it just skips to the next available one.
    """
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.PENDING)
        .where(Job.available_at <= func.now())
        .order_by(Job.available_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job_types is not None:
        stmt = stmt.where(Job.job_type.in_(job_types))

    job = session.execute(stmt).scalar_one_or_none()
    if job is None:
        return None

    job.status = JobStatus.IN_PROGRESS
    job.attempts += 1
    session.flush()
    return job


def complete_job(session: Session, job: Job) -> None:
    job.status = JobStatus.SUCCEEDED
    session.flush()


def fail_job(session: Session, job: Job, *, error: str) -> None:
    job.last_error = error[:2000]
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.FAILED
    else:
        job.status = JobStatus.PENDING
        job.available_at = datetime.now(UTC) + timedelta(
            seconds=min(_BASE_BACKOFF_SECONDS**job.attempts, _MAX_BACKOFF_SECONDS)
        )
    session.flush()