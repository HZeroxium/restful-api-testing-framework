import json
import os
import uuid
from hashlib import md5
from llm.providers.openai import OpenAICaller

from llm.providers.gemini import GeminiCaller

llm_clients = {
    "openai": OpenAICaller(),
    "gemini": GeminiCaller(),
}


def post_processing(response: str) -> str:
    """
    This function use to parse Groovy code snippet

    Args:
        response (str): Response to be parsed

    Returns:
        str: Parse Groovy code
    """
    # Extract the code between ```groovy and ```
    if "```groovy" not in response:
        return response
    return response.split("```groovy")[1].split("```")[0]


def store_response(prompt: str, response: str) -> None:
    """
    This function use to store the response to a file

    Args:
        prompt (str): Prompt to be stored
        response (str): Response to be stored
    """
    uuid_str = str(uuid.uuid4())
    gpt_response_folder = "gpt_response"
    os.makedirs(gpt_response_folder, exist_ok=True)
    file_name = f"{gpt_response_folder}/api_response_{uuid_str}.json"
    with open(file_name, "w") as f:
        json.dump(
            {
                "prompt": prompt,
                "response": response,
                "prompt_hash": md5(prompt.encode()).hexdigest(),
            },
            f,
        )


def find_previous_response(prompt: str) -> str:
    """
    This function use to find the previous response for a prompt

    Args:
        prompt (str): Prompt to be found

    Returns:
        str: Previous response
    """
    gpt_response_folder = "gpt_response"
    if not os.path.exists(gpt_response_folder):
        return None  # type: ignore
    for file in os.listdir(gpt_response_folder):
        with open(f"{gpt_response_folder}/{file}", "r") as f:
            data = json.load(f)
            if data["prompt_hash"] == md5(prompt.encode()).hexdigest():
                return data["response"]
    return None  # type: ignore


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "groq",
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_tokens: int = -1,
) -> str:
    previous_response = find_previous_response(prompt)
    if previous_response:
        return previous_response

    if model not in llm_clients:
        raise ValueError(f"Unsupported model: {model}")

    response = llm_clients[model].send_prompt(
        prompt=prompt,
        system=system,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

    store_response(prompt, response)
    return response
