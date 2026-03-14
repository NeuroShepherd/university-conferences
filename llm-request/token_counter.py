import json, os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
model = "gemini-2.5-flash"

with open("llm-request/extracted_data_responses.json") as f:
    data = json.load(f)

total = 0

for conf_name, payload in data.items():
    text = payload.get("sql_text") or ""
    result = client.models.count_tokens(
        model=model,
        contents=text,
    )
    print(conf_name, result.total_tokens)
    total += result.total_tokens

print("TOTAL", total)