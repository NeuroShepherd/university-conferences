import argparse
import json
from pathlib import Path

RESPONSES_PATH = Path("llm-request/data/extracted_wiki_data_responses.json")
MAX_COL_WIDTH = 40

EXPECTED_COLUMNS = {
    "universities": ["university_name", "university_wikipedia_href", "city", "state"],
    "conferences": [
        "conference_name",
        "conference_wikipedia_href",
        "conference_start_year",
        "conference_end_year",
    ],
    "university_conference_memberships": [
        "university_wikipedia_href",
        "conference_name",
        "start_year",
        "end_year",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect extracted wiki response payloads in tabular form."
    )
    parser.add_argument(
        "--conference",
        help="Conference name key to inspect exactly as it appears in the JSON file.",
    )
    parser.add_argument(
        "--index",
        type=int,
        help="0-based index of conference entry to inspect.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available conference names with indices.",
    )
    return parser.parse_args()


def strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Drop opening fence line (``` or ```json)
        lines = lines[1:]
        # Drop closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def to_str(value) -> str:
    if value is None:
        return "NULL"
    return str(value)


def clamp(text: str, max_width: int = MAX_COL_WIDTH) -> str:
    if len(text) <= max_width:
        return text
    if max_width <= 1:
        return text[:max_width]
    return text[: max_width - 1] + "…"


def render_table(columns: list[str], rows: list[list]) -> str:
    col_headers = [clamp(col) for col in columns]
    string_rows = [[clamp(to_str(cell)) for cell in row] for row in rows]
    widths = [len(col) for col in col_headers]

    for row in string_rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    def hline(char: str = "-") -> str:
        return "+" + "+".join(char * (w + 2) for w in widths) + "+"

    def fmt_row(cells: list[str]) -> str:
        padded = [f" {cells[i].ljust(widths[i])} " for i in range(len(widths))]
        return "|" + "|".join(padded) + "|"

    lines = [hline("-"), fmt_row(col_headers), hline("=")]
    for row in string_rows:
        # Pad short rows to match header width
        fixed = row + [""] * (len(widths) - len(row))
        lines.append(fmt_row(fixed))
        lines.append(hline("-"))
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    if not RESPONSES_PATH.exists():
        raise FileNotFoundError(f"Missing file: {RESPONSES_PATH}")

    data = json.loads(RESPONSES_PATH.read_text())
    if not isinstance(data, dict) or not data:
        print("No results found.")
        return

    entries = list(data.items())

    if args.list:
        for idx, (conf_name, _) in enumerate(entries):
            print(f"{idx}: {conf_name}")
        return

    selected_conf_name = None
    selected_payload = None

    if args.conference:
        selected_conf_name = args.conference
        selected_payload = data.get(args.conference)
        if selected_payload is None:
            raise KeyError(f"Conference not found: {args.conference}")
    elif args.index is not None:
        if args.index < 0 or args.index >= len(entries):
            raise IndexError(f"Index {args.index} out of range (0-{len(entries)-1})")
        selected_conf_name, selected_payload = entries[args.index]
    else:
        selected_conf_name, selected_payload = entries[0]

    response_text = None
    if isinstance(selected_payload, dict):
        response_text = selected_payload.get("response_text")

    print(f"Conference: {selected_conf_name}")
    print("-" * 80)
    if response_text:
        cleaned = strip_fences(response_text)
        parsed = json.loads(cleaned)

        for section_name, section_payload in parsed.items():
            if not isinstance(section_payload, dict):
                continue
            columns = section_payload.get("columns") or []
            rows = section_payload.get("rows") or []
            if not isinstance(columns, list) or not isinstance(rows, list):
                continue

            print(f"\n{section_name}:")
            expected = EXPECTED_COLUMNS.get(section_name)
            if expected is not None and columns != expected:
                print(f"[schema warning] Expected columns: {expected}")
                print(f"[schema warning] Actual columns:   {columns}")
            print(render_table(columns, rows))
    else:
        print("No response_text found for the first result.")


if __name__ == "__main__":
    main()
