"""AI provider interface.

Business logic (invoice extraction, change-order extraction, duplicate
detection via embeddings) must never import a vendor SDK directly.
Every model call goes through this interface instead, so that:

- Tests can run against MockProvider with no network access, no API
  key, and no cost.
- Swapping providers (cloud API now, local DGX inference later) means
  adding a new class that implements AIProvider, not rewriting call
  sites across the codebase.
- A future fallback/router (e.g. local first, cloud on failure) can be
  built as another AIProvider implementation without touching business
  logic at all.

AIProvider is a typing.Protocol -- Python's structural-typing tool for
interfaces. A class satisfies it just by having matching method
signatures; it doesn't need to inherit from AIProvider. The bodies here
are `...` because this file defines the shape only; the real logic
lives in the classes that implement it (MockProvider now, CloudProvider
in TASK-017).
"""

from typing import Any, Protocol


class AIProvider(Protocol):
    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Return model output constrained to output_schema.

        Used wherever the caller will parse the result into a Pydantic
        model (invoice fields, change-order fields) -- the schema is
        passed into the provider so the model is steered toward valid
        output, rather than validating freeform text after the fact.
        """
        ...

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Return unstructured model text for callers that don't need
        schema-constrained output.
        """
        ...

    def create_embeddings(
        self,
        *,
        texts: list[str],
    ) -> list[list[float]]:
        """Return one embedding vector per input text, in the same
        order as texts. Used for duplicate-invoice detection.
        """
        ...
