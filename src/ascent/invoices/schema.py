"""Invoice extraction schema.

Field set matches the invoice_data table design
(docs/architecture/database-design.md) and the master-plan invoice
field list. Every field is Optional -- the model may not find a given
field on a given invoice -- so a missing value is representable
without Pydantic rejecting the whole extraction. Which of those
missing values actually matter is decided in extraction.py via
REQUIRED_FIELDS, not by field-level validation here: that keeps "is
this JSON-shaped" (this file) separate from "is this invoice usable"
(a business decision downstream review can override).
"""

from datetime import date

from pydantic import BaseModel


class InvoiceLineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    cost_code: str | None = None


class InvoiceData(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    project_name: str | None = None
    customer_name: str | None = None
    po_number: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    currency: str | None = None
    payment_terms: str | None = None
    line_items: list[InvoiceLineItem] = []


# Fields whose absence makes the invoice unusable without human review --
# not every field the model might find, just the ones downstream
# workflow (approval, export, duplicate detection) depends on.
REQUIRED_FIELDS: tuple[str, ...] = (
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "total",
    "currency",
)
