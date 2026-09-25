from ascent.ai.providers.mock import MockProvider
from ascent.documents.classification import classify_document
from ascent.documents.models import DocumentType


def test_classify_document_returns_invoice() -> None:
    provider = MockProvider(structured_output={"document_type": "invoice"})

    assert classify_document(provider, "some document text") == DocumentType.INVOICE


def test_classify_document_returns_change_order() -> None:
    provider = MockProvider(structured_output={"document_type": "change_order"})

    assert classify_document(provider, "some document text") == DocumentType.CHANGE_ORDER


def test_classify_document_returns_unrecognized() -> None:
    provider = MockProvider(structured_output={"document_type": "unrecognized"})

    assert classify_document(provider, "some document text") == DocumentType.UNRECOGNIZED
