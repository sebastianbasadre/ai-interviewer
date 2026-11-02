"""Explicit, side-effect-free settings loading. Never log this model."""
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_mode: Literal["mock", "real"] = "mock"
    privacy_contact: str = ""

    anthropic_api_key: SecretStr | None = Field(default=None, repr=False)
    openai_api_key: SecretStr | None = Field(default=None, repr=False)
    tavus_api_key: SecretStr | None = Field(default=None, repr=False)
    tavus_replica_id: SecretStr | None = Field(default=None, repr=False)
    admin_api_key: SecretStr | None = Field(default=None, repr=False)
    ip_hash_secret: SecretStr | None = Field(default=None, repr=False)
    conversation_model: str = "claude-haiku-5-5"
    scoring_model: str = "claude-opus-5-5"
    tts_provider: Literal["openai", "piper"] = "openai"
    stt_provider: Literal["whisper_local", "openai"] = "whisper_local"
    whisper_model: str = "large-v3-turbo"
    whisper_device: Literal["cuda", "cpu"] = "cuda"
    avatar_mode: Literal["mock", "tavus"] = "mock"
    tavus_max_minutes_per_session: int = Field(default=30, ge=1, le=30)
    public_base_url: str = "http://localhost:8000"
    data_dir: Path = Path("data")
    retention_days: int = Field(default=30, ge=1, le=365)
    interview_max_minutes: int = Field(default=30, ge=1, le=30)

    def missing_secrets(self, *, realtime: bool = False) -> list[str]:
        """Return names only; offline tests need no secrets or service calls."""
        required = ["admin_api_key", "ip_hash_secret"]
        if realtime:
            required.append("anthropic_api_key")
            if self.tts_provider == "openai" or self.stt_provider == "openai":
                required.append("openai_api_key")
            if self.avatar_mode == "tavus":
                required.extend(["tavus_api_key", "tavus_replica_id"])
        return [name.upper() for name in required if not (value := getattr(self, name)) or not value.get_secret_value().strip()]
