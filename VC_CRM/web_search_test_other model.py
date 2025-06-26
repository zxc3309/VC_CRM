from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from openai import OpenAI
client = OpenAI()
prompt = """
Please provide a verified biography of **David Low**(including career history, education background, founder journey), founder of **Hata Technologies Pte Ltd**, based in Singapore. Please search for the profile using keywords "David Low"&"Hata Technologies Pte Ltd". 
Avoid confusing with other people named David Low.
"""

response = client.responses.create(
  model="o3-pro",
  input=[{"role": "user", "content": prompt}],
  tools=[{
        "type": "web_search",
        "search_context_size": "medium"
        }],
  temperature=0,
  top_p=1,
  store=False
)
print(response.output_text)
