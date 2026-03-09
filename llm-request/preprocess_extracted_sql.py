from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TABLE_ORDER = [
    "dim_associations",
    "dim_divisions",
    "dim_states",
    "dim_cities",
    "dim_affiliations",
    "dim_sports",
    "dim_membership_types",
    "dim_universities",
    "dim_conferences",
    "bridge_university_names",
    "bridge_university_nicknames",
    "bridge_university_sports",
    "bridge_conference_names",
    "bridge_conference_divisions",
    "fact_membership",
]

NATURAL_KEY_FIELDS = {
    "dim_associations": ["association_name"],
    "dim_divisions": ["division_name", "association_id"],
    "dim_states": ["state_abbreviation"],
    "dim_cities": ["city_name", "state_id"],
    "dim_affiliations": ["affiliation_type", "denomination"],
    "dim_sports": ["sport_name_normalized"],
    "dim_membership_types": ["type_name"],
    "dim_universities": ["current_university_name"],
    "dim_conferences": ["current_conference_name"],
    "bridge_university_names": ["university_id", "university_name", "start_year", "end_year"],
    "bridge_university_nicknames": ["university_id", "nickname", "start_year", "sport_id"],
    "bridge_university_sports": ["university_id", "sport_id", "division_id", "start_year", "end_year"],
    "bridge_conference_names": ["conference_id", "conference_name", "start_year", "end_year"],
    "bridge_conference_divisions": ["conference_id", "division_id", "start_year", "end_year"],
    "fact_membership": [
        "university_id",
        "conference_id",
        "membership_type_id",
        "joined_year",
        "left_year",
        "sport_id",
        "division_id",
    ],
}

MEMBERSHIP_TYPE_CODE_MAP = {
    "Full": "Full Member",
    "FullxF": "Full Member (non-football)",
    "AssocF": "Associate Member (Football only)",
    "AssocOS": "Associate Member (Other Sport)",
    "AssocMIH": "Associate Member (Men's Ice Hockey only)",
    "Ind": "Full Member",
    "OtherC1": "Full Member",
    "OtherC2": "Full Member",
}

TEMPORAL_RULES = {
    "bridge_university_names": {
        "group_by": ["university_id"],
        "start": "start_year",
        "end": "end_year",
        "compare": ["university_name"],
    },
    "bridge_conference_names": {
        "group_by": ["conference_id"],
        "start": "start_year",
        "end": "end_year",
        "compare": ["conference_name"],
    },
    "bridge_university_nicknames": {
        "group_by": ["university_id", "sport_id"],
        "start": "start_year",
        "end": "end_year",
        "compare": ["nickname"],
    },
    "bridge_university_sports": {
        "group_by": ["university_id", "sport_id", "division_id"],
        "start": "start_year",
        "end": "end_year",
        "compare": ["is_varsity", "sport_notes"],
    },
    "bridge_conference_divisions": {
        "group_by": ["conference_id", "division_id"],
        "start": "start_year",
        "end": "end_year",
        "compare": [],
    },
    "fact_membership": {
        "group_by": ["university_id", "sport_id", "division_id"],
        "start": "joined_year",
        "end": "left_year",
        "compare": ["conference_id", "membership_type_id"],
    },
}


@dataclass
class ParsedRecord:
    source_entry: str
    table: str
    columns: list[str]
    row: dict[str, Any]
    raw_sql: str
    order_index: int
    source_statement_index: int


@dataclass
class DedupedRecord:
    table: str
    row: dict[str, Any]
    key: str
    sources: list[str]
    source_statement_indexes: list[int]
    representative_sql: str
    order_index: int


def normalize_space(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_name(value: str) -> str:
    return normalize_space(value).casefold()


def strip_line_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            out.append(ch)
            if ch == "'":
                if nxt == "'":
                    out.append(nxt)
                    i += 2
                    continue
                in_string = False
            i += 1
            continue
        if ch == "'":
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "-" and nxt == "-":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def scan_insert_statements(text: str) -> list[str]:
    cleaned = strip_line_comments(text)
    pattern = re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE)
    statements: list[str] = []
    for match in pattern.finditer(cleaned):
        start = match.start()
        i = match.end()
        in_string = False
        depth = 0
        while i < len(cleaned):
            ch = cleaned[i]
            nxt = cleaned[i + 1] if i + 1 < len(cleaned) else ""
            if in_string:
                if ch == "'":
                    if nxt == "'":
                        i += 2
                        continue
                    in_string = False
                i += 1
                continue
            if ch == "'":
                in_string = True
                i += 1
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == ";" and depth == 0:
                statements.append(cleaned[start:i].strip())
                break
            i += 1
    return statements


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            current.append(ch)
            if ch == "'":
                if nxt == "'":
                    current.append(nxt)
                    i += 2
                    continue
                in_string = False
            i += 1
            continue
        if ch == "'":
            in_string = True
            current.append(ch)
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == delimiter and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def extract_value_groups(values_sql: str) -> list[str]:
    groups: list[str] = []
    i = 0
    in_string = False
    depth = 0
    start: int | None = None
    while i < len(values_sql):
        ch = values_sql[i]
        nxt = values_sql[i + 1] if i + 1 < len(values_sql) else ""
        if in_string:
            if ch == "'":
                if nxt == "'":
                    i += 2
                    continue
                in_string = False
            i += 1
            continue
        if ch == "'":
            in_string = True
            i += 1
            continue
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0 and start is not None:
                groups.append(values_sql[start : i + 1].strip())
                start = None
        i += 1
    return groups


def parse_string_literal(text: str) -> str:
    inner = text[1:-1]
    return inner.replace("''", "'")


def expression_to_string(expr: Any) -> str:
    if isinstance(expr, dict):
        return json.dumps(expr, sort_keys=True, ensure_ascii=False)
    if isinstance(expr, str):
        return expr
    return json.dumps(expr, sort_keys=True, ensure_ascii=False)


def parse_simple_select(expr: str) -> dict[str, Any] | None:
    compact = normalize_space(expr)
    match = re.match(
        r"^\(?\s*SELECT\s+[^\s]+\s+FROM\s+([a-zA-Z_][\w]*)"
        r"(?:\s+[a-zA-Z_][\w]*)?\s+WHERE\s+(.+?)\s*\)?$",
        compact,
        re.IGNORECASE,
    )
    if not match:
        return None
    table = match.group(1)
    where_text = match.group(2)
    conditions: dict[str, Any] = {}
    for part in split_top_level(where_text.replace(" AND ", ","), delimiter=","):
        cond = normalize_space(part)
        if not cond:
            continue
        cond_match = re.match(r"^(?:[a-zA-Z_][\w]*\.)?([a-zA-Z_][\w]*)\s*=\s*(.+)$", cond)
        if not cond_match:
            return {"kind": "sql", "sql": compact}
        field = cond_match.group(1)
        value = parse_expression(cond_match.group(2))
        conditions[field] = value
    return {"kind": "ref", "table": table, "key": conditions}


def parse_expression(expr: str) -> Any:
    expr = expr.strip()
    if not expr:
        return {"kind": "empty"}
    upper = expr.upper()
    if upper == "NULL":
        return None
    if upper == "TRUE":
        return True
    if upper == "FALSE":
        return False
    if re.fullmatch(r"-?\d+", expr):
        return int(expr)
    if re.fullmatch(r"-?\d+\.\d+", expr):
        return float(expr)
    if expr.startswith("'") and expr.endswith("'"):
        return parse_string_literal(expr)
    if upper.startswith("(SELECT") or upper.startswith("SELECT"):
        parsed = parse_simple_select(expr)
        if parsed is not None:
            return parsed
    call_match = re.match(r"^([a-zA-Z_][\w\.]*)\((.*)\)$", expr, re.DOTALL)
    if call_match:
        func_name = call_match.group(1)
        args = [parse_expression(part) for part in split_top_level(call_match.group(2))] if call_match.group(2).strip() else []
        return {"kind": "call", "name": func_name, "args": args}
    if re.fullmatch(r"[a-zA-Z_][\w\.]*", expr):
        return {"kind": "var", "name": expr}
    return {"kind": "sql", "sql": normalize_space(expr)}


def parse_insert_statement(statement: str) -> tuple[str, list[str], list[dict[str, Any]]] | None:
    match = re.match(
        r"^INSERT\s+INTO\s+([a-zA-Z_][\w]*)\s*\((.*?)\)\s*VALUES\s*(.+)$",
        statement,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return None
    table = match.group(1)
    columns = [col.strip() for col in split_top_level(match.group(2))]
    values_part = re.split(r"\bON\s+CONFLICT\b", match.group(3), maxsplit=1, flags=re.IGNORECASE)[0].strip()
    groups = extract_value_groups(values_part)
    rows: list[dict[str, Any]] = []
    for group in groups:
        inner = group[1:-1].strip()
        values = [parse_expression(part) for part in split_top_level(inner)]
        if len(values) != len(columns):
            rows.append({"__parse_error__": {"expected_columns": len(columns), "values_found": len(values), "raw_group": group}})
            continue
        rows.append(dict(zip(columns, values, strict=True)))
    return table, columns, rows


def extract_assignments(text: str) -> dict[int, dict[str, Any]]:
    cleaned = strip_line_comments(text)
    assignment_map: dict[int, dict[str, Any]] = {}
    pattern = re.compile(r"\b([a-zA-Z_][\w]*)\s*(?:[A-Z]+\s+)?(?::=)\s*(.+?)\s*;", re.DOTALL)
    context: dict[str, Any] = {}
    for match in pattern.finditer(cleaned):
        var_name = match.group(1)
        expr = parse_expression(match.group(2))
        context[var_name] = expr
        assignment_map[match.start()] = dict(context)
    return assignment_map


def assignment_context_for_index(assignment_map: dict[int, dict[str, Any]], index: int) -> dict[str, Any]:
    best_key = -1
    for key in assignment_map:
        if key <= index and key > best_key:
            best_key = key
    return assignment_map.get(best_key, {}).copy()


def resolve_expression(expr: Any, context: dict[str, Any], seen: set[str] | None = None) -> Any:
    seen = seen or set()
    if isinstance(expr, (str, int, float, bool)) or expr is None:
        return expr
    if not isinstance(expr, dict):
        return expr
    kind = expr.get("kind")
    if kind == "var":
        name = expr["name"]
        if name in seen:
            return {"kind": "unresolved_var", "name": name}
        if name in context:
            return resolve_expression(context[name], context, seen | {name})
        return {"kind": "unresolved_var", "name": name}
    if kind == "call":
        name = expr["name"]
        args = [resolve_expression(arg, context, seen) for arg in expr.get("args", [])]
        if name == "get_state_id_by_abbrev" and len(args) == 1:
            return {"kind": "ref", "table": "dim_states", "key": {"state_abbreviation": args[0]}}
        if name == "get_city_id" and len(args) == 2:
            return {"kind": "ref", "table": "dim_cities", "key": {"city_name": args[0], "state_abbreviation": args[1]}}
        if name == "get_affiliation_id" and len(args) == 2:
            return {"kind": "ref", "table": "dim_affiliations", "key": {"affiliation_type": args[0], "denomination": args[1]}}
        if name == "get_university_id" and len(args) == 1:
            return {"kind": "ref", "table": "dim_universities", "key": {"current_university_name": args[0]}}
        if name == "get_sport_id" and len(args) == 1:
            return {"kind": "ref", "table": "dim_sports", "key": {"sport_name_normalized": args[0]}}
        if name == "get_conference_id" and len(args) == 1:
            return {"kind": "ref", "table": "dim_conferences", "key": {"current_conference_name": args[0]}}
        if name == "get_membership_type_id" and len(args) == 1:
            if isinstance(args[0], str):
                mapped = MEMBERSHIP_TYPE_CODE_MAP.get(args[0], args[0])
                return {"kind": "ref", "table": "dim_membership_types", "key": {"type_name": mapped}}
            return {"kind": "ref", "table": "dim_membership_types", "key": {"type_name": args[0]}}
        if name.upper() == "GREATEST" and len(args) == 2 and all(isinstance(arg, (int, float)) for arg in args):
            return max(args)
        if name.upper() == "COALESCE":
            for arg in args:
                if arg is not None:
                    return arg
            return None
        return {"kind": "call", "name": name, "args": args}
    if kind == "ref":
        return {
            "kind": "ref",
            "table": expr["table"],
            "key": {key: resolve_expression(value, context, seen) for key, value in expr.get("key", {}).items()},
        }
    return expr


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_space(value)
    return value


def canonicalize(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_name(value)
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, dict):
        if value.get("kind") == "ref":
            return {
                "kind": "ref",
                "table": value["table"],
                "key": {k: canonicalize(v) for k, v in sorted(value.get("key", {}).items())},
            }
        return {k: canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, float) and math.isfinite(value):
        return round(value, 6)
    return value


def row_key(table: str, row: dict[str, Any]) -> str:
    key_fields = NATURAL_KEY_FIELDS.get(table, sorted(row.keys()))
    key_obj = {field: canonicalize(row.get(field)) for field in key_fields}
    return json.dumps(key_obj, sort_keys=True, ensure_ascii=False)


def row_signature(row: dict[str, Any]) -> str:
    return json.dumps(canonicalize(row), sort_keys=True, ensure_ascii=False)


def serialize_value(value: Any) -> str | None:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, dict) and value.get("kind") == "ref":
        table = value["table"]
        key = value.get("key", {})
        if table == "dim_associations" and "association_name" in key:
            val = serialize_value(key["association_name"])
            return f"(SELECT association_id FROM dim_associations WHERE association_name = {val})"
        if table == "dim_divisions" and "division_name" in key:
            val = serialize_value(key["division_name"])
            return f"(SELECT division_id FROM dim_divisions WHERE division_name = {val})"
        if table == "dim_states" and "state_abbreviation" in key:
            val = serialize_value(key["state_abbreviation"])
            return f"(SELECT state_id FROM dim_states WHERE state_abbreviation = {val})"
        if table == "dim_cities" and "city_name" in key and "state_abbreviation" in key:
            city = serialize_value(key["city_name"])
            state = serialize_value(key["state_abbreviation"])
            return (
                "(SELECT city_id FROM dim_cities WHERE city_name = "
                f"{city} AND state_id = (SELECT state_id FROM dim_states WHERE state_abbreviation = {state}))"
            )
        if table == "dim_affiliations" and "affiliation_type" in key:
            aff = serialize_value(key["affiliation_type"])
            denom = key.get("denomination")
            if denom is None:
                return (
                    "(SELECT affiliation_id FROM dim_affiliations WHERE affiliation_type = "
                    f"{aff} AND denomination IS NULL)"
                )
            denom_sql = serialize_value(denom)
            return (
                "(SELECT affiliation_id FROM dim_affiliations WHERE affiliation_type = "
                f"{aff} AND denomination = {denom_sql})"
            )
        if table == "dim_universities" and "current_university_name" in key:
            val = serialize_value(key["current_university_name"])
            return f"(SELECT university_id FROM dim_universities WHERE current_university_name = {val})"
        if table == "dim_conferences" and "current_conference_name" in key:
            val = serialize_value(key["current_conference_name"])
            return f"(SELECT conference_id FROM dim_conferences WHERE current_conference_name = {val})"
        if table == "dim_sports" and "sport_name_normalized" in key:
            val = serialize_value(key["sport_name_normalized"])
            return f"(SELECT sport_id FROM dim_sports WHERE sport_name_normalized = {val})"
        if table == "dim_membership_types" and "type_name" in key:
            val = serialize_value(key["type_name"])
            return f"(SELECT membership_type_id FROM dim_membership_types WHERE type_name = {val})"
    return None


def build_insert_sql(table: str, row: dict[str, Any]) -> str | None:
    columns = list(row.keys())
    values_sql: list[str] = []
    for column in columns:
        sql_value = serialize_value(row[column])
        if sql_value is None:
            return None
        values_sql.append(sql_value)
    joined_cols = ", ".join(columns)
    joined_values = ", ".join(values_sql)
    return f"INSERT INTO {table} ({joined_cols}) VALUES ({joined_values}) ON CONFLICT DO NOTHING;"


def parse_records(input_path: Path) -> list[ParsedRecord]:
    payload = json.loads(input_path.read_text())
    records: list[ParsedRecord] = []
    order_index = 0
    for source_entry, entry_payload in payload.items():
        sql_text = entry_payload.get("sql_text")
        if not isinstance(sql_text, str) or not sql_text.strip():
            continue
        assignments = extract_assignments(sql_text)
        cleaned = strip_line_comments(sql_text)
        insert_statements = scan_insert_statements(sql_text)
        search_start = 0
        for statement_index, statement in enumerate(insert_statements, start=1):
            parsed = parse_insert_statement(statement)
            if parsed is None:
                continue
            table, columns, rows = parsed
            found_at = cleaned.find(statement, search_start)
            search_start = found_at + max(1, len(statement)) if found_at >= 0 else search_start
            context = assignment_context_for_index(assignments, max(found_at, 0))
            for row in rows:
                if "__parse_error__" in row:
                    row = row.copy()
                    row["__source_context__"] = {"statement": statement}
                resolved_row = {column: resolve_expression(value, context) for column, value in row.items()}
                resolved_row = {column: normalize_scalar(value) if not isinstance(value, dict) else canonicalize(value) for column, value in resolved_row.items()}
                records.append(
                    ParsedRecord(
                        source_entry=source_entry,
                        table=table,
                        columns=columns,
                        row=resolved_row,
                        raw_sql=statement,
                        order_index=order_index,
                        source_statement_index=statement_index,
                    )
                )
                order_index += 1
    return records


def dedupe_records(records: list[ParsedRecord]) -> tuple[list[DedupedRecord], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[ParsedRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.table, row_key(record.table, record.row))].append(record)

    deduped: list[DedupedRecord] = []
    conflicts: list[dict[str, Any]] = []

    for (table, key), group in grouped.items():
        signatures = defaultdict(list)
        for item in group:
            signatures[row_signature(item.row)].append(item)
        if len(signatures) > 1:
            conflicts.append(
                {
                    "type": "duplicate-key-conflict",
                    "table": table,
                    "natural_key": json.loads(key),
                    "variants": [
                        {
                            "row": variant_group[0].row,
                            "sources": [variant.source_entry for variant in variant_group],
                            "statement_indexes": [variant.source_statement_index for variant in variant_group],
                        }
                        for variant_group in signatures.values()
                    ],
                }
            )
        representative_group = max(signatures.values(), key=len)
        representative = min(representative_group, key=lambda item: item.order_index)
        deduped.append(
            DedupedRecord(
                table=table,
                row=representative.row,
                key=key,
                sources=sorted({item.source_entry for item in group}),
                source_statement_indexes=sorted({item.source_statement_index for item in group}),
                representative_sql=representative.raw_sql,
                order_index=min(item.order_index for item in group),
            )
        )
    deduped.sort(key=lambda item: (TABLE_ORDER.index(item.table) if item.table in TABLE_ORDER else 999, item.order_index))
    return deduped, conflicts


def interval_end(value: Any) -> float:
    if value is None:
        return math.inf
    if isinstance(value, (int, float)):
        return float(value)
    return math.inf


def intervals_overlap(start_a: Any, end_a: Any, start_b: Any, end_b: Any) -> bool:
    if not isinstance(start_a, (int, float)) or not isinstance(start_b, (int, float)):
        return False
    a_end = interval_end(end_a)
    b_end = interval_end(end_b)
    return float(start_a) < b_end and float(start_b) < a_end


def temporal_sort_key(value: Any) -> tuple[int, float, str]:
    if isinstance(value, (int, float)):
        return (0, float(value), "")
    if value is None:
        return (1, math.inf, "")
    return (2, math.inf, json.dumps(canonicalize(value), sort_keys=True, ensure_ascii=False))


def detect_temporal_conflicts(records: list[DedupedRecord]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for table, rule in TEMPORAL_RULES.items():
        grouped: dict[str, list[DedupedRecord]] = defaultdict(list)
        for record in records:
            if record.table != table:
                continue
            group_key = json.dumps(
                {field: canonicalize(record.row.get(field)) for field in rule["group_by"]},
                sort_keys=True,
                ensure_ascii=False,
            )
            grouped[group_key].append(record)
        for group_key, group_records in grouped.items():
            ordered = sorted(
                group_records,
                key=lambda item: (temporal_sort_key(item.row.get(rule["start"])), item.order_index),
            )
            for i, left in enumerate(ordered):
                for right in ordered[i + 1 :]:
                    if not intervals_overlap(
                        left.row.get(rule["start"]),
                        left.row.get(rule["end"]),
                        right.row.get(rule["start"]),
                        right.row.get(rule["end"]),
                    ):
                        continue
                    left_compare = {field: canonicalize(left.row.get(field)) for field in rule["compare"]}
                    right_compare = {field: canonicalize(right.row.get(field)) for field in rule["compare"]}
                    if left_compare == right_compare:
                        continue
                    conflicts.append(
                        {
                            "type": "temporal-overlap",
                            "table": table,
                            "group": json.loads(group_key),
                            "left": {"row": left.row, "sources": left.sources},
                            "right": {"row": right.row, "sources": right.sources},
                        }
                    )
    return conflicts


def build_output_payload(records: list[DedupedRecord]) -> dict[str, list[dict[str, Any]]]:
    payload: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        payload[record.table].append(
            {
                "row": record.row,
                "sources": record.sources,
                "source_statement_indexes": record.source_statement_indexes,
            }
        )
    return dict(payload)


def write_clean_sql(records: list[DedupedRecord], output_path: Path) -> dict[str, int]:
    skipped_by_table: dict[str, int] = defaultdict(int)
    lines = ["SET search_path TO sports_conferences;", ""]
    for table in TABLE_ORDER:
        table_records = [record for record in records if record.table == table]
        if not table_records:
            continue
        lines.append(f"-- {table}")
        for record in table_records:
            sql = build_insert_sql(table, record.row)
            if sql is None:
                skipped_by_table[table] += 1
                continue
            lines.append(sql)
        lines.append("")
    output_path.write_text("\n".join(lines))
    return dict(skipped_by_table)


def summarize(records: list[ParsedRecord], deduped: list[DedupedRecord], conflicts: list[dict[str, Any]], skipped_sql: dict[str, int]) -> dict[str, Any]:
    raw_counts = defaultdict(int)
    deduped_counts = defaultdict(int)
    for record in records:
        raw_counts[record.table] += 1
    for record in deduped:
        deduped_counts[record.table] += 1
    return {
        "raw_record_count": len(records),
        "deduped_record_count": len(deduped),
        "conflict_count": len(conflicts),
        "raw_counts_by_table": dict(sorted(raw_counts.items())),
        "deduped_counts_by_table": dict(sorted(deduped_counts.items())),
        "skipped_clean_sql_rows_by_table": skipped_sql,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse, dedupe, and inspect LLM-generated SQL inserts.")
    parser.add_argument(
        "--input",
        default="llm-request/extracted_data_responses.json",
        help="Path to the raw LLM response JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default="llm-request/processed-sql",
        help="Directory where parsed artifacts should be written.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parsed_records = parse_records(input_path)
    deduped_records, key_conflicts = dedupe_records(parsed_records)
    temporal_conflicts = detect_temporal_conflicts(deduped_records)
    conflicts = key_conflicts + temporal_conflicts

    clean_sql_path = output_dir / "clean_load.sql"
    skipped_sql = write_clean_sql(deduped_records, clean_sql_path)

    structured_payload = build_output_payload(deduped_records)
    (output_dir / "deduped_records.json").write_text(json.dumps(structured_payload, indent=2, ensure_ascii=False))
    (output_dir / "conflicts.json").write_text(json.dumps(conflicts, indent=2, ensure_ascii=False))
    (output_dir / "summary.json").write_text(
        json.dumps(summarize(parsed_records, deduped_records, conflicts, skipped_sql), indent=2, ensure_ascii=False)
    )

    print(f"Parsed {len(parsed_records)} raw insert rows")
    print(f"Kept {len(deduped_records)} deduped rows")
    print(f"Detected {len(conflicts)} conflicts")
    print(f"Artifacts written to {output_dir}")


if __name__ == "__main__":
    main()
