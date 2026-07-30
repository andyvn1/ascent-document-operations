"""Document processing job handler.

This is a placeholder for real classification/extraction, which doesn't
exist yet (TASK-016+, the AI provider system). For now it just advances
a document through uploaded -> processing -> extracted, so the queue
mechanics (TASK-014) have real work to do and TASK-016+ has a slot to
plug real logic into later.

Idempotent by construction: each step only runs if the document is
still at the status that step expects. Re-running this handler on a
document that already reached "extracted" (e.g. a retried job after a
transient failure) does nothing on either branch — safe to call as
many times as the queue decides to.
"""

import uuid

from sqlalchemy.orm import Session

from ascent.documents.models import Document, DocumentStatus
from ascent.documents.repository import transition_status
from ascent.jobs.models import Job


class DocumentNotFoundError(ValueError):
    def __init__(self, document_id: uuid.UUID) -> None:
        self.document_id = document_id
        super().__init__(f"document not found: {document_id}")


def process_document_job(session: Session, job: Job) -> None:
    document_id = uuid.UUID(job.payload["document_id"])
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)

    if document.status == DocumentStatus.UPLOADED:
        transition_status(session, document, new_status=DocumentStatus.PROCESSING)

    if document.status == DocumentStatus.PROCESSING:
        # Placeholder for real classification/extraction (TASK-016+).
        transition_status(session, document, new_status=DocumentStatus.EXTRACTED)