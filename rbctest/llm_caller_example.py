# llm_caller_example.py

from typing import List
from pydantic import BaseModel, Field
from llm import create_llm_client, LLMRequest


# Simple example - get a text response
def simple_example():
    print("=== Simple Example ===")

    # Create a client with default provider (from environment)
    llm_client = create_llm_client()

    # Create a request
    request = LLMRequest(
        prompt="What are the three fundamental laws of robotics?",
        system_message="You are a helpful AI assistant specializing in science fiction literature.",
        temperature=0.2,
    )

    # Get a response
    response = llm_client.send_prompt(request)

    print(f"Response:\n{response.text}\n")


# Example with structured output
def structured_output_example():
    print("=== Structured Output Example ===")

    # Define an output schema
    class RoboticLaw(BaseModel):
        number: int = Field(..., description="The number of the law (1, 2, or 3)")
        description: str = Field(..., description="The full text of the law")
        explanation: str = Field(
            ..., description="A brief explanation of the law's purpose and implications"
        )

    class RoboticLaws(BaseModel):
        laws: List[RoboticLaw] = Field(..., description="The three laws of robotics")
        author: str = Field(..., description="The author who created these laws")
        source: str = Field(
            ..., description="The literary work where these laws first appeared"
        )

    # Create a client for this specific use case - using OpenAI explicitly
    llm_client = create_llm_client(provider="openai")

    # Create a request
    request = LLMRequest(
        prompt="List and explain Isaac Asimov's three laws of robotics.",
        system_message="You are a helpful AI assistant specializing in science fiction literature.",
        temperature=0.1,  # Lower temperature for more deterministic output
    )

    # Get a structured response
    response = llm_client.send_prompt_with_schema(request, RoboticLaws)

    print(f"Raw Response: {response}")

    print("Structured Response:")
    print(f"Author: {response.author}")
    print(f"Source: {response.source}")
    print("Laws:")
    for law in response.laws:
        print(f" - Law {law.number}: {law.description}")
        print(f"   Explanation: {law.explanation}")
    print()


# Example with different providers
def multi_provider_example():
    print("=== Multi-Provider Example ===")

    prompt = (
        "Explain the concept of gradient descent in machine learning in 2-3 sentences."
    )

    # Try with different providers
    for provider in ["openai", "gemini"]:
        try:
            print(f"\n--- {provider.upper()} ---")
            llm_client = create_llm_client(provider=provider)

            request = LLMRequest(prompt=prompt)
            response = llm_client.send_prompt(request)

            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error with {provider}: {e}")


if __name__ == "__main__":
    # Run all examples
    simple_example()
    structured_output_example()
    multi_provider_example()
