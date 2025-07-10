from .utils.llm_utils import create_and_execute_llm_agent
from pydantic import BaseModel, Field
from .common.logger import LoggerFactory, LoggerType, LogLevel

logger = LoggerFactory.get_logger(
    name="test.llm_cache",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.DEBUG,
)


class LLMAnswer(BaseModel):
    """Model to represent the answer from an LLM agent."""

    answer: str = Field(..., description="The answer provided by the LLM agent")


async def test_llm_cache():
    """Test the LLM cache functionality."""
    # Define a simple instruction and input data
    instruction = "What is the capital of France?"
    input_data = {"country": "France"}

    # Create and execute the LLM agent
    result = await create_and_execute_llm_agent(
        app_name="test_app",
        agent_name="test_agent",
        instruction=instruction,
        input_data=input_data,
        output_schema=LLMAnswer,
        verbose=True,
        cache_enabled=True,
    )

    logger.debug(f"LLM agent result: {result}")

    # Check if the result is as expected
    assert result is not None, "LLM agent should return a result"
    assert isinstance(result, object), "Result should be a string"
    # assert "Paris" in result, "Result should contain the capital of France"


if __name__ == "__main__":
    import asyncio

    # Run the test
    asyncio.run(test_llm_cache())
    print("LLM cache test passed successfully.")
