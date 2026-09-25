"""Schema shaping for AIProvider's structured-output mode.

Shared by every document-type extraction module -- takes any Pydantic
model, not just an invoice- or change-order-specific one.
"""

from typing import Any

from pydantic import BaseModel


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build a JSON Schema for model suitable for a provider's
    strict/schema-constrained structured-output mode.

    Pydantic's model_json_schema() marks Optional fields as not
    required (since they have a default) and never sets
    additionalProperties. Strict mode needs the opposite: every
    property listed in "required" -- nullability is expressed through
    the anyOf/type union Pydantic already emits, not through omitting
    the key -- and additionalProperties: false on every object,
    including nested $defs entries (e.g. InvoiceLineItem).
    """
    schema = model.model_json_schema()
    for definition in (*schema.get("$defs", {}).values(), schema):
        if definition.get("type") == "object":
            definition["additionalProperties"] = False
            definition["required"] = list(definition.get("properties", {}).keys())
    return schema
