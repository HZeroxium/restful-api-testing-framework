import os
from openai import OpenAI
from llm.llm_interface import LLMInterface


class OpenAICaller(LLMInterface):
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def send_prompt(
        self, prompt: str, system: str = "", temperature=0.2, top_p=0.9, max_tokens=-1
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens > 0:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
