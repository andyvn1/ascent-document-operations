"""Cloud AI provider backed by OpenAI's API.

Implements AIProvider (TASK-016) against a real API, as the counterpart
to MockProvider's in-memory placeholders. Timeouts and retries are
configured on the OpenAI client itself rather than hand-rolled here --
the SDK's built-in retry loop already retries connection errors, 429s,
and 5xxs with exponential backoff.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import jsonschema
from openai import OpenAI

logger = logging.getLogger(__name__)

# USD per 1M tokens, as (input_price, output_price). Embeddings have no
# separate output price, so their output_price is 0. A model missing
# from this table logs a warning and prices at $0 rather than raising --
# a pricing-table gap shouldn't take down extraction, only make its
# cost invisible until the table is updated.
_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "gpt-5-nano": (0.20, 1.25),
    "gpt-5-mini": (0.75, 4.50),
    "text-embedding-3-small": (0.02, 0.0),
}


@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class CloudProvider:
    """AIProvider implementation backed by OpenAI's Chat Completions and
    Embeddings APIs.
    """

    def __init__(
        self,
        *,
        api_key: str,
        text_model: str = "gpt-5-nano",
        embedding_model: str = "text-embedding-3-small",
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        client: OpenAI | None = None,
    ) -> None:
        self._text_model = text_model
        self._embedding_model = embedding_model
        self.usage_log: list[UsageRecord] = []
        self._client = client or OpenAI(
            api_key=api_key, max_retries=max_retries, timeout=timeout_seconds
        )

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._text_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": output_schema, "strict": True},
            },
        )
        content = response.choices[0].message.content or "{}"
        result: dict[str, Any] = json.loads(content)
        # Schema-constrained decoding makes a mismatch unlikely, but
        # model output is untrusted input -- validate before any caller
        # treats it as a typed extraction result.
        jsonschema.validate(instance=result, schema=output_schema)
        self._record_usage(self._text_model, response.usage)
        return result

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = self._client.chat.completions.create(
            model=self._text_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        self._record_usage(self._text_model, response.usage)
        return response.choices[0].message.content or ""

    def create_embeddings(
        self,
        *,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._embedding_model, input=texts)
        self._record_usage(self._embedding_model, response.usage)
        return [item.embedding for item in response.data]

    def _record_usage(self, model: str, usage: Any) -> None:
        input_tokens = usage.prompt_tokens
        output_tokens = getattr(usage, "completion_tokens", 0)
        cost_usd = _cost_for_usage(model, input_tokens, output_tokens)
        self.usage_log.append(
            UsageRecord(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )
        )
        logger.info(
            "ai provider request: model=%s input_tokens=%d output_tokens=%d cost_usd=%.6f",
            model,
            input_tokens,
            output_tokens,
            cost_usd,
        )


def _cost_for_usage(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _PRICING_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        logger.warning("no pricing configured for model %r; recording cost as $0", model)
        return 0.0
    input_price, output_price = pricing
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
