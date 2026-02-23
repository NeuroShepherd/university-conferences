import json
from urllib.parse import parse_qs, urlparse

import requests


API = "https://en.wikipedia.org/w/api.php"
SESSION = requests.Session()
SESSION.headers.update(
	{
		"User-Agent": "university-conferences/0.1 (contact: example@example.com)",
		"Accept": "application/json",
	}
)


with (open("data-assembly/json/conference_timeline_map_edit_links.json", "r", encoding="utf-8") as f):
    json_data = json.load(f)
	


conference_maps = [{"conference": item["conference"], "edit_url": item["edit_url"]} for item in json_data]




def parse_edit_url(url: str) -> tuple[str, str]:
	parsed = urlparse(url)
	query = parse_qs(parsed.query)
	title = query.get("title", [None])[0]
	section = query.get("section", [None])[0]
	if not title or not section:
		raise ValueError("Edit URL is missing required title/section query params")
	return title, section


def fetch_section_wikitext(title: str, section: str) -> str:
	params = {
		"action": "parse",
		"format": "json",
		"formatversion": 2,
		"page": title,
		"prop": "wikitext",
		"section": section,
	}
	response = SESSION.get(API, params=params, timeout=30)
	response.raise_for_status()
	payload = response.json()
	if "error" in payload:
		raise ValueError(payload["error"].get("info", "Unknown API error"))

	return payload.get("parse", {}).get("wikitext", "")


	
for url in conference_maps:
    title, section = parse_edit_url(url["edit_url"])
    wikitext = fetch_section_wikitext(title, section)
    print(f"=== {url['conference']} ===")
    print(wikitext)
    print("\n\n")
    url["membership_map_wikitext"] = wikitext


with open("data-assembly/json/conference_timeline_map_edit_links_with_wikitext.json", "w", encoding="utf-8") as f:
    json.dump(conference_maps, f, indent=2, ensure_ascii=False)




