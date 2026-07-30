"""Background worker: polls the jobs table and dispatches to handlers.

Run locally with: uv run python -m apps.worker.main

Claiming a job and running its handler are deliberately two separate
transactions: the claim (status -> in_progress, attempts += 1) commits
immediately, so that fact survives even if the handler's own
transaction later gets rolled back on failure. Each handler invocation
is otherwise atomic -- either all of its work commits, or none of it
does; retries simply re-run the whole (idempotent) handler rather than
trying to resume from a partial state.
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from ascent.documents.processing import process_document_job
from ascent.jobs.models import Job
from ascent.jobs.queue import claim_next_job, complete_job, fail_job
from ascent.shared import model_registry  # noqa: F401
from ascent.shared.config import get_settings
from ascent.shared.db import SessionLocal
from ascent.shared.logging import configure_logging

logger = logging.getLogger(__name__)

JOB_HANDLERS: dict[str, Callable[[Session, Job], None]] = {
    "process_document": process_document_job,
}

_POLL_INTERVAL_SECONDS = 2.0


def run_once(
    session: Session,
    handlers: dict[str, Callable[[Session, Job], None]] | None = None,
) -> bool:
    """Claim and process a single job, if one is available.

    Returns True if a job was claimed (regardless of success or
    failure), False if the queue was empty -- lets the caller decide
    whether to sleep before polling again.

    `handlers` defaults to the real JOB_HANDLERS registry; tests pass a
    substitute dict (e.g. a deliberately flaky handler) to exercise the
    retry/backoff/failure paths without needing the real document
    handler to actually fail.
    """
    handlers = handlers if handlers is not None else JOB_HANDLERS
    job = claim_next_job(session, job_types=list(handlers))
    if job is None:
        session.commit()
        return False
    session.commit()

    job_id = job.id
    handler = handlers[job.job_type]
    try:
        handler(session, job)
    except Exception as exc:  # noqa: BLE001 - any handler failure should retry, never crash the worker
        session.rollback()
        job = session.get(Job, job_id)
        if job is None:
            logger.error("job %s vanished after failure", job_id)
            return True
        fail_job(session, job, error=str(exc))
        session.commit()
        logger.warning("job %s (%s) failed: %s", job.id, job.job_type, exc)
        return True

    complete_job(session, job)
    session.commit()
    logger.info("job %s (%s) succeeded", job.id, job.job_type)
    return True


def run_forever() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger.info("Worker started, polling for job types: %s", list(JOB_HANDLERS))
    while True:
        session = SessionLocal()
        try:
            claimed = run_once(session)
        finally:
            session.close()
        if not claimed:
            time.sleep(_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()