import pytest

from core.config import settings


@pytest.fixture(autouse=True)
def use_mock_source(monkeypatch):
    """Tests must not invoke a paid external Actor from a developer's .env."""
    monkeypatch.setattr(settings, "JOB_SOURCE", "mock")
