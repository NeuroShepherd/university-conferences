import csv
import json
from pathlib import Path

from bs4 import BeautifulSoup


DATA_ASSEMBLY_DIR = Path(__file__).resolve().parent
JSON_DIR = DATA_ASSEMBLY_DIR / "json"
INPUT_PATH = JSON_DIR / "conference_wikipedia_html.json"
JSON_OUTPUT_PATH = JSON_DIR / "conference_section_headers.json"
CSV_OUTPUT_PATH = DATA_ASSEMBLY_DIR / "conference_section_headers.csv"


def clean_header_text(text: str) -> str:
    return " ".join(text.split())


def extract_headers_from_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    sections: list[dict] = []
    current_section: dict | None = None

    for tag in soup.find_all(["h2", "h3"]):
        header_text = clean_header_text(tag.get_text(" ", strip=True))
        if not header_text:
            continue

        if tag.name == "h2":
            current_section = {"h2": header_text, "h3": []}
            sections.append(current_section)
        elif tag.name == "h3":
            if current_section is None:
                current_section = {"h2": "(no h2)", "h3": []}
                sections.append(current_section)
            current_section["h3"].append(header_text)

    return sections


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "conference_name",
        "h2_index",
        "h2_text",
        "h3_index",
        "h3_text",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {INPUT_PATH}")

    JSON_DIR.mkdir(parents=True, exist_ok=True)

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        payloads = json.load(f)

    mapping: dict[str, list[dict]] = {}
    rows: list[dict] = []

    for conference_name, payload in payloads.items():
        if payload.get("status") != "ok":
            continue
        html = payload.get("html")
        if not html:
            continue

        sections = extract_headers_from_html(html)
        mapping[conference_name] = sections

        for h2_index, section in enumerate(sections, start=1):
            h2_text = section["h2"]
            h3_headers = section.get("h3", [])
            if not h3_headers:
                rows.append(
                    {
                        "conference_name": conference_name,
                        "h2_index": h2_index,
                        "h2_text": h2_text,
                        "h3_index": "",
                        "h3_text": "",
                    }
                )
                continue

            for h3_index, header in enumerate(h3_headers, start=1):
                rows.append(
                    {
                        "conference_name": conference_name,
                        "h2_index": h2_index,
                        "h2_text": h2_text,
                        "h3_index": h3_index,
                        "h3_text": header,
                    }
                )

    with JSON_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    write_csv(CSV_OUTPUT_PATH, rows)

    print(f"Wrote headers for {len(mapping)} conferences to {JSON_OUTPUT_PATH}")
    print(f"Wrote {len(rows)} header rows to {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
