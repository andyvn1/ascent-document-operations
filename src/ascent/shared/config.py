"""Application configuration.

Settings are read once from the environment and validated at startup,
rather than calling os.environ.get() throughout the codebase. A missing
or malformed value fails immediately and loudly here, instead of
surfacing as a confusing bug wherever that value happens to get used.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Cached so Settings is parsed from the environment exactly once
    per process, not on every request.
    """
    return Settings()