# # llm/providers/groq.py

from typing import Optional

from langchain_groq import ChatGroq

from llm.base_client import BaseLLMClient
from llm.config import GroqConfig, load_config_from_env


class GroqCaller(BaseLLMClient):
    """Groq implementation of LLM client using LangChain"""

    def __init__(
        self, config: Optional[GroqConfig] = None, dotenv_path: Optional[str] = None
    ):
        """
        Initialize the Groq caller

        Args:
            config: Groq configuration, if None will load from environment
            dotenv_path: Path to .env file, if needed
        """
        if config is None:
            loaded_config = load_config_from_env(dotenv_path)
            if loaded_config.groq is None:
                raise ValueError(
                    "Groq configuration not found in environment variables"
                )
            config = loaded_config.groq

        model = ChatGroq(
            api_key=config.api_key,
            model_name=config.model,
        )

        super().__init__(model)
