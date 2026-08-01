"""Integration tests for the worker loop (apps/worker/main.py), covering
both the real document-processing handler end-to-end and the generic
retry/backoff/failure path using a controllable fake handler.
"""

import pytest
from sqlalchemy.orm import Session

from apps.worker.main import run_once
from ascent.documents.models import Document, DocumentStatus
from ascent.documents.processing import process_document_job
from ascent.documents.repository import create_document, list_audit_events
from ascent.jobs.models import Job, JobStatus
from ascent.jobs.queue import enqueue
from ascent.shared.models import Tenant, User


@pytest.fixture
def uploader(db_session: Session) -> User:
    tenant = Tenant(name="Acme Construction")
    db_session.add(tenant)
    db_session.flush()

    user = User(tenant_id=tenant.id, email="worker-test@acme.test", role="reviewer")
    db_session.add(user)
    db_session.flush()
    return user


def test_run_once_advances_document_through_processing_to_extracted(
    db_session: Session, uploader: User
) -> None:
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="invoice.pdf",
        storage_key="documents/invoice.pdf",
    )
    job = enqueue(
        db_session, job_type="process_document", payload={"document_id": str(document.id)}
    )
    db_session.commit()

    claimed = run_once(db_session, handlers={"process_document": process_document_job})

    assert claimed is True
    refreshed_document = db_session.get(Document, document.id)
    assert refreshed_document is not None
    assert refreshed_document.status == DocumentStatus.EXTRACTED

    refreshed_job = db_session.get(Job, job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == JobStatus.SUCCEEDED

    events = list_audit_events(db_session, tenant_id=document.tenant_id, document_id=document.id)
    assert [e.event_type for e in events] == ["uploaded", "processing", "extracted"]


def test_reprocessing_an_already_extracted_document_is_a_no_op(
    db_session: Session, uploader: User
) -> None:
    """Idempotency: re-running the handler directly on a document
    that's already reached its final state for this handler must not
    raise, and must not add duplicate audit events.
    """
    document = create_document(
        db_session,
        tenant_id=uploader.tenant_id,
        uploaded_by_user_id=uploader.id,
        original_filename="invoice.pdf",
        storage_key="documents/invoice.pdf",
    )
    job = enqueue(
        db_session, job_type="process_document", payload={"document_id": str(document.id)}
    )
    db_session.commit()

    process_document_job(db_session, job)
    db_session.commit()
    events_after_first_run = list_audit_events(
        db_session, tenant_id=document.tenant_id, document_id=document.id
    )

    # Call the handler again directly -- simulates a job being
    # redelivered/retried after it already succeeded.
    process_document_job(db_session, job)
    db_session.commit()
    events_after_second_run = list_audit_events(
        db_session, tenant_id=document.tenant_id, document_id=document.id
    )

    assert len(events_after_first_run) == 3
    assert events_after_second_run == events_after_first_run


def test_run_once_retries_on_failure_then_succeeds(db_session: Session) -> None:
    attempts_seen: list[int] = []

    def flaky_handler(session: Session, job: Job) -> None:
        attempts_seen.append(job.attempts)
        if job.attempts < 2:
            raise RuntimeError("simulated transient failure")

    enqueue(db_session, job_type="flaky", payload={}, max_attempts=5)
    db_session.commit()

    # First attempt fails and schedules a retry (with a future
    # available_at), so it won't be claimed again immediately.
    claimed_first = run_once(db_session, handlers={"flaky": flaky_handler})
    assert claimed_first is True
    assert run_once(db_session, handlers={"flaky": flaky_handler}) is False

    job = db_session.query(Job).filter(Job.job_type == "flaky").one()
    assert job.status == JobStatus.PENDING
    assert job.last_error == "simulated transient failure"

    # Force it available now instead of waiting out the real backoff.
    job.available_at = job.created_at
    db_session.commit()

    claimed_second = run_once(db_session, handlers={"flaky": flaky_handler})
    assert claimed_second is True

    refreshed = db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.SUCCEEDED
    assert attempts_seen == [1, 2]


def test_run_once_marks_job_failed_after_exhausting_attempts(db_session: Session) -> None:
    def always_fails(session: Session, job: Job) -> None:
        raise RuntimeError("permanent failure")

    job = enqueue(db_session, job_type="doomed", payload={}, max_attempts=1)
    db_session.commit()

    claimed = run_once(db_session, handlers={"doomed": always_fails})
    assert claimed is True

    refreshed = db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.FAILED
    assert refreshed.last_error == "permanent failure"