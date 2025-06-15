# llm/providers/openai.py

from typing import Optional

from langchain_openai import ChatOpenAI

from llm.base_client import BaseLLMClient
from llm.config import OpenAIConfig, load_config_from_env


class OpenAICaller(BaseLLMClient):
    """OpenAI implementation of LLM client using LangChain"""

    def __init__(
        self, config: Optional[OpenAIConfig] = None, dotenv_path: Optional[str] = None
    ):
        """
        Initialize the OpenAI caller

        Args:
            config: OpenAI configuration, if None will load from environment
            dotenv_path: Path to .env file, if needed
        """
        if config is None:
            loaded_config = load_config_from_env(dotenv_path)
            if loaded_config.openai is None:
                raise ValueError(
                    "OpenAI configuration not found in environment variables"
                )
            config = loaded_config.openai

        model = ChatOpenAI(
            api_key=config.api_key,
            model_name=config.model,
            base_url=config.base_url,
        )

        super().__init__(model)
