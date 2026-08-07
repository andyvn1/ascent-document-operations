"""Deterministic AIProvider implementation for tests.

No network calls, no API key, no cost, and no nondeterminism -- unit
tests for extraction and validation logic (TASK-018 onward) run
instantly against this instead of a real model. Tests that need to
assert on a *specific* extraction result construct MockProvider with
`structured_output=...` to control exactly what
generate_structured_output returns; tests that only care about the
plumbing can use the default schema-shaped placeholder.
"""

from typing import Any


class MockProvider:
    def __init__(
        self,
        *,
        structured_output: dict[str, Any] | None = None,
        text_output: str = "mock response",
        embedding_dim: int = 8,
    ) -> None:
        self._structured_output = structured_output
        self._text_output = text_output
        self._embedding_dim = embedding_dim

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        if self._structured_output is not None:
            return self._structured_output
        return _placeholder_for_schema(output_schema)

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return self._text_output

    def create_embeddings(
        self,
        *,
        texts: list[str],
    ) -> list[list[float]]:
        return [[0.0] * self._embedding_dim for _ in texts]


def _placeholder_for_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Build a dict matching schema's top-level properties.

    Lets generate_structured_output return something structurally
    valid by default, so a test that doesn't care about the actual
    values still gets a well-shaped result rather than an empty dict.
    """
    properties: dict[str, Any] = schema.get("properties", {})
    return {name: _placeholder_for_type(prop.get("type")) for name, prop in properties.items()}


def _placeholder_for_type(json_type: str | None) -> Any:
    """Map a JSON Schema "type" to a placeholder value.

    Only handles a property with a plain top-level "type" key. Real
    Pydantic schemas also produce "anyOf" (Optional fields) and "$ref"
    (nested models) with no "type" key at all -- those fall through to
    the None default below. That's deliberate, not an oversight: this
    placeholder only needs to satisfy tests that don't care about the
    actual values, and resolving anyOf/$ref would mean walking
    schema["$defs"], which nothing here currently needs. Tests that do
    care construct MockProvider with structured_output=... instead.
    """
    if json_type is None:
        return None
    placeholders: dict[str, Any] = {
        "string": "",
        "integer": 0,
        "number": 0.0,
        "boolean": False,
        "array": [],
        "object": {},
    }
    return placeholders.get(json_type)
