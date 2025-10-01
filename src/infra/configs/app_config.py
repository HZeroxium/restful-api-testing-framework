# infra/configs/app_config.py

from pydantic_settings import BaseSettings
from typing import Optional


class AppSettings(BaseSettings):
    """Application settings."""

    # Application info
    app_name: str = "RESTful API Testing Framework"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database/Repository settings
    endpoints_file_path: str = "data/endpoints.json"
    constraints_file_path: str = "data/constraints.json"
    validation_scripts_file_path: str = "data/validation_scripts.json"

    # LLM settings
    llm_provider: str = "openai"
    llm_model: str = "gemini-2.0-flash"
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Caching settings
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = AppSettings()
