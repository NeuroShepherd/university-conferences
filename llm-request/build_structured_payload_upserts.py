from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import finalize_executable_sql as final


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


def make_ref(table: str, key: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "ref", "table": table, "key": key}


def row_from_payload(columns: list[str], row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if isinstance(row, list):
        normalized_row = list(row)
        if len(normalized_row) < len(columns):
            normalized_row.extend([None] * (len(columns) - len(normalized_row)))
        elif len(normalized_row) > len(columns):
            normalized_row = normalized_row[: len(columns)]
        return dict(zip(columns, normalized_row, strict=True))
    if len(columns) == 1:
        return {columns[0]: row}
    raise ValueError(f"Unsupported row type: {type(row).__name__}")


def conference_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_conferences", {"current_conference_name": name})


def university_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_universities", {"current_university_name": name})


def sport_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_sports", {"sport_name_normalized": name})


def membership_type_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_membership_types", {"type_name": name})


def division_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_divisions", {"division_name": name})


def association_ref(name: Any) -> dict[str, Any] | None:
    if not isinstance(name, str) or not name.strip():
        return None
    return make_ref("dim_associations", {"association_name": name})


def state_ref(abbreviation: Any, state_name: Any = None) -> dict[str, Any] | None:
    if isinstance(abbreviation, str) and abbreviation.strip():
        return make_ref("dim_states", {"state_abbreviation": abbreviation})
    if isinstance(state_name, str) and state_name.strip():
        return make_ref("dim_states", {"state_name": state_name})
    return None


def city_ref(city_name: Any, state_abbreviation: Any, state_name: Any = None) -> dict[str, Any] | None:
    if not isinstance(city_name, str) or not city_name.strip():
        return None
    state = state_ref(state_abbreviation, state_name)
    if state is None:
        return None
    return make_ref("dim_cities", {"city_name": city_name, "state_id": state})


def affiliation_ref(affiliation_type: Any, denomination: Any) -> dict[str, Any] | None:
    if not isinstance(affiliation_type, str) or not affiliation_type.strip():
        return None
    return make_ref(
        "dim_affiliations",
        {"affiliation_type": affiliation_type, "denomination": denomination},
    )


def convert_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    if table == "dim_associations":
        return {"association_name": row.get("association_name")}
    if table == "dim_divisions":
        return {
            "division_name": row.get("division_name"),
            "association_id": association_ref(row.get("association_name")),
        }
    if table == "dim_states":
        return {
            "state_name": row.get("state_name"),
            "state_abbreviation": row.get("state_abbreviation"),
        }
    if table == "dim_cities":
        return {
            "city_name": row.get("city_name"),
            "state_id": state_ref(row.get("state_abbreviation"), row.get("state_name")),
        }
    if table == "dim_affiliations":
        return {
            "affiliation_type": row.get("affiliation_type"),
            "denomination": row.get("denomination"),
        }
    if table == "dim_sports":
        return {"sport_name_normalized": row.get("sport_name_normalized")}
    if table == "dim_membership_types":
        return {
            "type_name": row.get("type_name"),
            "description": row.get("description"),
        }
    if table == "dim_universities":
        return {
            "current_university_name": row.get("current_university_name"),
            "founded_year": row.get("founded_year"),
            "current_enrollment": row.get("current_enrollment"),
            "current_colors": row.get("current_colors"),
            "main_campus_city_id": city_ref(
                row.get("main_campus_city_name"),
                row.get("main_campus_state_abbreviation"),
                row.get("main_campus_state_name"),
            ),
            "main_campus_latitude": row.get("main_campus_latitude"),
            "main_campus_longitude": row.get("main_campus_longitude"),
            "current_affiliation_id": affiliation_ref(
                row.get("current_affiliation_type"),
                row.get("current_denomination"),
            ),
        }
    if table == "dim_conferences":
        return {
            "current_conference_name": row.get("current_conference_name"),
            "short_name": row.get("short_name"),
            "founded_year": row.get("founded_year"),
        }
    if table == "bridge_university_names":
        return {
            "university_id": university_ref(row.get("current_university_name")),
            "university_name": row.get("university_name"),
            "start_year": row.get("start_year"),
            "end_year": row.get("end_year"),
        }
    if table == "bridge_university_nicknames":
        return {
            "university_id": university_ref(row.get("current_university_name")),
            "nickname": row.get("nickname"),
            "start_year": row.get("start_year"),
            "end_year": row.get("end_year"),
            "sport_id": sport_ref(row.get("sport_name_normalized")),
        }
    if table == "bridge_university_sports":
        return {
            "university_id": university_ref(row.get("current_university_name")),
            "sport_id": sport_ref(row.get("sport_name_normalized")),
            "division_id": division_ref(row.get("division_name")),
            "start_year": row.get("start_year"),
            "end_year": row.get("end_year"),
            "is_varsity": row.get("is_varsity"),
            "sport_notes": row.get("sport_notes"),
        }
    if table == "bridge_conference_names":
        return {
            "conference_id": conference_ref(row.get("current_conference_name")),
            "conference_name": row.get("conference_name"),
            "start_year": row.get("start_year"),
            "end_year": row.get("end_year"),
        }
    if table == "bridge_conference_divisions":
        return {
            "conference_id": conference_ref(row.get("current_conference_name")),
            "division_id": division_ref(row.get("division_name")),
            "start_year": row.get("start_year"),
            "end_year": row.get("end_year"),
        }
    if table == "fact_membership":
        return {
            "university_id": university_ref(row.get("current_university_name")),
            "conference_id": conference_ref(row.get("current_conference_name")),
            "membership_type_id": membership_type_ref(row.get("membership_type_name")),
            "joined_year": row.get("joined_year"),
            "left_year": row.get("left_year"),
            "sport_id": sport_ref(row.get("sport_name_normalized")),
            "division_id": division_ref(row.get("division_name")),
            "primary_conference_for_sport_id": conference_ref(row.get("primary_conference_for_sport_name")),
            "previous_conference_id": conference_ref(row.get("previous_conference_name")),
            "next_conference_id": conference_ref(row.get("next_conference_name")),
            "reason_for_change": row.get("reason_for_change"),
            "membership_notes": row.get("membership_notes"),
        }
    raise KeyError(f"Unsupported table: {table}")


def parse_conference_payloads(input_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_payload = json.loads(input_path.read_text())
    records: list[dict[str, Any]] = []
    parse_errors: dict[str, str] = {}
    skipped_conferences: list[str] = []
    table_row_counts: dict[str, int] = defaultdict(int)

    for ingest_order, (conf_name, entry) in enumerate(raw_payload.items(), start=1):
        if entry.get("error") is not None:
            skipped_conferences.append(conf_name)
            continue

        cleaned_payload = entry.get("sql_text")
        if not isinstance(cleaned_payload, str) or not cleaned_payload.strip():
            skipped_conferences.append(conf_name)
            continue

        try:
            conference_payload = json.loads(strip_fences(cleaned_payload))
        except Exception as exc:
            parse_errors[conf_name] = str(exc)
            continue

        for table in final.TABLE_ORDER:
            table_payload = conference_payload.get(table)
            if not isinstance(table_payload, dict):
                continue

            columns = table_payload.get("columns", [])
            rows = table_payload.get("rows", [])
            if not isinstance(columns, list) or not isinstance(rows, list):
                parse_errors[conf_name] = f"invalid_table_payload:{table}"
                continue

            for row in rows:
                try:
                    row_obj = row_from_payload(columns, row)
                except Exception as exc:
                    parse_errors[f"{conf_name}:{table}"] = str(exc)
                    continue

                records.append(
                    {
                        "table": table,
                        "row": convert_row(table, row_obj),
                        "sources": [conf_name],
                        "source_statement_indexes": [],
                        "ingest_order": ingest_order,
                    }
                )
                table_row_counts[table] += 1

    return records, {
        "conference_count": len(raw_payload),
        "skipped_conferences": skipped_conferences,
        "parse_errors": parse_errors,
        "parsed_row_counts_by_table": dict(sorted(table_row_counts.items())),
    }


def merge_record_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(group, key=lambda item: item.get("ingest_order", 0))
    table = ordered[-1]["table"]
    merged_row: dict[str, Any] = {}

    for record in ordered:
        for column in final.TABLE_SCHEMAS[table]["columns"]:
            if column not in record["row"]:
                continue
            value = record["row"][column]
            if value is not None or column not in merged_row:
                merged_row[column] = value

    latest = ordered[-1].copy()
    latest["row"] = merged_row
    latest["sources"] = sorted({source for record in ordered for source in record.get("sources", [])})
    latest["merged_from"] = len(ordered)
    return latest


def merge_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = final.unique_key_for_table(record["table"], record["row"])
        grouped[(record["table"], key)].append(record)

    merged: list[dict[str, Any]] = []
    merged_counts: dict[str, int] = defaultdict(int)
    for (_, _), group in grouped.items():
        merged_record = merge_record_group(group)
        merged.append(merged_record)
        if len(group) > 1:
            merged_counts[merged_record["table"]] += len(group) - 1

    merged.sort(key=lambda record: (final.TABLE_ORDER.index(record["table"]), final.json_key(record["row"])))
    return merged, dict(sorted(merged_counts.items()))


def conflict_target_for_table(table: str) -> str:
    targets = {
        "dim_associations": "(association_name)",
        "dim_divisions": "(division_name)",
        "dim_states": "(state_abbreviation)",
        "dim_cities": "(city_name, state_id)",
        "dim_affiliations": "(affiliation_type)",
        "dim_sports": "(sport_name_normalized)",
        "dim_membership_types": "(type_name)",
        "dim_universities": "(current_university_name)",
        "dim_conferences": "(current_conference_name)",
        "bridge_university_names": "(university_id, university_name, start_year)",
        "bridge_university_nicknames": "(university_id, nickname, start_year, COALESCE(sport_id, 0))",
        "bridge_university_sports": "(university_id, sport_id, start_year, COALESCE(division_id, 0))",
        "bridge_conference_names": "(conference_id, conference_name, start_year)",
        "bridge_conference_divisions": "(conference_id, division_id, start_year)",
        "fact_membership": "(university_id, conference_id, COALESCE(sport_id, 0), division_id, joined_year, COALESCE(left_year, 9999))",
    }
    return targets[table]


def build_upsert_sql(table: str, row: dict[str, Any]) -> str | None:
    columns: list[str] = []
    values: list[str] = []
    required_ref_predicates: list[str] = []

    for column in final.TABLE_SCHEMAS[table]["columns"]:
        if column not in row:
            continue
        raw_value = row[column]
        sql_value = final.serialize_value(raw_value)
        if sql_value is None:
            return None
        columns.append(column)
        values.append(sql_value)
        if column in final.TABLE_SCHEMAS[table]["required"] and isinstance(raw_value, dict) and raw_value.get("kind") == "ref":
            required_ref_predicates.append(f"{sql_value} IS NOT NULL")

    if not columns:
        return None

    unique_fields = set(final.TABLE_SCHEMAS[table]["unique"])
    update_columns = [column for column in columns if column not in unique_fields]
    if update_columns:
        assignments = ", ".join(
            f"{column} = COALESCE(EXCLUDED.{column}, {table}.{column})"
            for column in update_columns
        )
        conflict_action = f"DO UPDATE SET {assignments}"
    else:
        conflict_action = "DO NOTHING"

    if required_ref_predicates:
        return (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"SELECT {', '.join(values)} "
            f"WHERE {' AND '.join(required_ref_predicates)} "
            f"ON CONFLICT {conflict_target_for_table(table)} {conflict_action};"
        )

    return (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)}) "
        f"ON CONFLICT {conflict_target_for_table(table)} {conflict_action};"
    )


def write_upsert_sql(records: list[dict[str, Any]], output_path: Path) -> dict[str, int]:
    skipped: dict[str, int] = defaultdict(int)
    lines = ["BEGIN;", "SET search_path TO sports_conferences;", ""]

    for table in final.TABLE_ORDER:
        table_records = [record for record in records if record["table"] == table]
        if not table_records:
            continue
        lines.append(f"-- {table}")
        for record in table_records:
            sql = build_upsert_sql(table, record["row"])
            if sql is None:
                skipped[table] += 1
                continue
            lines.append(sql)
        lines.append("")

    lines.append("COMMIT;")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return dict(sorted(skipped.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build executable upsert SQL from structured conference payloads.")
    parser.add_argument(
        "--input",
        default="llm-request/extracted_data_responses.json",
        help="Path to extracted conference response JSON.",
    )
    parser.add_argument(
        "--output-sql",
        default="llm-request/processed-json/final_upsert_load.sql",
        help="Path to write the executable upsert SQL script.",
    )
    parser.add_argument(
        "--output-summary",
        default="llm-request/processed-json/final_upsert_summary.json",
        help="Path to write the loader summary.",
    )
    args = parser.parse_args()

    raw_records, parse_summary = parse_conference_payloads(Path(args.input))
    aliased_records = [final.apply_aliases(record) for record in raw_records]

    valid_records: list[dict[str, Any]] = []
    skipped_reasons: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in aliased_records:
        transformed, reason = final.transform_record(record, {})
        if transformed is None:
            skipped_reasons[record["table"]][reason or "unknown"] += 1
            continue
        valid_records.append(transformed)

    merged_records, merged_counts = merge_records(valid_records)
    merged_records, pruned_unused_cities = final.prune_unused_dim_cities(merged_records)
    merged_records, pruned_unresolvable_university_names = final.prune_unresolvable_bridge_university_names(merged_records)
    merged_records, pruned_unresolvable_university_nicknames = final.prune_unresolvable_bridge_university_nicknames(merged_records)
    merged_records, pruned_unresolvable_university_sports, nulled_optional_sport_divisions = final.prune_unresolvable_bridge_university_sports(merged_records)
    merged_records, pruned_unresolvable_conference_names = final.prune_unresolvable_bridge_conference_names(merged_records)
    merged_records, pruned_unresolvable_conference_divisions = final.prune_unresolvable_bridge_conference_divisions(merged_records)

    sql_skipped = write_upsert_sql(merged_records, Path(args.output_sql))

    output_summary = {
        "parse_summary": parse_summary,
        "raw_records_considered": len(raw_records),
        "valid_records_after_normalization": len(valid_records),
        "merged_duplicate_rows_by_table": merged_counts,
        "records_pruned_after_reference_check": {
            "dim_cities": pruned_unused_cities,
            "bridge_university_names": pruned_unresolvable_university_names,
            "bridge_university_nicknames": pruned_unresolvable_university_nicknames,
            "bridge_university_sports": pruned_unresolvable_university_sports,
            "bridge_conference_names": pruned_unresolvable_conference_names,
            "bridge_conference_divisions": pruned_unresolvable_conference_divisions,
        },
        "optional_references_removed": {
            "bridge_university_sports.division_id": nulled_optional_sport_divisions,
        },
        "records_in_final_sql": len(merged_records) - sum(sql_skipped.values()),
        "records_skipped_during_sql_generation": sql_skipped,
        "skipped_reasons": {table: dict(reasons) for table, reasons in skipped_reasons.items()},
    }

    summary_path = Path(args.output_summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(output_summary, indent=2, ensure_ascii=False))

    print(f"Wrote SQL to {args.output_sql}")
    print(f"Wrote summary to {args.output_summary}")
    print(json.dumps(output_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
