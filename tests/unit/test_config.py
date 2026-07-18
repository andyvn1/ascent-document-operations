import pytest
from pydantic import ValidationError

from ascent.shared.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"


def test_settings_rejects_invalid_app_env() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="not_a_real_env")  # type: ignore[call-arg, arg-type]