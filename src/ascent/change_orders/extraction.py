"""Change-order classification and extraction.

Change-order validation differs from invoice validation in one
important way: an invoice missing a required field is always a defect
(the field is on the document; extraction just didn't find it), but a
change order missing an approver can be entirely correct -- a change
order is often submitted *before* anyone has approved it, and that's a
normal point in its lifecycle, not an extraction failure. Treating a
missing approver the same as any other missing field would either bury
a genuinely important signal in a list of minor omissions, or train
reviewers to ignore that list. So `requires_approval_review` is its own
field, separate from `missing_required_fields`: not because the data
is missing, but because the master plan requires that nothing tied to
a change order (cost, schedule, contract terms) is treated as
authoritative -- let alone auto-processed -- without a recorded
approver. Downstream workflow must treat `requires_approval_review`
as a hard block, not a suggestion.
"""

from datetime import date

from pydantic import BaseModel

from ascent.ai.provider import AIProvider
from ascent.ai.schema import strict_json_schema
from ascent.change_orders.schema import REQUIRED_FIELDS, ChangeOrderData
from ascent.documents.classification import classify_document
from ascent.documents.models import DocumentType

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured data from construction change-order "
    "documents. Return only what is actually printed on the document "
    "-- if a field isn't present, leave it null rather than guessing "
    "or inventing a value. Dates may be printed in any format (e.g. "
    "'03/11/2026', 'March 11, 2026', '2026-03-11') -- always convert "
    "them to ISO 8601 (YYYY-MM-DD) in your output, regardless of the "
    "format printed on the document."
)


class NotAChangeOrderError(ValueError):
    """Raised when extract_change_order is called on a document that
    classify_document did not identify as a change order.
    """

    def __init__(self, document_type: DocumentType) -> None:
        self.document_type = document_type
        super().__init__(f"document classified as {document_type.value!r}, not change_order")


class ChangeOrderExtractionResult(BaseModel):
    data: ChangeOrderData
    missing_required_fields: list[str]
    # True whenever no approver was found. Not folded into
    # missing_required_fields -- see this module's docstring -- and
    # must block auto-processing downstream regardless of how complete
    # everything else is.
    requires_approval_review: bool
    validation_issues: list[str]


def extract_change_order(
    provider: AIProvider,
    document_text: str,
    *,
    as_of: date | None = None,
) -> ChangeOrderExtractionResult:
    """as_of is the reference date for flagging a future-dated request;
    defaults to today. Exposed as a parameter (rather than always using
    date.today() internally) so callers -- tests included -- can pin it
    instead of the result depending on wall-clock time.
    """
    document_type = classify_document(provider, document_text)
    if document_type != DocumentType.CHANGE_ORDER:
        raise NotAChangeOrderError(document_type)

    raw = provider.generate_structured_output(
        system_prompt=_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=document_text,
        output_schema=strict_json_schema(ChangeOrderData),
    )
    data = ChangeOrderData.model_validate(raw)

    missing_required_fields = [field for field in REQUIRED_FIELDS if getattr(data, field) is None]
    validation_issues = _validation_issues(data, as_of=as_of or date.today())

    return ChangeOrderExtractionResult(
        data=data,
        missing_required_fields=missing_required_fields,
        requires_approval_review=data.approver is None,
        validation_issues=validation_issues,
    )


def _validation_issues(data: ChangeOrderData, *, as_of: date) -> list[str]:
    issues: list[str] = []

    if data.requested_amount is not None and data.requested_amount <= 0:
        issues.append("requested_amount must be a positive amount")

    if data.request_date is not None and data.request_date > as_of:
        issues.append("request_date is in the future")

    return issues
