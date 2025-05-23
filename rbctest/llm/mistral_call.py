import os
import requests
from dotenv import load_dotenv
from llm.llm_interface import LLMInterface

load_dotenv()


class MistralCaller(LLMInterface):
    def __init__(self):
        self.api_key = os.getenv("HF_API_KEY")
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
        print(self.api_key)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def send_prompt(
        self, prompt: str, system: str = "", temperature=0.2, top_p=0.9, max_tokens=-1
    ) -> str:
        payload = {
            "inputs": f"<s>[INST] {prompt} [/INST]",
            "parameters": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }

        if max_tokens > 0:
            payload["parameters"]["max_tokens"] = max_tokens

        response = requests.post(self.api_url, headers=self.headers, json=payload)

        if response.status_code == 200:
            generated_text = response.json()[0]["generated_text"]
            return generated_text.strip()
        return f"[Error] {response.status_code}: {response.text}"


if __name__ == "__main__":
    mistral = MistralCaller()
    result = mistral.send_prompt("What is the capital of Vietnam?")
    print(result)
