import json
import pandas as pd

with open("data-assembly/json/final_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

top_level_keys = list(data.keys())
print(top_level_keys)


with open("llm-request/conferences_with_links.csv", "r") as f:
    conferences = pd.read_csv(f)

conference_titles = list(conferences["name"])

not_found_in_final_data = [title for title in conference_titles if title not in top_level_keys]

print(f"Not found in final data: {not_found_in_final_data}")