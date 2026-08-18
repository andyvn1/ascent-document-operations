"""Confidence scoring and duplicate detection for extracted invoices.

Confidence here is rule-based, not the model's self-reported
confidence -- LLMs are poorly calibrated at rating their own certainty,
so a field's score is derived from checks a reviewer could verify by
eye: is the field present, and does it agree with the invoice's other
numbers. That keeps every score explainable ("total is low confidence
because it doesn't match subtotal + tax"), which is what a review UI
needs to show a reviewer, rather than an opaque number the model made
up.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ascent.invoices.schema import InvoiceData

# Invoice totals come from OCR'd/AI-extracted text, not a ledger --
# treat amounts within a cent as reconciled rather than requiring
# exact float equality.
_AMOUNT_TOLERANCE = 0.01

_PRESENT_CONFIDENCE = 0.95
_INCONSISTENT_CONFIDENCE = 0.4
_MISSING_CONFIDENCE = 0.0


@dataclass
class FieldConfidence:
    field_name: str
    value: Any
    confidence: float


def score_invoice_fields(data: InvoiceData) -> list[FieldConfidence]:
    """Return one FieldConfidence per field on InvoiceData, each in
    [0.0, 1.0].

    A missing field scores 0.0 -- there's nothing to be confident
    about. A present field starts at a high baseline and is marked
    down only if numeric_inconsistencies() names it, so a reviewer can
    always trace a low score back to a specific, stated reason instead
    of a single opaque formula covering the whole invoice.
    """
    inconsistent = numeric_inconsistencies(data)
    scores: list[FieldConfidence] = []
    for field_name in InvoiceData.model_fields:
        value = getattr(data, field_name)
        if field_name == "line_items":
            confidence = (
                _MISSING_CONFIDENCE
                if not value
                else (
                    _INCONSISTENT_CONFIDENCE
                    if "line_items" in inconsistent
                    else _PRESENT_CONFIDENCE
                )
            )
        elif value is None:
            confidence = _MISSING_CONFIDENCE
        elif field_name in inconsistent:
            confidence = _INCONSISTENT_CONFIDENCE
        else:
            confidence = _PRESENT_CONFIDENCE
        scores.append(FieldConfidence(field_name=field_name, value=value, confidence=confidence))
    return scores


def numeric_inconsistencies(data: InvoiceData) -> set[str]:
    """Return the names of numeric fields whose values don't reconcile
    with each other. Two checks, both skipped (not falsely flagged)
    when the inputs they need aren't fully present:

    - subtotal + tax should equal total.
    - the sum of each line item's quantity * unit_price should equal
      subtotal.
    """
    inconsistent: set[str] = set()

    if data.subtotal is not None and data.tax is not None and data.total is not None:
        if abs((data.subtotal + data.tax) - data.total) > _AMOUNT_TOLERANCE:
            inconsistent.update({"subtotal", "tax", "total"})

    if data.subtotal is not None and data.line_items:
        line_items_total = 0.0
        every_item_priced = True
        for item in data.line_items:
            quantity = item.quantity
            unit_price = item.unit_price
            if quantity is None or unit_price is None:
                every_item_priced = False
                break
            line_items_total += quantity * unit_price
        if every_item_priced and abs(line_items_total - data.subtotal) > _AMOUNT_TOLERANCE:
            inconsistent.update({"subtotal", "line_items"})

    return inconsistent


def find_duplicate(candidate: InvoiceData, existing: Iterable[InvoiceData]) -> InvoiceData | None:
    """Return the first invoice in existing that matches candidate on
    vendor name, invoice number, and total -- the three fields a human
    reviewer would check by eye to spot a re-submitted invoice.
    Deliberately not fuzzy/semantic matching: every match this returns
    can be explained as "same vendor, same invoice number, same
    amount," rather than a similarity score nobody can audit.
    """
    for other in existing:
        if _same_invoice(candidate, other):
            return other
    return None


def _same_invoice(a: InvoiceData, b: InvoiceData) -> bool:
    if a.vendor_name is None or b.vendor_name is None:
        return False
    if a.invoice_number is None or b.invoice_number is None:
        return False
    if a.total is None or b.total is None:
        return False
    return (
        a.vendor_name.strip().casefold() == b.vendor_name.strip().casefold()
        and a.invoice_number.strip().casefold() == b.invoice_number.strip().casefold()
        and abs(a.total - b.total) <= _AMOUNT_TOLERANCE
    )
