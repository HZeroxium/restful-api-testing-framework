import os
from openai import OpenAI
from llm.llm_interface import LLMInterface
from dotenv import load_dotenv


class OpenAICaller:
    def __init__(self):
        load_dotenv(
            dotenv_path="/media/aaronpham5504/New Volume/Research/restful-api-testing-framework/rbctest/llm/.env"
        )
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)

    def send_prompt(
        self, prompt: str, system: str = "", temperature=0.2, top_p=0.9, max_tokens=-1
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": "gpt-4-turbo",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens > 0:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
