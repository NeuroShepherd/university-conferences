import json
from pathlib import Path

from bs4 import BeautifulSoup


INPUT_PATH = Path("conference_wikipedia_html.json")
OUTPUT_PATH = Path("conference_relevant_sections.json")

member_h2_variants = {
    "Member Schools",
    "Member schools",
    "Member universities",
    "Members",
    "Member institutions",
}

history_h2_variants = {
    "History",
}


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def normalize_header(text: str) -> str:
    return normalize_text(text).lower()


def collect_between_nodes(start_node) -> str:
    chunks: list[str] = []
    start = start_node
    if getattr(start_node.parent, "name", None) == "div":
        start = start_node.parent

    sibling = start.next_sibling
    while sibling is not None:
        sibling_name = getattr(sibling, "name", None)
        if sibling_name == "h2":
            break
        if sibling_name == "div" and sibling.find("h2"):
            break

        html_fragment = str(sibling)
        if html_fragment.strip():
            chunks.append(html_fragment)
        sibling = sibling.next_sibling

    return "\n".join(chunks)


def extract_section_content(html: str, header_variants: set[str]) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    variants_normalized = {normalize_header(v) for v in header_variants}
    sections: list[dict] = []

    for h2 in soup.find_all("h2"):
        h2_text = normalize_text(h2.get_text(" ", strip=True))
        if not h2_text:
            continue
        if normalize_header(h2_text) not in variants_normalized:
            continue

        content = collect_between_nodes(h2)
        sections.append(
            {
                "h2": h2_text,
                "content": content,
                "content_length": len(content),
            }
        )

    return sections


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        payloads = json.load(f)

    output: dict[str, dict[str, list[dict]]] = {}
    for conference_name, payload in payloads.items():
        if payload.get("status") != "ok":
            continue
        html = payload.get("html")
        if not html:
            continue

        output[conference_name] = {
            "member_schools": extract_section_content(html, member_h2_variants),
            "conference_history": extract_section_content(html, history_h2_variants),
        }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(
        f"Wrote relevant section content for {len(output)} conferences to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()