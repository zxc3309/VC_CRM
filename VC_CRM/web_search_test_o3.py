from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from openai import OpenAI
client = OpenAI()
prompt = """
Please provide a verified biography of **David Low**(including career history, education background, founder journey), founder of **Hata Technologies Pte Ltd**. Please search for the profile using keywords "David Low"&"Hata Technologies Pte Ltd". 
Avoid confusing with other people named David Low.
"""
response = client.responses.create(
    model="o3-pro",
    input=[
        {
        "role": "user",
        "content": prompt
        }
    ],
    reasoning={
        "effort": "medium",  # 請求的推理強度（影響推論精度與搜尋範圍）
        "summary": "auto"   # 自動摘要查得內容
    },
    store=True  # 將這次請求與結果存到使用者帳號下的歷史中（若支援）
    # temperature=0  # 如果 API 支援
)
print(response.output_text)

