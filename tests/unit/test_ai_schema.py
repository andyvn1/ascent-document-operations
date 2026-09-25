from pydantic import BaseModel

from ascent.ai.schema import strict_json_schema


class _NestedModel(BaseModel):
    a: str | None = None
    b: int | None = None


class _ParentModel(BaseModel):
    x: str | None = None
    y: list[_NestedModel] = []


def test_strict_json_schema_requires_every_property_and_forbids_extras() -> None:
    schema = strict_json_schema(_ParentModel)

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())

    nested_schema = schema["$defs"]["_NestedModel"]
    assert nested_schema["additionalProperties"] is False
    assert set(nested_schema["required"]) == set(nested_schema["properties"].keys())
