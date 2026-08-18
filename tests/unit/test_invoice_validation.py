import json
from pathlib import Path

import pytest

from ascent.invoices.schema import InvoiceData
from ascent.invoices.validation import (
    FieldConfidence,
    find_duplicate,
    numeric_inconsistencies,
    score_invoice_fields,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "invoices"


def _load_expected(name: str) -> InvoiceData:
    payload = json.loads((FIXTURES_DIR / f"{name}.expected.json").read_text())
    return InvoiceData.model_validate(payload)


def test_fixture_pairs_exist_and_parse_as_invoice_data() -> None:
    txt_files = sorted(FIXTURES_DIR.glob("*.txt"))
    assert len(txt_files) >= 4, "expected at least 4 synthetic evaluation invoices"
    for txt_file in txt_files:
        expected_path = txt_file.with_suffix("").with_suffix(".expected.json")
        assert expected_path.exists(), f"missing ground truth for {txt_file.name}"
        # Raises if the fixture's ground truth doesn't match InvoiceData's shape.
        InvoiceData.model_validate(json.loads(expected_path.read_text()))


def test_score_invoice_fields_gives_full_confidence_to_clean_invoice() -> None:
    data = _load_expected("clean-full")

    scores = score_invoice_fields(data)

    by_name = {score.field_name: score for score in scores}
    assert by_name["total"].confidence == pytest.approx(0.95)
    assert by_name["subtotal"].confidence == pytest.approx(0.95)
    assert by_name["line_items"].confidence == pytest.approx(0.95)


def test_score_invoice_fields_zeroes_out_missing_fields() -> None:
    data = _load_expected("missing-optional-fields")

    scores = score_invoice_fields(data)

    by_name = {score.field_name: score for score in scores}
    assert by_name["due_date"].confidence == 0.0
    assert by_name["po_number"].confidence == 0.0
    assert by_name["vendor_name"].confidence == pytest.approx(0.95)


def test_score_invoice_fields_covers_every_schema_field() -> None:
    data = _load_expected("clean-full")

    scores = score_invoice_fields(data)

    assert {score.field_name for score in scores} == set(InvoiceData.model_fields)
    assert all(isinstance(score, FieldConfidence) for score in scores)
    assert all(0.0 <= score.confidence <= 1.0 for score in scores)


def test_numeric_inconsistencies_empty_for_reconciled_invoice() -> None:
    data = _load_expected("clean-full")

    assert numeric_inconsistencies(data) == set()


def test_numeric_inconsistencies_flags_total_mismatch() -> None:
    data = _load_expected("inconsistent-totals")

    inconsistent = numeric_inconsistencies(data)

    assert inconsistent == {"subtotal", "tax", "total"}


def test_score_invoice_fields_lowers_confidence_for_inconsistent_total() -> None:
    data = _load_expected("inconsistent-totals")

    scores = score_invoice_fields(data)

    by_name = {score.field_name: score for score in scores}
    assert by_name["total"].confidence == pytest.approx(0.4)
    assert by_name["subtotal"].confidence == pytest.approx(0.4)
    assert by_name["tax"].confidence == pytest.approx(0.4)
    # Untouched fields keep their normal confidence.
    assert by_name["vendor_name"].confidence == pytest.approx(0.95)


def test_numeric_inconsistencies_flags_line_items_not_matching_subtotal() -> None:
    data = InvoiceData.model_validate(
        {
            "subtotal": 100.0,
            "line_items": [{"quantity": 2, "unit_price": 10.0}],  # sums to 20, not 100
        }
    )

    assert numeric_inconsistencies(data) == {"subtotal", "line_items"}


def test_numeric_inconsistencies_skips_line_item_check_when_a_line_is_unpriced() -> None:
    data = InvoiceData.model_validate(
        {
            "subtotal": 100.0,
            "line_items": [{"quantity": 2, "unit_price": None}],
        }
    )

    # No false positive: without a unit_price we can't compute a line-item
    # total, so the mismatch check is skipped rather than guessing.
    assert numeric_inconsistencies(data) == set()


def test_find_duplicate_matches_on_vendor_invoice_number_and_amount() -> None:
    duplicate_a = _load_expected("duplicate-a")
    duplicate_b = _load_expected("duplicate-b")

    match = find_duplicate(duplicate_b, existing=[duplicate_a])

    assert match == duplicate_a


def test_find_duplicate_returns_none_for_distinct_invoices() -> None:
    clean = _load_expected("clean-full")
    other = _load_expected("missing-optional-fields")

    assert find_duplicate(clean, existing=[other]) is None


def test_find_duplicate_returns_none_when_key_fields_are_missing() -> None:
    incomplete = InvoiceData.model_validate({"vendor_name": "Acme", "total": 100.0})
    other = InvoiceData.model_validate(
        {"vendor_name": "Acme", "invoice_number": "1", "total": 100.0}
    )

    assert find_duplicate(incomplete, existing=[other]) is None


def test_find_duplicate_is_case_insensitive_on_vendor_and_invoice_number() -> None:
    a = InvoiceData.model_validate(
        {"vendor_name": "Acme Corp", "invoice_number": "INV-1", "total": 500.0}
    )
    b = InvoiceData.model_validate(
        {"vendor_name": "  acme corp  ", "invoice_number": "inv-1", "total": 500.0}
    )

    assert find_duplicate(a, existing=[b]) == b
