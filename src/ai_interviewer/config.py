"""Explicit, side-effect-free settings loading. Never log this model."""
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_mode: Literal["mock", "real"] = "mock"
    privacy_contact: str = ""

    anthropic_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    tavus_api_key: SecretStr | None = Field(default=None, repr=False)
    tavus_face_id: SecretStr | None = Field(default=None, repr=False)
    tavus_pal_id: SecretStr | None = Field(default=None, repr=False)
    # Compatibility for existing .env files. New code and diagnostics use FACE_ID.
    tavus_replica_id: SecretStr | None = Field(default=None, repr=False)
    admin_api_key: SecretStr | None = Field(default=None, repr=False)
    ip_hash_secret: SecretStr | None = Field(default=None, repr=False)
    conversation_model: str = "claude-haiku-5-5"
    conversation_enabled: bool = False
    conversation_max_calls: int = Field(default=30, ge=1, le=1000)
    conversation_timeout_seconds: float = Field(default=8, ge=1, le=20)
    scoring_model: str = "claude-opus-5-5"
    scoring_enabled: bool = False
    scoring_auto_generate: bool = True
    scoring_max_calls: int = Field(default=12, ge=3, le=300)
    scoring_timeout_seconds: float = Field(default=45, ge=5, le=90)
    tts_provider: Literal["openai", "piper"] = "openai"
    stt_provider: Literal["whisper_local", "openai"] = "whisper_local"
    whisper_model: str = "large-v3-turbo"
    whisper_device: Literal["cuda", "cpu"] = "cuda"
    avatar_mode: Literal["mock", "tavus", "svg"] = "mock"
    tavus_max_minutes_per_session: int = Field(default=30, ge=1, le=30)
    public_base_url: str = "http://localhost:8000"
    allow_mock_lan_http: bool = False
    realtime_enabled: bool = False
    tavus_enabled: bool = False
    piper_voice: str = "es_AR-daniela-high"
    piper_english_voice: str = "en_GB-jenny_dioco-medium"
    media_max_minutes: int = Field(default=3, ge=1, le=30)
    listen_port: int = Field(default=8000, ge=1024, le=65535)
    tls_cert_file: Path | None = None
    tls_key_file: Path | None = None
    turn_url: str = ""
    turn_shared_secret: SecretStr | None = Field(default=None, repr=False)
    data_dir: Path = Path("data")
    retention_days: int = Field(default=30, ge=1, le=365)
    interview_max_minutes: int = Field(default=30, ge=1, le=30)

    @field_validator("tls_cert_file", "tls_key_file", mode="before")
    @classmethod
    def empty_tls_path(cls, value):
        return None if value == "" else value

    @property
    def resolved_tavus_face_id(self) -> SecretStr | None:
        for value in (self.tavus_face_id, self.tavus_replica_id):
            if value and value.get_secret_value().strip():
                return value
        return None

    def missing_tavus_settings(self) -> list[str]:
        missing = [name.upper() for name in ("tavus_api_key", "tavus_pal_id")
                   if not (value := getattr(self, name)) or not value.get_secret_value().strip()]
        if self.resolved_tavus_face_id is None:
            missing.append("TAVUS_FACE_ID")
        return missing

    def missing_secrets(self, *, realtime: bool = False) -> list[str]:
        """Return names only; offline tests need no secrets or service calls."""
        required = ["admin_api_key", "ip_hash_secret"]
        if realtime:
            required.append("anthropic_api_key")
            if self.tts_provider == "openai" or self.stt_provider == "openai":
                required.append("openai_api_key")
            if self.avatar_mode == "tavus":
                required.extend(["tavus_api_key", "tavus_pal_id"])
        missing = [name.upper() for name in required if not (value := getattr(self, name)) or not value.get_secret_value().strip()]
        if realtime and self.avatar_mode == "tavus" and self.resolved_tavus_face_id is None:
            missing.append("TAVUS_FACE_ID")
        return missing
