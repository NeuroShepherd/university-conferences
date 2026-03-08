
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
EXPECTED_RESPONSE_KEYS = ["notes", "commands", "text_description"]


def to_json_safe(value):
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "dict"):
        return value.dict()

    return value


def parse_response_json(response_text):
    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        lines = cleaned_text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned_text = "\n".join(lines).strip()

    parsed = json.loads(cleaned_text)

    if not isinstance(parsed, dict):
        raise ValueError("response.text did not parse to a JSON object")

    missing_keys = [key for key in EXPECTED_RESPONSE_KEYS if key not in parsed]
    if missing_keys:
        raise ValueError(f"response.text is missing expected keys: {missing_keys}")

    return {
        "notes": parsed.get("notes", []),
        "commands": parsed.get("commands", []),
        "text_description": parsed.get("text_description", []),
    }


def is_completed_result(result):
    if not isinstance(result, dict):
        return False

    parsed_response = result.get("parsed_response")
    if not isinstance(parsed_response, dict):
        return False

    return all(key in parsed_response for key in EXPECTED_RESPONSE_KEYS)


def save_results(all_results):
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_results, f, indent=2)


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
    existing_result = all_results.get(conf_name)
    if is_completed_result(existing_result):
        print(f"Skipping {conf_name}; already processed")
        continue

    content = [
        database_design_notes,
        prompt,
        json.dumps(conf_data, indent=2)
    ]

    response = None

    try:
        response = client.models.generate_content(
            model=model,
            contents=content
        )

        parsed_response = parse_response_json(response.text)

        all_results[conf_name] = {
            "conf_name": conf_name,
            "response_text": response.text,
            "parsed_response": parsed_response,
            "usage_metadata": to_json_safe(response.usage_metadata),
            "error": None,
        }

        save_results(all_results)
        print(f"Processed {conf_name}")

    except Exception as exc:
        all_results[conf_name] = {
            "conf_name": conf_name,
            "response_text": None if response is None else response.text,
            "parsed_response": None,
            "usage_metadata": None if response is None else to_json_safe(response.usage_metadata),
            "error": str(exc),
        }

        save_results(all_results)
        print(f"Failed {conf_name}: {exc}")

