
# This script will be the first approach to extracting conference data from Wikipedia.


import json
import os
from dotenv import load_dotenv
from google import genai



load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"

OUTPUT_PATH = "llm-request/extracted_data_responses.json"


def to_json_safe(value):
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "dict"):
        return value.dict()

    return value


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

if os.path.exists(OUTPUT_PATH):
    with open(OUTPUT_PATH, "r") as f:
        all_results = json.load(f)
else:
    all_results = {}


for conf_name, conf_data in conferences_data.items():
    content = [
        database_design_notes,
        prompt,
        json.dumps(conf_data, indent=2)
    ]

    response = client.models.generate_content(
        model=model,
        contents=content
    )

    all_results[conf_name] = {
        "conf_name": conf_name,
        "response_text": response.text,
        "usage_metadata": to_json_safe(response.usage_metadata),
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"Processed {conf_name}")

