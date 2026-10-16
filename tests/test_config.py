import pytest
from pydantic import ValidationError

from app.config import Settings


def test_weak_admin_token_rejected():
    with pytest.raises(ValidationError):
        Settings(ADMIN_TOKEN="change-me-admin")


def test_short_admin_token_rejected():
    with pytest.raises(ValidationError):
        Settings(ADMIN_TOKEN="krotki")


def test_strong_admin_token_ok():
    settings = Settings(ADMIN_TOKEN="bardzo-dlugi-i-losowy-sekret-123")
    assert settings.ADMIN_TOKEN == "bardzo-dlugi-i-losowy-sekret-123"


def test_insecure_override_allows_weak_token():
    settings = Settings(ADMIN_TOKEN="change-me-admin", ALLOW_INSECURE_DEFAULTS=True)
    assert settings.ADMIN_TOKEN == "change-me-admin"
