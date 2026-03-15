
import json
import os
from dotenv import load_dotenv
from google import genai


load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"
OUTPUT_PATH = "llm-request/data/extracted_wiki_data_responses.json"


def save_results(results):
    temp_path = f"{OUTPUT_PATH}.tmp"
    with open(temp_path, "w") as f:
        json.dump(results, f, indent=2)
    os.replace(temp_path, OUTPUT_PATH)


with open("data-assembly/json/final_data.json", "r") as f:
    conferences_data = json.load(f)

with open("llm-request/prompts/extract_wiki_data_prompt.md", "r") as f:
    extract_wiki_data_prompt = f.read()




# extract relevant fields and reformat for easier use in LLM prompting
formatted_conferences = {}
for conf_name, conf_data in conferences_data.items():

    member_schools = conf_data.get("member_schools") or []
    conference_history = conf_data.get("conference_history") or []
    timeline_map = conf_data.get("timeline_map") or {}

    member_school_text = (
        member_schools[0].get("content")
        if member_schools and isinstance(member_schools[0], dict)
        else None
    )

    conference_history_text = (
        conference_history[0].get("content")
        if conference_history and isinstance(conference_history[0], dict)
        else None
    )

    timeline_map_text = (
        timeline_map.get("map_text")
        if timeline_map and isinstance(timeline_map, dict)
        else None
    )


    formatted_conferences[conf_name] = {
        "name": conf_data.get("name"),
        "member_schools": member_school_text,
        "conference_history": conference_history_text,
        "timeline_map": timeline_map_text,
    }




# loop over the formatted conferences, submitting to LLM and saving the response for each. Use the extract_wiki_data_prompt.md
# as part of the prompt alongside the information in formatted_conferences. Save results to a json file as you go, so you can
# pick up where you left off if needed. Also save any failed attempts with error messages for later review.
if os.path.exists(OUTPUT_PATH):
    with open(OUTPUT_PATH, "r") as f:
        responses = json.load(f)
else:
    responses = {}




for conf_name, conf_data in formatted_conferences.items():
    if conf_name in responses and isinstance(responses[conf_name], dict) and "error" not in responses[conf_name]:
        print(f"Skipping {conf_name}; already processed")
        continue

    content = [
        extract_wiki_data_prompt,
        json.dumps(conf_data, indent=2)
    ]


    try:
        response = client.chat.completions.create(
            model=model,
            content=content
        )
        responses[conf_name] = {
            "response_text": response.text,
            "error": None,
            "metadata": response.metadata
        }
        save_results(responses)
        print(f"Processed {conf_name}")
    except Exception as e:
        responses[conf_name] = {"error": str(e), "metadata": None}
        save_results(responses)
        print(f"Failed to process {conf_name}: {e}")




