from openai import AzureOpenAI
import os
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Khởi tạo client Azure OpenAI
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

client = AzureOpenAI(
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_KEY,
)

# Setup log folder
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "azure_gpt_output.log"

def log_to_file(content: str):
    """Ghi log ra file với timestamp"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] {content}\n")


def GPTChatCompletion(prompt, system="", model='gpt-4.1', temperature=0, top_p=1, max_tokens=-1):
    """
    Hàm giữ nguyên interface cũ nhưng chạy bằng Azure OpenAI.
    - model: chính là tên deployment trên Azure (vd: 'gpt-4.1-deploy')
    - max_tokens=-1 nghĩa là để API tự quyết định (None)
    """
    if system:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    else:
        messages = [
            {"role": "user", "content": prompt}
        ]

    while True:
        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p
            )
            if max_tokens != -1:
                kwargs["max_tokens"] = max_tokens

            response = client.chat.completions.create(**kwargs)
            output = response.choices[0].message.content


            return output

        except Exception as e:
            log_to_file(f"[AzureOpenAI Error] {e}")
            print(f"[AzureOpenAI Error] {e}")
            time.sleep(10)
