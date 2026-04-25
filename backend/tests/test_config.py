import pytest
import os


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("NEWS_API_KEY", "test-key")

    import importlib
    import app.config as cfg_module
    importlib.reload(cfg_module)
    from app.config import Settings
    s = Settings()

    assert s.anthropic_api_key == "sk-ant-test"
    assert s.max_position_pct == 0.20
    assert s.max_positions == 5
    assert s.min_confidence_to_trade == 0.65


def test_settings_missing_required_field():
    from pydantic import ValidationError
    from app.config import Settings
    with pytest.raises((ValidationError, Exception)):
        Settings(anthropic_api_key=None, database_url=None, news_api_key=None)
