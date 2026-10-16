"""Application settings.

Runtime configuration. LLM credentials are intentionally absent from round 1
(LLM advisory is a planned milestone). Auth is local-only demo by default; see
README security notes. Environment variables are non-secret defaults only.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "tensor-forge"
    app_version: str = "1.0.0"
    environment: str = "development"

    # SQLite persistence (relative to backend dir by default).
    database_url: str = "sqlite:///./tensor-forge.db"

    # Local-only demo mode. In production the controller refuses to start the
    # default demo binding; operators set DEMO_MODE=false and mount TLS.
    demo_mode: bool = True
    host: str = "127.0.0.1"
    port: int = 8000


settings = Settings()