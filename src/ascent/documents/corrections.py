"""Field correction workflow (FR5-FR7, TASK-023).

A correction never overwrites extracted_value -- it only ever sets
corrected_value and flips is_corrected. This is what "why must the
original AI output be preserved" (this task's first learning
objective) means concretely: a reviewer's fix and the model's original
answer both stay on the same row forever, so anyone auditing extraction
quality later can compare what the AI actually said against what a
human decided was right, rather than the correction silently replacing
the evidence that a correction was ever needed.

Only allowed while the document is in_review, matching the endpoint
design already sketched in api-specification.md -- correcting a field
on a document that's already been approved or exported would let data
change after the point FR6 says nothing else may act on it.
"""

import uuid

from sqlalchemy.orm import Session

from ascent.documents.models import DocumentStatus, ExtractedField
from ascent.documents.repository import (
    DocumentNotFoundError,
    get_document,
    get_extracted_field,
    record_event,
)


class FieldNotFoundError(ValueError):
    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        super().__init__(f"field not found: {field_name!r}")


class DocumentNotInReviewError(ValueError):
    def __init__(self, status: DocumentStatus) -> None:
        self.status = status
        super().__init__(f"document is not in review (status={status.value!r})")


def correct_field(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    field_name: str,
    corrected_value: str,
    user_id: uuid.UUID,
) -> ExtractedField:
    document = get_document(session, tenant_id=tenant_id, document_id=document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    if document.status != DocumentStatus.IN_REVIEW:
        raise DocumentNotInReviewError(document.status)

    field = get_extracted_field(
        session, tenant_id=tenant_id, document_id=document_id, field_name=field_name
    )
    if field is None:
        raise FieldNotFoundError(field_name)

    # A field can be corrected more than once -- the audit event should
    # show what changed *this time*, so the "old" value is whatever was
    # showing a moment ago (a prior correction if there was one),
    # not always the original AI output.
    old_value = field.corrected_value if field.is_corrected else field.extracted_value
    field.corrected_value = corrected_value
    field.is_corrected = True
    session.flush()

    record_event(
        session,
        document=document,
        event_type="field_corrected",
        user_id=user_id,
        event_data={
            "field_name": field_name,
            "old_value": old_value,
            "new_value": corrected_value,
        },
    )
    return field
