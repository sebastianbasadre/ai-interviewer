import pytest
from pydantic import ValidationError

from ai_interviewer.config import Settings


def test_offline_settings_default_to_mock_without_secrets(monkeypatch):
    for key in ("ADMIN_API_KEY", "IP_HASH_SECRET", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AVATAR_MODE"):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.avatar_mode == "mock"
    assert set(settings.missing_secrets()) == {"ADMIN_API_KEY", "IP_HASH_SECRET"}


def test_secret_is_hidden_from_repr_and_missing_check_names_only():
    settings = Settings(_env_file=None, admin_api_key="unit-test-only", ip_hash_secret=" ")
    assert "unit-test-only" not in repr(settings)
    assert settings.missing_secrets() == ["IP_HASH_SECRET"]


@pytest.mark.parametrize("minutes", [0, 31])
def test_session_cost_cap_cannot_exceed_thirty_minutes(minutes):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, interview_max_minutes=minutes)
