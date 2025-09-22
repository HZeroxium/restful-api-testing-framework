from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),  # key lấy từ Azure Portal
    api_version="2024-02-01",               # version hiện tại
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  # vd: https://your-resource-name.openai.azure.com/
)
