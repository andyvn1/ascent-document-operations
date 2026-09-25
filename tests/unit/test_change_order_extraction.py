from datetime import date
from typing import Any

import pytest

from ascent.ai.provider import AIProvider
from ascent.ai.providers.mock import MockProvider
from ascent.change_orders.extraction import (
    NotAChangeOrderError,
    extract_change_order,
)
from ascent.change_orders.schema import ChangeOrderData
from ascent.documents.models import DocumentType

_FULL_CHANGE_ORDER = {
    "project_name": "Maple Street Townhomes",
    "change_order_number": "CO-004",
    "request_date": "2026-06-01",
    "requesting_company": "Ascent General Contracting",
    "description": "Add fire-rated drywall to stairwell enclosures",
    "reason": "Updated fire code requirement from inspector",
    "requested_amount": 4200.00,
    "schedule_impact": "Adds 3 days to framing phase",
    "approver": "Jane Rivera, Project Manager",
    "status": "Pending",
    "related_contract_or_po": "PO-7734",
    "supporting_documentation": "Inspector report attached",
}


class _QueuedProvider:
    """Returns queued responses in order -- one per
    generate_structured_output call. classify_document and
    extract_change_order each need a distinct response shape, which
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


def test_extract_change_order_raises_when_not_classified_as_change_order() -> None:
    provider = _QueuedProvider([{"document_type": "invoice"}])

    with pytest.raises(NotAChangeOrderError) as exc_info:
        extract_change_order(provider, "some document text")

    assert exc_info.value.document_type == DocumentType.INVOICE


def test_extract_change_order_does_not_call_extraction_when_not_change_order() -> None:
    # Only one response queued -- if extract_change_order made a second
    # generate_structured_output call after classification rejected the
    # document, popping from the empty list would raise IndexError.
    provider = _QueuedProvider([{"document_type": "unrecognized"}])

    with pytest.raises(NotAChangeOrderError):
        extract_change_order(provider, "some document text")


def test_extract_change_order_returns_parsed_data_with_no_missing_fields_or_issues() -> None:
    provider = _QueuedProvider([{"document_type": "change_order"}, dict(_FULL_CHANGE_ORDER)])

    result = extract_change_order(provider, "some document text", as_of=date(2026, 12, 1))

    assert result.data.project_name == "Maple Street Townhomes"
    assert result.data.requested_amount == 4200.00
    assert result.missing_required_fields == []
    assert result.validation_issues == []
    assert result.requires_approval_review is False


def test_extract_change_order_flags_missing_required_fields_instead_of_defaulting() -> None:
    incomplete = dict(_FULL_CHANGE_ORDER)
    incomplete["requested_amount"] = None
    incomplete["change_order_number"] = None
    provider = _QueuedProvider([{"document_type": "change_order"}, incomplete])

    result = extract_change_order(provider, "some document text", as_of=date(2026, 12, 1))

    assert result.data.requested_amount is None
    assert set(result.missing_required_fields) == {"requested_amount", "change_order_number"}


def test_extract_change_order_requires_approval_review_when_approver_missing() -> None:
    unapproved = dict(_FULL_CHANGE_ORDER)
    unapproved["approver"] = None
    provider = _QueuedProvider([{"document_type": "change_order"}, unapproved])

    result = extract_change_order(provider, "some document text", as_of=date(2026, 12, 1))

    # A missing approver is a normal lifecycle state, not an extraction
    # failure -- it must NOT show up in missing_required_fields, only
    # in the dedicated requires_approval_review flag.
    assert "approver" not in result.missing_required_fields
    assert result.requires_approval_review is True


def test_extract_change_order_flags_non_positive_requested_amount() -> None:
    bad_amount = dict(_FULL_CHANGE_ORDER)
    bad_amount["requested_amount"] = 0.0
    provider = _QueuedProvider([{"document_type": "change_order"}, bad_amount])

    result = extract_change_order(provider, "some document text", as_of=date(2026, 12, 1))

    assert "requested_amount must be a positive amount" in result.validation_issues


def test_extract_change_order_flags_future_request_date() -> None:
    provider = _QueuedProvider([{"document_type": "change_order"}, dict(_FULL_CHANGE_ORDER)])

    # _FULL_CHANGE_ORDER's request_date is 2026-06-01 -- pin as_of to
    # before that instead of relying on wall-clock "today".
    result = extract_change_order(provider, "some document text", as_of=date(2026, 1, 1))

    assert "request_date is in the future" in result.validation_issues


def test_extract_change_order_with_mock_provider_flags_missing_fields_and_approval() -> None:
    provider = MockProvider(structured_output={"document_type": "change_order"})

    result = extract_change_order(provider, "some document text", as_of=date(2026, 12, 1))

    assert result.data == ChangeOrderData()
    assert set(result.missing_required_fields) == {
        "project_name",
        "change_order_number",
        "request_date",
        "requesting_company",
        "description",
        "requested_amount",
    }
    assert result.requires_approval_review is True
    assert result.validation_issues == []
