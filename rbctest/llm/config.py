# llm/config.py

from pydantic import BaseModel, Field
from typing import Dict, Optional, Union, Literal


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI models"""

    api_key: str
    model: str = Field(default="gpt-4o-mini")
    base_url: Optional[str] = None


class GeminiConfig(BaseModel):
    """Configuration for Google Gemini models"""

    api_key: str
    model: str = Field(default="gemini-2.0-flash")


class GroqConfig(BaseModel):
    """Configuration for Groq models"""

    api_key: str
    model: str = Field(default="mixtral-8x7b-32768")


class AnthropicConfig(BaseModel):
    """Configuration for Anthropic models"""

    api_key: str
    model: str = Field(default="claude-3-opus-20240229")


class LLMConfig(BaseModel):
    """Global LLM configuration"""

    default_provider: Literal["openai", "gemini", "groq", "anthropic"] = "openai"
    openai: Optional[OpenAIConfig] = None
    gemini: Optional[GeminiConfig] = None
    groq: Optional[GroqConfig] = None
    anthropic: Optional[AnthropicConfig] = None


def load_config_from_env(dotenv_path: Optional[str] = None) -> LLMConfig:
    """Load LLM configuration from environment variables"""
    import os
    from dotenv import load_dotenv

    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
    else:
        load_dotenv()

    configs = {}

    # OpenAI config
    if os.getenv("OPENAI_API_KEY"):
        configs["openai"] = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

    # Gemini config
    if os.getenv("GOOGLE_API_KEY"):
        configs["gemini"] = GeminiConfig(
            api_key=os.getenv("GOOGLE_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro-preview-03-25"),
        )

    # Groq config
    if os.getenv("GROQ_API_KEY"):
        configs["groq"] = GroqConfig(
            api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
        )

    # Anthropic config
    if os.getenv("ANTHROPIC_API_KEY"):
        configs["anthropic"] = AnthropicConfig(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
        )

    # Determine default provider
    default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    if default_provider not in configs:
        # Fall back to the first available provider
        default_provider = next(iter(configs.keys())) if configs else "openai"

    return LLMConfig(default_provider=default_provider, **configs)
