"""AI provider selection.

Every future call site that needs an AIProvider (invoice extraction,
change-order extraction, embeddings for duplicate detection) asks for
one here instead of importing MockProvider or a cloud implementation
directly. That keeps "which provider is active" a single
configuration-driven decision instead of an if/mock/cloud branch
duplicated at every call site.
"""

from ascent.ai.provider import AIProvider
from ascent.ai.providers.mock import MockProvider
from ascent.shared.config import Settings, get_settings


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    if settings.ai_provider == "mock":
        return MockProvider()
    raise NotImplementedError(
        f"AI provider {settings.ai_provider!r} is not implemented yet"
    )
