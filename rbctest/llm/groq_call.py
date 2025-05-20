from groq import Groq
import os
from llm.llm_interface import LLMInterface
from dotenv import load_dotenv

load_dotenv()


class GroqCaller(LLMInterface):
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL")

    def send_prompt(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = -1,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if max_tokens > 0:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


if __name__ == "__main__":
    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")
    print(key)
    print(model)
