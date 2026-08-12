import json
from dataclasses import dataclass
from typing import Any

import jsonschema
import pytest

from ascent.ai.provider import AIProvider
from ascent.ai.providers.cloud import CloudProvider

TEST_SCHEMA: dict[str, Any] = {
    "properties": {
        "vendor_name": {"type": "string"},
        "total": {"type": "number"},
    },
    "required": ["vendor_name", "total"],
}


@dataclass
class _Usage:
    prompt_tokens: int
    completion_tokens: int = 0


@dataclass
class _Message:
    content: str


@dataclass
class _Choice:
    message: _Message


@dataclass
class _ChatResponse:
    choices: list[_Choice]
    usage: _Usage


@dataclass
class _EmbeddingItem:
    embedding: list[float]


@dataclass
class _EmbeddingResponse:
    data: list[_EmbeddingItem]
    usage: _Usage


class _FakeCompletions:
    def __init__(self, response: _ChatResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _ChatResponse:
        self.calls.append(kwargs)
        return self.response


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeEmbeddings:
    def __init__(self, response: _EmbeddingResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _EmbeddingResponse:
        self.calls.append(kwargs)
        return self.response


class _FakeClient:
    """Stands in for openai.OpenAI in tests -- only implements the
    two attributes CloudProvider actually touches, so tests never make
    a real network call or need an API key.
    """

    def __init__(self, *, chat: _FakeChat, embeddings: _FakeEmbeddings | None = None) -> None:
        self.chat = chat
        self.embeddings = embeddings


def _chat_provider(
    content: str, *, prompt_tokens: int = 10, completion_tokens: int = 5
) -> tuple[CloudProvider, _FakeCompletions]:
    response = _ChatResponse(
        choices=[_Choice(message=_Message(content=content))],
        usage=_Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )
    completions = _FakeCompletions(response)
    client = _FakeClient(chat=_FakeChat(completions))
    provider = CloudProvider(api_key="test-key", client=client)  # type: ignore[arg-type]
    return provider, completions


def test_cloud_provider_satisfies_ai_provider_protocol() -> None:
    provider, _ = _chat_provider("{}")
    checked: AIProvider = provider
    assert checked is not None


def test_generate_structured_output_returns_parsed_and_validated_json() -> None:
    provider, completions = _chat_provider(json.dumps({"vendor_name": "Acme", "total": 42.5}))

    result = provider.generate_structured_output(
        system_prompt="extract",
        user_prompt="doc text",
        output_schema=TEST_SCHEMA,
    )

    assert result == {"vendor_name": "Acme", "total": 42.5}
    assert completions.calls[0]["response_format"]["json_schema"]["schema"] == TEST_SCHEMA


def test_generate_structured_output_raises_on_schema_mismatch() -> None:
    provider, _ = _chat_provider(json.dumps({"vendor_name": "Acme"}))

    with pytest.raises(jsonschema.ValidationError):
        provider.generate_structured_output(
            system_prompt="extract",
            user_prompt="doc text",
            output_schema=TEST_SCHEMA,
        )


def test_generate_text_returns_message_content() -> None:
    provider, _ = _chat_provider("plain text response")

    result = provider.generate_text(system_prompt="summarize", user_prompt="doc text")

    assert result == "plain text response"


def test_create_embeddings_returns_one_vector_per_text() -> None:
    response = _EmbeddingResponse(
        data=[_EmbeddingItem(embedding=[0.1, 0.2]), _EmbeddingItem(embedding=[0.3, 0.4])],
        usage=_Usage(prompt_tokens=6),
    )
    embeddings = _FakeEmbeddings(response)
    client = _FakeClient(
        chat=_FakeChat(_FakeCompletions(_ChatResponse([], _Usage(0)))), embeddings=embeddings
    )
    provider = CloudProvider(api_key="test-key", client=client)  # type: ignore[arg-type]

    result = provider.create_embeddings(texts=["a", "b"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]


def test_create_embeddings_empty_input_returns_empty_output_without_calling_api() -> None:
    embeddings = _FakeEmbeddings(_EmbeddingResponse([], _Usage(0)))
    client = _FakeClient(
        chat=_FakeChat(_FakeCompletions(_ChatResponse([], _Usage(0)))), embeddings=embeddings
    )
    provider = CloudProvider(api_key="test-key", client=client)  # type: ignore[arg-type]

    result = provider.create_embeddings(texts=[])

    assert result == []
    assert embeddings.calls == []


def test_generate_text_records_usage_and_cost() -> None:
    provider, _ = _chat_provider("response", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    provider._text_model = "gpt-5-nano"

    provider.generate_text(system_prompt="s", user_prompt="u")

    assert len(provider.usage_log) == 1
    record = provider.usage_log[0]
    assert record.input_tokens == 1_000_000
    assert record.output_tokens == 1_000_000
    assert record.cost_usd == pytest.approx(0.20 + 1.25)


def test_unknown_model_pricing_defaults_to_zero_cost() -> None:
    provider, _ = _chat_provider("response")
    provider._text_model = "some-future-model"

    provider.generate_text(system_prompt="s", user_prompt="u")

    assert provider.usage_log[0].cost_usd == 0.0
