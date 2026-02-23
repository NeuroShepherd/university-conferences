

import json


with open("data-assembly/json/conference_timeline_map_edit_links_with_wikitext.json", "r", encoding="utf-8") as f:
    timeline_maps = json.load(f)

with open("data-assembly/json/conference_relevant_sections.json", "r", encoding="utf-8") as f:
    relevant_sections = json.load(f)



output = {}
for result in timeline_maps:
    output[result["conference"]] = relevant_sections[result["conference"]]
    output[result["conference"]]["timeline_map"] = {
        "map_text": result["membership_map_wikitext"],
        "edit_url": result["edit_url"],
        }
    
with open("data-assembly/json/final_data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)



# check number of timeline maps against total conferences
print(f"Total conferences: {len(relevant_sections)}")
print(f"Timeline maps found: {len(timeline_maps)}")