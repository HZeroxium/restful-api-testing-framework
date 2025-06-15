# config/settings.py

from typing import Optional
from pydantic_settings import BaseSettings


class LlmSettings(BaseSettings):
    """Settings for LLM models."""

    # LLM provider and model settings
    LLM_PROVIDER: str = "openai"  # Options: openai, google, anthropic
    LLM_MODEL: str = "gemini-2.0-flash"  # Default model

    # API keys for different providers
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Inference parameters
    # TEMPERATURE: float = 0.0  # Low temperature for more deterministic outputs
    # MAX_TOKENS: int = 4096

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class Settings(BaseSettings):
    """Global application settings."""

    # Application info
    APP_NAME: str = "RESTful API Testing Framework"
    APP_VERSION: str = "0.1.0"

    # Debug mode
    DEBUG: bool = False

    # LLM Settings
    llm: LlmSettings = LlmSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create global settings instance
settings = Settings()
