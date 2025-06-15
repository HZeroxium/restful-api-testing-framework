# llm/providers/gemini.py

from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from llm.base_client import BaseLLMClient
from llm.config import GeminiConfig, load_config_from_env


class GeminiCaller(BaseLLMClient):
    """Google Gemini implementation of LLM client using LangChain"""

    def __init__(
        self, config: Optional[GeminiConfig] = None, dotenv_path: Optional[str] = None
    ):
        """
        Initialize the Gemini caller

        Args:
            config: Gemini configuration, if None will load from environment
            dotenv_path: Path to .env file, if needed
        """
        if config is None:
            loaded_config = load_config_from_env(dotenv_path)
            if loaded_config.gemini is None:
                raise ValueError(
                    "Gemini configuration not found in environment variables"
                )
            config = loaded_config.gemini

        model = ChatGoogleGenerativeAI(
            google_api_key=config.api_key,
            model=config.model,
        )

        super().__init__(model)
