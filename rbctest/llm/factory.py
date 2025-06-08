# llm/factory.py

from typing import Literal, Optional

from llm.interface import LLMClient
from llm.config import LLMConfig, load_config_from_env
from llm.providers.openai import OpenAICaller
from llm.providers.gemini import GeminiCaller
from llm.providers.groq import GroqCaller


def create_llm_client(
    provider: Optional[Literal["openai", "gemini", "groq", "anthropic"]] = None,
    config: Optional[LLMConfig] = None,
    dotenv_path: Optional[str] = None,
) -> LLMClient:
    """
    Create an LLM client based on provider

    Args:
        provider: LLM provider to use, if None will use default from config
        config: Configuration to use, if None will load from environment
        dotenv_path: Path to .env file, if needed

    Returns:
        An instance of LLMClient implementation
    """
    if config is None:
        config = load_config_from_env(dotenv_path)

    if provider is None:
        provider = config.default_provider

    if provider == "openai":
        if config.openai is None:
            raise ValueError("OpenAI configuration not found")
        return OpenAICaller(config=config.openai)

    elif provider == "gemini":
        if config.gemini is None:
            raise ValueError("Gemini configuration not found")
        return GeminiCaller(config=config.gemini)

    elif provider == "groq":
        if config.groq is None:
            raise ValueError("Groq configuration not found")
        return GroqCaller(config=config.groq)

    elif provider == "anthropic":
        # Implement if needed
        raise NotImplementedError("Anthropic provider not implemented yet")

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
