import pytest
from pydantic_core import ValidationError

from app.core.config import Settings


def test_unrelated_debug_environment_does_not_break_settings(monkeypatch):
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.delenv("DRIFTWATCH_DEBUG", raising=False)

    settings = Settings()

    assert settings.DEBUG is True


def test_namespaced_debug_accepts_boolean_values(monkeypatch):
    monkeypatch.setenv("DRIFTWATCH_DEBUG", "false")

    settings = Settings()

    assert settings.DEBUG is False


def test_namespaced_debug_rejects_non_boolean_values(monkeypatch):
    monkeypatch.setenv("DRIFTWATCH_DEBUG", "release")

    with pytest.raises(ValidationError):
        Settings()
