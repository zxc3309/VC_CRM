from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

resp = client.responses.create(
    model="o3",                     # 完整版 o3
    input="台積電 ADR 今天收盤多少？",
    tools=[{"type": "web_search"}]  # 只用正式名稱
)
print(resp.content)