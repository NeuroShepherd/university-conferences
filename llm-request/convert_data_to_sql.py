

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


INPUT_PATH = Path("llm-request/data/extracted_wiki_data_responses.json")
OUTPUT_DIR = Path("llm-request/sql")
OUTPUT_FILE = OUTPUT_DIR / "conference_data_canonicalized.sql"

# Order matters if foreign keys are enforced.
TABLE_ORDER = [
    "conferences",
    "universities",
    "university_conference_memberships",
]


def strip_markdown_fences(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).replace("'", "''")
    return f"'{text}'"


def parse_payload(entry: dict[str, Any]) -> dict[str, Any]:
    response_text = entry.get("response_text") or ""
    raw_response_text = entry.get("raw_response_text") or ""

    candidates = [response_text, strip_markdown_fences(raw_response_text)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError("Unable to parse JSON from response_text/raw_response_text")


def normalize_href(href: Any) -> str | None:
    if not isinstance(href, str):
        return None

    text = href.strip()
    if not text:
        return None

    text = unicodedata.normalize("NFKC", unquote(text))
    parts = urlsplit(text)
    path = parts.path.strip()

    if not path:
        return None
    if path.startswith("wiki/"):
        path = "/" + path
    if not path.startswith("/wiki/"):
        return None

    title = path[len("/wiki/") :].strip("/")
    if not title:
        return None

    title = re.sub(r"\s+", "_", title)
    title = re.sub(r"_+", "_", title)
    return f"/wiki/{title}"


def canonical_name_for_href(observed_names: Counter[str]) -> str | None:
    if not observed_names:
        return None

    # Prefer frequently observed forms; use longest as tie-break for abbreviations.
    ranked = sorted(observed_names.items(), key=lambda item: (item[1], len(item[0]), item[0]), reverse=True)
    return ranked[0][0]


def build_insert_statement(table_name: str, columns: list[str], rows: list[list[Any]]) -> str | None:
    if not rows:
        return None

    row_literals = []
    for row in rows:
        values = ", ".join(sql_literal(cell) for cell in row)
        row_literals.append(f"({values})")

    values_block = ",\n".join(f"    {row}" for row in row_literals)
    return f"INSERT INTO {table_name} ({', '.join(columns)})\nVALUES\n{values_block};"


def normalize_table_rows(columns: list[str], rows: list[Any]) -> list[list[Any]]:
    normalized: list[list[Any]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        row_copy = row[: len(columns)] + [None] * max(0, len(columns) - len(row))
        normalized.append(row_copy)
    return normalized


def gather_university_catalog(payloads: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str, str]]]:
    names_by_href: dict[str, Counter[str]] = defaultdict(Counter)
    attrs_by_href: dict[str, Counter[tuple[str | None, str | None]]] = defaultdict(Counter)
    aliases: set[tuple[str, str, str]] = set()

    for conference_name, payload in payloads.items():
        universities = payload.get("universities", {})
        if not isinstance(universities, dict):
            continue

        columns = universities.get("columns")
        rows = universities.get("rows")
        if not isinstance(columns, list) or not isinstance(rows, list):
            continue

        rows = normalize_table_rows(columns, rows)
        column_map = {name: index for index, name in enumerate(columns)}

        for row in rows:
            href_idx = column_map.get("university_wikipedia_href")
            name_idx = column_map.get("university_name")
            city_idx = column_map.get("city")
            state_idx = column_map.get("state")

            href = normalize_href(row[href_idx]) if href_idx is not None else None
            if href is None:
                continue

            name = str(row[name_idx]).strip() if name_idx is not None and row[name_idx] is not None else ""
            if name:
                names_by_href[href][name] += 1
                aliases.add((href, name, conference_name))

            city = str(row[city_idx]).strip() if city_idx is not None and row[city_idx] is not None else None
            state = str(row[state_idx]).strip() if state_idx is not None and row[state_idx] is not None else None
            attrs_by_href[href][(city, state)] += 1

    canonical: dict[str, dict[str, Any]] = {}
    for href, counter in names_by_href.items():
        canonical_name = canonical_name_for_href(counter)
        if canonical_name is None:
            continue

        city_state_counts = attrs_by_href.get(href)
        city, state = (None, None)
        if city_state_counts:
            city, state = sorted(city_state_counts.items(), key=lambda item: item[1], reverse=True)[0][0]

        canonical[href] = {
            "university_name": canonical_name,
            "university_wikipedia_href": href,
            "city": city,
            "state": state,
        }

    return canonical, sorted(aliases)


def build_rows_for_table(
    table_name: str,
    payload: dict[str, Any],
    canonical_universities: dict[str, dict[str, Any]],
) -> tuple[list[str], list[list[Any]]]:
    table_payload = payload.get(table_name)
    if not isinstance(table_payload, dict):
        return [], []

    columns = table_payload.get("columns")
    rows = table_payload.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return [], []

    rows = normalize_table_rows(columns, rows)
    column_map = {name: index for index, name in enumerate(columns)}

    if table_name == "universities":
        href_idx = column_map.get("university_wikipedia_href")
        name_idx = column_map.get("university_name")
        city_idx = column_map.get("city")
        state_idx = column_map.get("state")
        if href_idx is not None:
            deduped: dict[str, list[Any]] = {}
            for row in rows:
                normalized_href = normalize_href(row[href_idx])
                if normalized_href is None:
                    continue
                row[href_idx] = normalized_href
                canonical = canonical_universities.get(normalized_href)
                if canonical:
                    if name_idx is not None:
                        row[name_idx] = canonical["university_name"]
                    if city_idx is not None and row[city_idx] is None:
                        row[city_idx] = canonical["city"]
                    if state_idx is not None and row[state_idx] is None:
                        row[state_idx] = canonical["state"]
                deduped[normalized_href] = row
            rows = list(deduped.values())

    if table_name == "university_conference_memberships":
        href_idx = column_map.get("university_wikipedia_href")
        if href_idx is not None:
            for row in rows:
                row[href_idx] = normalize_href(row[href_idx])
            rows = [row for row in rows if row[href_idx] is not None]

    return columns, rows


def build_single_sql(
    parsed_payloads: dict[str, dict[str, Any]],
    canonical_universities: dict[str, dict[str, Any]],
    aliases: list[tuple[str, str, str]],
    failed: dict[str, str],
) -> str:
    lines: list[str] = [
        "-- Auto-generated SQL inserts for all conferences",
        "-- Source: llm-request/data/extracted_wiki_data_responses.json",
        "-- Universities are canonicalized by normalized university_wikipedia_href.",
        "",
        "BEGIN;",
        "",
    ]

    canonical_rows = [
        [
            row["university_name"],
            row["university_wikipedia_href"],
            row["city"],
            row["state"],
        ]
        for row in sorted(canonical_universities.values(), key=lambda item: item["university_name"])
    ]

    lines.append("-- Canonical universities (one row per normalized href)")
    canonical_stmt = build_insert_statement(
        "universities",
        ["university_name", "university_wikipedia_href", "city", "state"],
        canonical_rows,
    )
    if canonical_stmt:
        lines.append(canonical_stmt)
    lines.append("")

    lines.append("-- University name variants observed in source conference pages")
    alias_stmt = build_insert_statement(
        "university_name_aliases",
        ["canonical_university_wikipedia_href", "alias_university_name", "source_conference_name"],
        [[href, alias_name, source_conf] for href, alias_name, source_conf in aliases],
    )
    if alias_stmt:
        lines.append(alias_stmt)
    lines.append("")

    all_conference_rows: list[list[Any]] = []
    all_membership_rows: list[list[Any]] = []
    conference_columns: list[str] = []
    membership_columns: list[str] = []

    for conference_name, payload in parsed_payloads.items():
        conf_cols, conf_rows = build_rows_for_table("conferences", payload, canonical_universities)
        mem_cols, mem_rows = build_rows_for_table("university_conference_memberships", payload, canonical_universities)

        if conf_cols and not conference_columns:
            conference_columns = conf_cols
        if mem_cols and not membership_columns:
            membership_columns = mem_cols

        all_conference_rows.extend(conf_rows)
        all_membership_rows.extend(mem_rows)

        lines.append(f"-- Parsed conference payload: {conference_name}")

    if conference_columns:
        lines.append("")
        lines.append("-- Conference entities")
        deduped_conferences: dict[tuple[Any, ...], list[Any]] = {}
        for row in all_conference_rows:
            deduped_conferences[tuple(row)] = row
        conf_stmt = build_insert_statement("conferences", conference_columns, list(deduped_conferences.values()))
        if conf_stmt:
            lines.append(conf_stmt)

    if membership_columns:
        lines.append("")
        lines.append("-- University membership history")
        deduped_memberships: dict[tuple[Any, ...], list[Any]] = {}
        for row in all_membership_rows:
            deduped_memberships[tuple(row)] = row
        mem_stmt = build_insert_statement(
            "university_conference_memberships",
            membership_columns,
            list(deduped_memberships.values()),
        )
        if mem_stmt:
            lines.append(mem_stmt)

    if failed:
        lines.append("")
        lines.append("-- Failed conference payloads")
        for conference_name, error in sorted(failed.items()):
            lines.append(f"-- {conference_name}: {error}")

    lines.extend(["", "COMMIT;", ""])
    return "\n".join(lines)


def main() -> None:
    extracted_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_payloads: dict[str, dict[str, Any]] = {}
    failed: dict[str, str] = {}

    for conference_name, entry in extracted_data.items():
        try:
            parsed_payloads[conference_name] = parse_payload(entry)
        except Exception as exc:
            failed[conference_name] = str(exc)

    canonical_universities, aliases = gather_university_catalog(parsed_payloads)
    sql_text = build_single_sql(parsed_payloads, canonical_universities, aliases, failed)
    OUTPUT_FILE.write_text(sql_text, encoding="utf-8")

    print(f"Wrote consolidated SQL file: {OUTPUT_FILE}")
    print(f"Canonical universities: {len(canonical_universities)}")
    print(f"University aliases: {len(aliases)}")
    if failed:
        print(f"Failed to parse {len(failed)} conference payloads")


if __name__ == "__main__":
    main()