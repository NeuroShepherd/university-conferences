
# Send a request to Google Gemini to design a database schema for storing information 
# about university conferences and their member institutions. This file will only contain
# the code for sending the request and receiving the response, and will not contain any
# code for parsing the response or storing the data in a database. Nor will it contain
# the prompt used to generate the response, which will be stored in a separate file 
# for better organization.


import os
from dotenv import load_dotenv
from google import genai
import random, json


load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model="gemini-2.5-flash"



with open("data-assembly/json/final_data.json", "r") as f:
    conferences = json.load(f)




sampled_keys = random.sample(list(conferences.keys()), 10)
sample_conferences = {k: conferences[k] for k in sampled_keys}

for conf in sample_conferences.values():
    # Remove from member_schools
    for school in conf.get("member_schools", []):
        school.pop("h2", None)
        school.pop("content_length", None)
    # Remove from conference_history
    for hist in conf.get("conference_history", []):
        hist.pop("h2", None)
        hist.pop("content_length", None)
    # Remove from timeline_map
    if "timeline_map" in conf:
        conf["timeline_map"].pop("edit_url", None)





with open("llm-request/database_design_prompt.md", "r") as f:
    prompt = f.read()

content = [
    prompt,
    json.dumps(sample_conferences, indent=2)
]

response = client.models.generate_content(
    model=model,
    contents=content
)

if response.usage_metadata is not None:
    print(f"Total tokens:    {response.usage_metadata.total_token_count}")

with open("llm-request/database_design_response.md", "w") as f:
    f.write(response.text)