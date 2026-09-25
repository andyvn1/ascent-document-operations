"""Document-type classification.

Shared by every document-type extraction module (invoices,
change orders, ...) so classification stays a single behavior instead
of each extraction module carrying its own copy of the prompt/schema.
Classification runs before extraction (FR2) so the more expensive
structured-extraction call only happens once a document is known to be
the type its extraction module handles -- extracting invoice fields
from a change order (or vice versa) would populate typed data with
noise a reviewer then has to notice and reject by hand, rather than
the pipeline never producing it in the first place.
"""

from ascent.ai.provider import AIProvider
from ascent.documents.models import DocumentType

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


def classify_document(provider: AIProvider, document_text: str) -> DocumentType:
    result = provider.generate_structured_output(
        system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=document_text,
        output_schema=_CLASSIFICATION_SCHEMA,
    )
    return DocumentType(result["document_type"])
