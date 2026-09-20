"""Invoice extraction evaluation (TASK-020).

Runs extract_invoice() against the synthetic fixtures from TASK-019
using whatever AIProvider is actually configured, and reports per-field
accuracy against each fixture's ground truth.

Skipped unless AI_PROVIDER=cloud and OPENAI_API_KEY are set: this test
makes real, paid LLM calls (two per fixture -- classify then extract),
so it must never run against MockProvider (which would trivially
"pass" everything by echoing back whatever's configured) or block a
contributor's `pytest` run when they have no key configured.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from ascent.ai.factory import get_ai_provider
from ascent.ai.provider import AIProvider
from ascent.invoices.extraction import NotAnInvoiceError, extract_invoice
from ascent.invoices.schema import InvoiceData
from ascent.shared.config import get_settings

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "invoices"
FIXTURE_NAMES = sorted({p.stem for p in FIXTURES_DIR.glob("*.txt")})

# Compared individually so a mismatch reports which field is wrong,
# rather than a single pass/fail for the whole invoice.
_SCALAR_FIELDS = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "project_name",
    "customer_name",
    "po_number",
    "subtotal",
    "tax",
    "total",
    "currency",
    "payment_terms",
)
_LINE_ITEM_FIELDS = ("description", "quantity", "unit_price", "cost_code")

_ACCURACY_THRESHOLD = 0.8


def _settings_allow_real_eval() -> bool:
    settings = get_settings()
    return settings.ai_provider == "cloud" and bool(settings.openai_api_key)


pytestmark = pytest.mark.skipif(
    not _settings_allow_real_eval(),
    reason="invoice evaluation calls a real AI provider; set AI_PROVIDER=cloud and OPENAI_API_KEY",
)


@dataclass
class FieldMismatch:
    field_name: str
    expected: Any
    actual: Any


@dataclass
class EvalResult:
    fixture_name: str
    field_count: int
    mismatches: list[FieldMismatch]

    @property
    def accuracy(self) -> float:
        if self.field_count == 0:
            return 1.0
        return 1 - len(self.mismatches) / self.field_count


def _values_match(expected: Any, actual: Any) -> bool:
    if expected is None:
        return actual is None
    if isinstance(expected, int | float) and isinstance(actual, int | float):
        return abs(float(expected) - float(actual)) < 0.01
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().casefold() == actual.strip().casefold()
    return expected == actual  # type: ignore[no-any-return]


def _load_expected(fixture_name: str) -> InvoiceData:
    payload = json.loads((FIXTURES_DIR / f"{fixture_name}.expected.json").read_text())
    return InvoiceData.model_validate(payload)


def _evaluate_fixture(fixture_name: str, provider: AIProvider) -> EvalResult:
    document_text = (FIXTURES_DIR / f"{fixture_name}.txt").read_text()
    expected = _load_expected(fixture_name)
    field_count = len(_SCALAR_FIELDS) + max(len(expected.line_items), 1) * len(_LINE_ITEM_FIELDS)

    try:
        result = extract_invoice(provider, document_text)
    except NotAnInvoiceError as exc:
        # A misclassification is a classification-prompt problem, not an
        # extraction-accuracy one -- surface it as a single, clearly
        # labeled mismatch rather than every field silently "failing".
        return EvalResult(
            fixture_name=fixture_name,
            field_count=field_count,
            mismatches=[
                FieldMismatch("classification", "invoice", exc.document_type.value),
            ],
        )

    actual = result.data
    mismatches = [
        FieldMismatch(field, getattr(expected, field), getattr(actual, field))
        for field in _SCALAR_FIELDS
        if not _values_match(getattr(expected, field), getattr(actual, field))
    ]

    if len(expected.line_items) != len(actual.line_items):
        mismatches.append(
            FieldMismatch("line_items.count", len(expected.line_items), len(actual.line_items))
        )
    else:
        for index, (expected_item, actual_item) in enumerate(
            zip(expected.line_items, actual.line_items, strict=True)
        ):
            for line_field in _LINE_ITEM_FIELDS:
                expected_value = getattr(expected_item, line_field)
                actual_value = getattr(actual_item, line_field)
                if not _values_match(expected_value, actual_value):
                    mismatches.append(
                        FieldMismatch(
                            f"line_items[{index}].{line_field}", expected_value, actual_value
                        )
                    )

    return EvalResult(fixture_name=fixture_name, field_count=field_count, mismatches=mismatches)


def test_invoice_extraction_accuracy_against_synthetic_dataset() -> None:
    provider = get_ai_provider()
    results = [_evaluate_fixture(name, provider) for name in FIXTURE_NAMES]
    overall_accuracy = sum(r.accuracy for r in results) / len(results)

    print(f"\n=== Invoice extraction evaluation ({len(results)} fixtures) ===")
    for result in results:
        label = f"{result.fixture_name}: {result.accuracy:.0%}"
        print(f"{label} ({len(result.mismatches)} mismatches)")
        for mismatch in result.mismatches:
            expected, actual = mismatch.expected, mismatch.actual
            print(f"  - {mismatch.field_name}: expected {expected!r}, got {actual!r}")
    print(f"Overall accuracy: {overall_accuracy:.0%}")

    assert overall_accuracy >= _ACCURACY_THRESHOLD, (
        f"accuracy {overall_accuracy:.0%} is below the {_ACCURACY_THRESHOLD:.0%} threshold"
    )
