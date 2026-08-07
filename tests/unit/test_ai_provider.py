from typing import Any

from ascent.ai.provider import AIProvider
from ascent.ai.providers.mock import MockProvider

TEST_SCHEMA: dict[str, Any] = {
    "properties": {
        "vendor_name": {"type": "string"},
        "total": {"type": "number"},
        "line_item_count": {"type": "integer"},
        "is_paid": {"type": "boolean"},
        "line_items": {"type": "array"},
        "metadata": {"type": "object"},
        "notes": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    }
}


def test_mock_provider_satisfies_ai_provider_protocol() -> None:
    provider: AIProvider = MockProvider()
    assert provider is not None


def test_generate_structured_output_default_placeholder_matches_schema_types() -> None:
    provider = MockProvider()

    result = provider.generate_structured_output(
        system_prompt="extract fields",
        user_prompt="document text",
        output_schema=TEST_SCHEMA,
    )

    assert result == {
        "vendor_name": "",
        "total": 0.0,
        "line_item_count": 0,
        "is_paid": False,
        "line_items": [],
        "metadata": {},
        "notes": None,
    }


def test_generate_structured_output_returns_configured_value_regardless_of_schema() -> None:
    configured = {"vendor_name": "Acme Construction", "total": 4200.50}
    provider = MockProvider(structured_output=configured)

    result = provider.generate_structured_output(
        system_prompt="extract fields",
        user_prompt="document text",
        output_schema=TEST_SCHEMA,
    )

    assert result == configured


def test_generate_text_default() -> None:
    provider = MockProvider()

    result = provider.generate_text(system_prompt="summarize", user_prompt="document text")

    assert result == "mock response"


def test_generate_text_configured() -> None:
    provider = MockProvider(text_output="a specific canned response")

    result = provider.generate_text(system_prompt="summarize", user_prompt="document text")

    assert result == "a specific canned response"


def test_create_embeddings_returns_one_vector_per_text() -> None:
    provider = MockProvider(embedding_dim=4)

    result = provider.create_embeddings(texts=["invoice one", "invoice two", "invoice three"])

    assert len(result) == 3
    assert all(len(vector) == 4 for vector in result)


def test_create_embeddings_empty_input_returns_empty_output() -> None:
    provider = MockProvider()

    result = provider.create_embeddings(texts=[])

    assert result == []
