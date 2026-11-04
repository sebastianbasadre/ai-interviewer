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


def test_tavus_face_setting_supports_existing_replica_name_but_prefers_face():
    old = Settings(_env_file=None, tavus_replica_id="legacy_face")
    assert old.resolved_tavus_face_id.get_secret_value() == "legacy_face"
    both = Settings(_env_file=None, tavus_face_id="new_face", tavus_replica_id="legacy_face")
    assert both.resolved_tavus_face_id.get_secret_value() == "new_face"
    blank = Settings(_env_file=None, tavus_face_id=" ", tavus_replica_id="legacy_face")
    assert blank.resolved_tavus_face_id.get_secret_value() == "legacy_face"
    assert "new_face" not in repr(both)


def test_missing_tavus_settings_use_current_names_and_require_echo_pal():
    assert set(Settings(_env_file=None).missing_tavus_settings()) == {
        "TAVUS_API_KEY", "TAVUS_FACE_ID", "TAVUS_PAL_ID"}
    configured = Settings(_env_file=None, tavus_api_key="key", tavus_face_id="face", tavus_pal_id="pal")
    assert configured.missing_tavus_settings() == []
