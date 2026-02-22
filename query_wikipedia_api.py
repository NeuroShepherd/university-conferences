import requests, json, time
import pandas as pd
from urllib.parse import quote_plus


S = requests.Session()
S.headers.update(
    {
        "User-Agent": "university-conferences/0.1 (contact: example@example.com)",
        "Accept": "application/json",
    }
)
API = "https://en.wikipedia.org/w/api.php"



with open("conferences.csv", "r") as f:
    conferences = pd.read_csv(f)


conference_titles = list(conferences["name"])



def get_page_html(title):
    params = {
        "action": "parse",
        "format": "json",
        "formatversion": 2,
        "page": title,
        "prop": "text",
        "redirects": 1,
    }
    r = S.get(API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        code = data["error"].get("code", "unknown")
        info = data["error"].get("info", "No details provided")
        raise ValueError(f"Wikipedia API error for '{title}': {code} - {info}")

    parse_data = data.get("parse")
    if not parse_data or "text" not in parse_data:
        raise ValueError(
            f"Unexpected response for '{title}'. Top-level keys: {list(data.keys())}"
        )

    return parse_data["text"]


def build_manual_search_url(title):
    return f"https://en.wikipedia.org/w/index.php?search={quote_plus(title)}"



# breakpoint()  # inspect titles before query


conf_info = {}
for title in conference_titles:
    time.sleep(1)  # be nice to the API
    try:
        html = get_page_html(title)
        print(f"{title}: {len(html)} chars")
        print(html[:300], "...")
        conf_info[title] = {
            "status": "ok",
            "html": html,
            "error": None,
            "manual_search_url": build_manual_search_url(title),
        }
    except (requests.RequestException, ValueError) as error:
        print(f"Failed for {title}: {error}")
        conf_info[title] = {
            "status": "failed",
            "html": None,
            "error": str(error),
            "manual_search_url": build_manual_search_url(title),
        }



with open("conference_wikipedia_html.json", "w") as f:
    json.dump(conf_info, f, indent=2)