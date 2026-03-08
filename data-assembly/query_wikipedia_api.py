import requests, json, time
import pandas as pd
from urllib.parse import quote_plus, unquote, urlparse


S = requests.Session()
S.headers.update(
    {
        "User-Agent": "university-conferences/0.1 (contact: example@example.com)",
        "Accept": "application/json",
    }
)
API = "https://en.wikipedia.org/w/api.php"



with open("data-assembly/conferences.csv", "r") as f:
    conferences = pd.read_csv(f)


conference_titles = list(conferences["name"])



def get_page_metadata(title):
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "redirects": 1,
        "titles": title,
        "prop": "info|pageprops",
        "inprop": "url",
    }
    r = S.get(API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        raise ValueError(f"No page metadata returned for '{title}'")

    page = pages[0]
    if page.get("missing"):
        raise ValueError(f"No Wikipedia page found for '{title}'")

    pageprops = page.get("pageprops", {})
    is_disambiguation = "disambiguation" in pageprops
    return {
        "title": page.get("title", title),
        "fullurl": page.get("fullurl"),
        "is_disambiguation": is_disambiguation,
    }


def search_specific_conference_title(title):
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "list": "search",
        "srlimit": 10,
        "srsearch": f'{title} NCAA conference',
    }
    r = S.get(API, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = data.get("query", {}).get("search", [])

    for result in results:
        candidate_title = result.get("title")
        if not candidate_title:
            continue
        metadata = get_page_metadata(candidate_title)
        if not metadata["is_disambiguation"]:
            return metadata

    raise ValueError(f"No specific (non-disambiguation) page found for '{title}'")


def get_page_html(title):
    metadata = get_page_metadata(title)
    if metadata["is_disambiguation"]:
        metadata = search_specific_conference_title(title)

    resolved_title = metadata["title"]
    params = {
        "action": "parse",
        "format": "json",
        "formatversion": 2,
        "page": resolved_title,
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
            f"Unexpected response for '{resolved_title}'. Top-level keys: {list(data.keys())}"
        )

    return {
        "html": parse_data["text"],
        "resolved_title": resolved_title,
        "resolved_url": metadata["fullurl"],
        "resolved_via_search": metadata["title"] != title,
    }


def get_title_from_wikipedia_url(url):
    slug = urlparse(url).path.split("/wiki/")[-1]
    return unquote(slug).replace("_", " ")


def build_manual_search_url(title):
    return f"https://en.wikipedia.org/w/index.php?search={quote_plus(title)}"



# breakpoint()  # inspect titles before query


conf_info = {}
for title in conference_titles:
    time.sleep(1)  # be nice to the API
    try:
        result = get_page_html(title)
        html = result["html"]
        print(f"{title}: {len(html)} chars")
        print(html[:300], "...")
        conf_info[title] = {
            "status": "ok",
            "html": html,
            "error": None,
            "manual_search_url": build_manual_search_url(title),
            "resolved_title": result["resolved_title"],
            "resolved_url": result["resolved_url"],
            "resolved_via_search": result["resolved_via_search"],
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



# initially failed conferences in search with corrected links:
correct_links = {
    "BIG EAST Conference": "https://en.wikipedia.org/wiki/Big_East_Conference",
    "Empire 8 Conference": "https://en.wikipedia.org/wiki/Empire_8",
    "New England Womens and Mens Athletic Conference": "https://en.wikipedia.org/wiki/New_England_Women%27s_and_Men%27s_Athletic_Conference",
    "Presidents Athletic Conference": "https://en.wikipedia.org/wiki/Presidents%27_Athletic_Conference",
}


for conference_name, corrected_url in correct_links.items():
    existing_entry = conf_info.get(conference_name)
    if existing_entry and existing_entry.get("status") == "ok":
        continue

    corrected_title = get_title_from_wikipedia_url(corrected_url)
    time.sleep(1)
    try:
        result = get_page_html(corrected_title)
        html = result["html"]
        print(f"Recovered {conference_name} using corrected link")
        conf_info[conference_name] = {
            "status": "ok",
            "html": html,
            "error": None,
            "manual_search_url": build_manual_search_url(conference_name),
            "resolved_via": "corrected_link",
            "corrected_url": corrected_url,
            "resolved_title": result["resolved_title"],
            "resolved_url": result["resolved_url"],
            "resolved_via_search": result["resolved_via_search"],
        }
    except (requests.RequestException, ValueError) as error:
        print(f"Still failed for {conference_name}: {error}")
        conf_info[conference_name] = {
            "status": "failed",
            "html": None,
            "error": str(error),
            "manual_search_url": build_manual_search_url(conference_name),
            "resolved_via": "corrected_link_attempt_failed",
            "corrected_url": corrected_url,
        }


with open("data-assembly/json/conference_wikipedia_html.json", "w") as f:
    json.dump(conf_info, f, indent=2)

