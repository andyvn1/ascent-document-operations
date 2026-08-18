"""Invoice classification and extraction.

Classification runs before extraction (FR2) so the more expensive
structured-extraction call only happens once a document is known to be
an invoice -- extracting invoice fields from a change order or an
unrelated document blindly would populate invoice data with noise a
reviewer then has to notice and reject by hand, rather than the
pipeline never producing it in the first place.
"""

from pydantic import BaseModel

from ascent.ai.provider import AIProvider
from ascent.documents.models import DocumentType
from ascent.invoices.schema import REQUIRED_FIELDS, InvoiceData, strict_json_schema

_CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "document_type": {
            "type": "string",
            "enum": [member.value for member in DocumentType],
        }
    },
    "required": ["document_type"],
    "additionalProperties": False,
}

_CLASSIFICATION_SYSTEM_PROMPT = (
    "You classify business documents for a construction company. Read "
    "the document text and return its type: 'invoice' for vendor "
    "invoices and bills, 'change_order' for construction change "
    "orders, or 'unrecognized' for anything else (purchase orders, "
    "quotes, receipts, correspondence, etc.)."
)

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured data from construction-vendor invoices. "
    "Return only what is actually printed on the document -- if a "
    "field isn't present, leave it null rather than guessing or "
    "inventing a value."
)


class NotAnInvoiceError(ValueError):
    """Raised when extract_invoice is called on a document that
    classify_document did not identify as an invoice.
    """

    def __init__(self, document_type: DocumentType) -> None:
        self.document_type = document_type
        super().__init__(f"document classified as {document_type.value!r}, not invoice")


class InvoiceExtractionResult(BaseModel):
    data: InvoiceData
    missing_required_fields: list[str]


def classify_document(provider: AIProvider, document_text: str) -> DocumentType:
    result = provider.generate_structured_output(
        system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=document_text,
        output_schema=_CLASSIFICATION_SCHEMA,
    )
    return DocumentType(result["document_type"])


def extract_invoice(provider: AIProvider, document_text: str) -> InvoiceExtractionResult:
    document_type = classify_document(provider, document_text)
    if document_type != DocumentType.INVOICE:
        raise NotAnInvoiceError(document_type)

    raw = provider.generate_structured_output(
        system_prompt=_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=document_text,
        output_schema=strict_json_schema(InvoiceData),
    )
    data = InvoiceData.model_validate(raw)
    missing_required_fields = [field for field in REQUIRED_FIELDS if getattr(data, field) is None]
    return InvoiceExtractionResult(data=data, missing_required_fields=missing_required_fields)
