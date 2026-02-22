

# many of the conference pages have a timeline map of the conference history, which is 
# often under the "Member institutions" or similarly named section. 
# They can be identified by looking for a div with class "timeline-wrapper" 
# or a <map> element. More specifically, the map element is generally tucked within a "timeline-wrapper" div.
# However, we want to access the underlying information from the map which can be done by clicking on the
# [ edit ] link next to the header right above the timelime map, which takes you to the section editor 
# where the map is represented in a more structured format.

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

INPUT_PATH = Path("conference_wikipedia_html.json")
OUTPUT_PATH = Path("conference_timeline_map_edit_links.json")
API = "https://en.wikipedia.org/w/api.php"

with INPUT_PATH.open("r", encoding="utf-8") as f:
    json_data = json.load(f)


member_h2_variants = {
    "Member Schools",
    "Member schools",
    "Member universities",
    "Members",
    "Member institutions",
}


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def normalize_header(text: str) -> str:
    return normalize_text(text).lower()


def iter_section_elements(h2_node):
    start = h2_node
    if getattr(h2_node.parent, "name", None) == "div":
        start = h2_node.parent

    for element in start.next_elements:
        if element is h2_node:
            continue
        if getattr(element, "name", None) == "h2":
            break
        yield element


def has_timeline_map_tag(tag) -> bool:
    if getattr(tag, "name", None) == "map":
        return True
    if getattr(tag, "name", None) == "div" and tag.has_attr("class"):
        return "timeline-wrapper" in tag.get("class", [])
    return False


def extract_edit_link(heading_tag, base_url: str | None) -> tuple[str | None, str | None]:
    if heading_tag is None:
        return None, None

    edit_span = heading_tag.find("span", class_="mw-editsection")
    if edit_span:
        link = edit_span.find("a")
    else:
        link = heading_tag.find("a", href=re.compile(r"[?&]action=edit"))

    if not link:
        return None, None

    href = link.get("href")
    if not href:
        return None, None

    if href.startswith("http"):
        return href, href
    base = "https://en.wikipedia.org"
    return href, f"{base}{href}"


def fetch_section_index(title: str) -> dict[str, str]:
    params = {
        "action": "parse",
        "format": "json",
        "formatversion": 2,
        "page": title,
        "prop": "sections",
    }
    response = requests.get(API, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    sections = payload.get("parse", {}).get("sections", [])
    return {normalize_header(section.get("line", "")): section.get("index") for section in sections}


def build_edit_url(title: str, section_index: str | None) -> str | None:
    if not title or not section_index:
        return None
    return f"https://en.wikipedia.org/w/index.php?title={title}&action=edit&section={section_index}"



normalized_variants = {normalize_header(v) for v in member_h2_variants}
results: list[dict] = []
section_index_cache: dict[str, dict[str, str]] = {}

for conference, payload in json_data.items():
    if payload.get("status") != "ok":
        continue
    html = payload.get("html")
    if not html:
        continue

    soup = BeautifulSoup(html, "html.parser")
    page_url = payload.get("resolved_url")
    page_title = payload.get("resolved_title") or conference

    if page_title not in section_index_cache:
        try:
            section_index_cache[page_title] = fetch_section_index(page_title)
        except requests.RequestException:
            section_index_cache[page_title] = {}

    for h2 in soup.find_all("h2"):
        h2_text = normalize_text(h2.get_text(" ", strip=True))
        if not h2_text:
            continue
        if normalize_header(h2_text) not in normalized_variants:
            continue

        last_heading = None
        last_heading_container = None
        for element in iter_section_elements(h2):
            if getattr(element, "name", None) in {"h3", "h4"}:
                last_heading = element
                last_heading_container = element.find_parent(
                    "div", class_=re.compile(r"\bmw-heading\b")
                )
                continue

            if has_timeline_map_tag(element):
                heading_text = None
                if last_heading is not None:
                    heading_text = normalize_text(last_heading.get_text(" ", strip=True))
                heading_node = last_heading_container or last_heading or h2
                href, full_url = extract_edit_link(heading_node, page_url)
                if full_url is None:
                    section_title = heading_text or h2_text
                    section_index = section_index_cache.get(page_title, {}).get(
                        normalize_header(section_title)
                    )
                    full_url = build_edit_url(page_title, section_index)
                    href = full_url
                results.append(
                    {
                        "conference": conference,
                        "member_section": h2_text,
                        "map_heading": heading_text,
                        "edit_href": href,
                        "edit_url": full_url,
                    }
                )
                break

        if results and results[-1]["conference"] == conference:
            break

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("==================")
print("Timeline map edit links found:")
for item in results:
    print(f"{item['conference']}: {item['edit_url']}")

