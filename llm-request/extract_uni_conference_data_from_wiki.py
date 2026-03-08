
# This script will be the first approach to extracting conference data from Wikipedia. 


import os, random, json
import pandas as pd
from dotenv import load_dotenv
from google import genai



load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model="gemini-2.5-flash"


with open("data-assembly/json/final_data.json", "r") as f:
    conferences_data = json.load(f)


for conf in conferences_data.values():
    # Remove fields from each dict in member_schools (list of dicts)
    if "member_schools" in conf:
        for school in conf["member_schools"]:
            school.pop("content_length", None)
            school.pop("h2", None)
    # Remove fields from each dict in conference_history (list of dicts)
    if "conference_history" in conf:
        for hist in conf["conference_history"]:
            hist.pop("content_length", None)
            hist.pop("h2", None)
    # Remove edit_url from timeline_map (dict)
    if "timeline_map" in conf and isinstance(conf["timeline_map"], dict):
        conf["timeline_map"].pop("edit_url", None)




with open("llm-request/extract_data_wiki_prompt.md", "r") as f:
    prompt = f.read()

with open("llm-request/database_design_response.md", "r") as f:
    database_design_notes = f.read()




# testing round

first_key, first_value = next(iter(conferences_data.items()))

content = [
    database_design_notes,
    prompt,
    json.dumps(first_value, indent=2)
]

response = client.models.generate_content(
    model=model,
    contents=content
)

print(response.text)

# save response to file
with open("llm-request/extracted_data_response_TEST.md", "w") as f:
    f.write(response.text)