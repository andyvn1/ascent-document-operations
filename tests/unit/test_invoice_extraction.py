from typing import Any

import pytest

from ascent.ai.provider import AIProvider
from ascent.ai.providers.mock import MockProvider
from ascent.documents.models import DocumentType
from ascent.invoices.extraction import (
    NotAnInvoiceError,
    classify_document,
    extract_invoice,
)
from ascent.invoices.schema import InvoiceData, strict_json_schema

_FULL_INVOICE = {
    "vendor_name": "Acme Construction Supply",
    "invoice_number": "INV-1001",
    "invoice_date": "2026-07-01",
    "due_date": "2026-07-31",
    "project_name": "Riverside Office Build",
    "customer_name": "Ascent GC",
    "po_number": "PO-42",
    "subtotal": 1000.0,
    "tax": 80.0,
    "total": 1080.0,
    "currency": "USD",
    "payment_terms": "Net 30",
    "line_items": [
        {
            "description": "Concrete mix",
            "quantity": 10.0,
            "unit_price": 100.0,
            "cost_code": "03-300",
        }
    ],
}


class _QueuedProvider:
    """Returns queued responses in order -- one per
    generate_structured_output call. classify_document and
    extract_invoice each need a distinct response shape, which
    MockProvider (a single fixed response regardless of call) can't
    represent, so tests here use this instead.
    """

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        return self._responses.pop(0)

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def create_embeddings(self, *, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


def test_queued_provider_satisfies_ai_provider_protocol() -> None:
    provider: AIProvider = _QueuedProvider([])
    assert provider is not None


def test_classify_document_returns_parsed_document_type() -> None:
    provider = _QueuedProvider([{"document_type": "invoice"}])

    result = classify_document(provider, "some document text")

    assert result == DocumentType.INVOICE


def test_extract_invoice_raises_when_not_classified_as_invoice() -> None:
    provider = _QueuedProvider([{"document_type": "change_order"}])

    with pytest.raises(NotAnInvoiceError) as exc_info:
        extract_invoice(provider, "some document text")

    assert exc_info.value.document_type == DocumentType.CHANGE_ORDER


def test_extract_invoice_does_not_call_extraction_when_not_invoice() -> None:
    # Only one response queued -- if extract_invoice made a second
    # generate_structured_output call after classification rejected
    # the document, popping from the empty list would raise IndexError.
    provider = _QueuedProvider([{"document_type": "unrecognized"}])

    with pytest.raises(NotAnInvoiceError):
        extract_invoice(provider, "some document text")


def test_extract_invoice_returns_parsed_data_with_no_missing_fields() -> None:
    provider = _QueuedProvider([{"document_type": "invoice"}, dict(_FULL_INVOICE)])

    result = extract_invoice(provider, "some document text")

    assert result.data.vendor_name == "Acme Construction Supply"
    assert result.data.total == 1080.0
    assert len(result.data.line_items) == 1
    assert result.data.line_items[0].cost_code == "03-300"
    assert result.missing_required_fields == []


def test_extract_invoice_flags_missing_required_fields_instead_of_defaulting() -> None:
    incomplete = dict(_FULL_INVOICE)
    incomplete["total"] = None
    incomplete["invoice_number"] = None
    provider = _QueuedProvider([{"document_type": "invoice"}, incomplete])

    result = extract_invoice(provider, "some document text")

    assert result.data.total is None
    assert set(result.missing_required_fields) == {"total", "invoice_number"}


def test_extract_invoice_with_mock_provider_flags_all_required_fields_as_missing() -> None:
    # MockProvider's default (unconfigured) response is a schema-shaped
    # placeholder of empty/None values -- exercising extract_invoice
    # against it end to end should surface every REQUIRED_FIELDS entry
    # as missing rather than accepting the placeholders as real data.
    provider = MockProvider(structured_output={"document_type": "invoice"})
    # MockProvider returns the same configured value for every call, so
    # extraction also receives {"document_type": "invoice"} -- which
    # InvoiceData happily parses as all-fields-absent.
    result = extract_invoice(provider, "some document text")

    assert result.data == InvoiceData()
    assert set(result.missing_required_fields) == {
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "total",
        "currency",
    }


def test_strict_json_schema_requires_every_property_and_forbids_extras() -> None:
    schema = strict_json_schema(InvoiceData)

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())

    line_item_schema = schema["$defs"]["InvoiceLineItem"]
    assert line_item_schema["additionalProperties"] is False
    assert set(line_item_schema["required"]) == set(line_item_schema["properties"].keys())
