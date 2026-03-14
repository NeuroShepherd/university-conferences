from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from json_repair import repair_json


def strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_json_text(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(strip_fences(text))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair malformed structured conference payload JSON entries.")
    parser.add_argument(
        "--input",
        default="llm-request/extracted_data_responses.json",
        help="Path to extracted conference response JSON.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Write repaired payloads back to the input file.",
    )
    parser.add_argument(
        "--report",
        default="llm-request/processed-json/repair_summary.json",
        help="Path to write repair summary JSON.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    report_path = Path(args.report)

    payload = json.loads(input_path.read_text())

    already_valid: list[str] = []
    repaired: list[str] = []
    unrepaired: dict[str, str] = {}

    for conf_name, entry in payload.items():
        raw = entry.get("sql_text")
        if not isinstance(raw, str) or not raw.strip():
            continue

        parsed = parse_json_text(raw)
        if parsed is not None:
            already_valid.append(conf_name)
            continue

        try:
            repaired_text = repair_json(strip_fences(raw), skip_json_loads=True)
            repaired_obj = json.loads(repaired_text)
            if not isinstance(repaired_obj, dict):
                unrepaired[conf_name] = "repair_result_not_object"
                continue
            entry["sql_text"] = json.dumps(repaired_obj, ensure_ascii=False, indent=2)
            repaired.append(conf_name)
        except Exception as exc:
            unrepaired[conf_name] = str(exc)

    if args.in_place:
        temp_path = input_path.with_suffix(input_path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        temp_path.replace(input_path)

    summary = {
        "input": str(input_path),
        "conference_count": len(payload),
        "already_valid_count": len(already_valid),
        "repaired_count": len(repaired),
        "unrepaired_count": len(unrepaired),
        "repaired_conferences": repaired,
        "unrepaired_conferences": unrepaired,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
