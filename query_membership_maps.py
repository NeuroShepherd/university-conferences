import json
from urllib.parse import parse_qs, urlparse

import requests


test_url = "https://en.wikipedia.org/w/index.php?title=Atlantic_Coast_Conference&action=edit&section=5"
API = "https://en.wikipedia.org/w/api.php"
SESSION = requests.Session()
SESSION.headers.update(
	{
		"User-Agent": "university-conferences/0.1 (contact: example@example.com)",
		"Accept": "application/json",
	}
)


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


def main() -> None:
	title, section = parse_edit_url(test_url)
	wikitext = fetch_section_wikitext(title, section)
	print(wikitext)


if __name__ == "__main__":
	main()

