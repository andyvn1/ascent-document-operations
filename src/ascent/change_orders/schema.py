"""Change-order extraction schema.

Field set matches the change_order_data table design
(docs/architecture/database-design.md) plus supporting_documentation
from the master plan's field list (not in the DB design's initial
table, but explicitly named as a field to extract). Every field is
Optional -- the model may not find a given field on a given change
order -- so a missing value is representable without Pydantic
rejecting the whole extraction. This schema deliberately doesn't decide
which absences matter; that's extraction.py's job (REQUIRED_FIELDS for
"extraction looks incomplete", separately from "approver" for "not yet
approved" -- see extraction.py's docstring for why those are not the
same kind of problem).
"""

from datetime import date

from pydantic import BaseModel


class ChangeOrderData(BaseModel):
    project_name: str | None = None
    change_order_number: str | None = None
    request_date: date | None = None
    requesting_company: str | None = None
    description: str | None = None
    reason: str | None = None
    requested_amount: float | None = None
    schedule_impact: str | None = None
    approver: str | None = None
    status: str | None = None
    related_contract_or_po: str | None = None
    supporting_documentation: str | None = None


# Fields whose absence means the extraction itself looks incomplete --
# not every field the model might find. Deliberately excludes
# `approver`: an unapproved change order is a normal, expected state
# (see extraction.py), not a sign extraction failed to find something
# that should be there.
REQUIRED_FIELDS: tuple[str, ...] = (
    "project_name",
    "change_order_number",
    "request_date",
    "requesting_company",
    "description",
    "requested_amount",
)
