

# Note: at the time of creation, this script is not strictly necessary, but it was used to identify 
# the correct Wikipedia links for the conferences that didn't have a direct match. It can be used 
# in the future if we want to expand our dataset to include more conferences and need to identify 
# the correct Wikipedia links for those conferences.


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

# check if the conference title directly matches a Wikipedia page
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


error_pages = []
for title in conference_titles:
    try:
        metadata = get_page_metadata(title)
        print(f"Found page for '{title}': {metadata['fullurl']}")
    except ValueError as e:
        print(f"Error for '{title}': {e}")
        error_pages.append(title)

print(error_pages)

# for the error pages, we want to substitute in the correct conference links by first identifying them manually, 
# then we can use those links to extract the correct Wikipedia page titles for each conference and update our dataset with the correct links.

correct_links = {
    "BIG EAST Conference": "Big_East_Conference",
    "Empire 8 Conference": "Empire_8",
    "New England Womens and Mens Athletic Conference": "New_England_Women%27s_and_Men%27s_Athletic_Conference",
    "Presidents Athletic Conference": "Presidents%27_Athletic_Conference",
}

# substitute in the correct links to the dataset
for title, link in correct_links.items():
    conferences.loc[conferences["name"] == title, "wiki_query_string"] = link

# use name for wiki_query_string for the conferences that had a direct match, and the correct link for the ones that didn't
conferences["wiki_query_string"] = conferences.apply(
    lambda row: row["name"] if pd.isna(row["wiki_query_string"]) else row["wiki_query_string"],
    axis=1,
)

# save the updated dataset with the correct links
conferences.to_csv("llm-request/conferences_with_links.csv", index=False)


# confirm that the updated links work by re-running the get_page_metadata function on the updated dataset

print("\nConfirming updated links...\n")
still_missing = []
for title in conferences["wiki_query_string"]:
    try:
        metadata = get_page_metadata(title)
        print(f"Found page for '{title}': {metadata['fullurl']}")
    except ValueError as e:
        print(f"Error for '{title}': {e}")
        still_missing.append(title)

print(f"Still missing {len(still_missing)}: {still_missing}")