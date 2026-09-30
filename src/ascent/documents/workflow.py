"""Approval and rejection workflow (FR5, FR6, TASK-024).

Approval is the single most consequential action in this system. Per
the master plan, the product "must not automatically approve payments,
contracts, or legally significant decisions" -- once a document is
approved it becomes eligible for export (FR6), meaning whatever was
extracted (and possibly corrected) is now treated as authoritative
data leaving the review loop. That's why approve_document requires a
real user_id rather than the optional one transition_status allows
elsewhere: there is no way to call this function without naming the
human who approved. The gate is enforced by the function's signature,
not by a convention someone could forget to follow -- see this task's
first learning objective.

Both approve_document and reject_document reuse transition_status's
existing _ALLOWED_TRANSITIONS check (IN_REVIEW -> {APPROVED, REJECTED})
rather than re-checking "must be in review" here -- that rule already
exists in one place and already raises InvalidTransitionError
consistently for every kind of invalid transition in the system, not
just this one.
"""

import uuid

from sqlalchemy.orm import Session

from ascent.documents.models import Document, DocumentStatus
from ascent.documents.repository import transition_status


class MissingRejectionCommentError(ValueError):
    """FR6: rejecting a document always requires a reviewer comment --
    a workflow-specific rule transition_status has no reason to know
    about, so it's enforced here rather than there.
    """

    def __init__(self) -> None:
        super().__init__("a rejection comment is required")


def approve_document(session: Session, document: Document, *, user_id: uuid.UUID) -> Document:
    """The only function in this codebase allowed to set
    status=approved. Raises InvalidTransitionError (via
    transition_status) if document isn't currently in_review.
    """
    return transition_status(session, document, new_status=DocumentStatus.APPROVED, user_id=user_id)


def reject_document(
    session: Session, document: Document, *, user_id: uuid.UUID, comment: str
) -> Document:
    """Raises MissingRejectionCommentError if comment is blank, or
    InvalidTransitionError (via transition_status) if document isn't
    currently in_review.
    """
    if not comment.strip():
        raise MissingRejectionCommentError()

    return transition_status(
        session,
        document,
        new_status=DocumentStatus.REJECTED,
        user_id=user_id,
        event_data={"comment": comment},
    )
