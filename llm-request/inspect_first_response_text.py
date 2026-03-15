import argparse
import json
import re
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


def parse_response_payload(text: str):
    candidates = []
    cleaned = strip_fences(text)
    candidates.append(cleaned)

    # Try extracting JSON from first '{' onward for responses that include preamble text.
    brace_idx = cleaned.find("{")
    if brace_idx != -1:
        candidates.append(cleaned[brace_idx:])

    last_error = None
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate), None
        except Exception as exc:
            last_error = exc
            try:
                # Attempt tolerant parse of leading valid JSON object.
                obj, _ = decoder.raw_decode(candidate)
                return obj, None
            except Exception as raw_exc:
                last_error = raw_exc

    return None, last_error


def extract_balanced_object(text: str, start_idx: int):
    # start_idx should point to '{'
    if start_idx < 0 or start_idx >= len(text) or text[start_idx] != "{":
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start_idx : i + 1]

    return None


def parse_sections_best_effort(text: str):
    cleaned = strip_fences(text)
    parsed_sections = {}
    section_names = [
        "universities",
        "conferences",
        "university_conference_memberships",
    ]

    for name in section_names:
        # Find: "section_name" : {
        match = re.search(rf'"{re.escape(name)}"\s*:\s*\{{', cleaned)
        if not match:
            continue

        # match ends after '{', so object starts one char before end
        obj_start = match.end() - 1
        obj_text = extract_balanced_object(cleaned, obj_start)
        if not obj_text:
            continue

        try:
            section_obj = json.loads(obj_text)
        except Exception:
            continue

        if isinstance(section_obj, dict):
            parsed_sections[name] = section_obj

    return parsed_sections


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
        parsed, parse_error = parse_response_payload(response_text)
        if not isinstance(parsed, dict):
            print(f"Could not fully parse response_text as JSON: {parse_error}")
            print("Attempting best-effort section parsing for tabular display...")
            parsed = parse_sections_best_effort(response_text)
            if not parsed:
                print("No recoverable table sections found.")
                print("Raw response_text preview:")
                preview = response_text[:2000]
                print(preview)
                if len(response_text) > len(preview):
                    print("... [truncated]")
                return

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
        print("No response_text found for this result.")


if __name__ == "__main__":
    main()
