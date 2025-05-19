import google.generativeai as genai
import os
from llm.llm_interface import LLMInterface
from dotenv import load_dotenv

load_dotenv()


class GeminiCaller(LLMInterface):
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel("gemini-pro")

    def send_prompt(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_tokens: int = -1,
    ) -> str:
        generation_config = {
            "temperature": temperature,
            "top_p": top_p,
        }
        if max_tokens > 0:
            generation_config["max_output_tokens"] = max_tokens

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )

        return response.text


if __name__ == "__main__":
    key = os.getenv("GOOGLE_API_KEY")
    print(key)
