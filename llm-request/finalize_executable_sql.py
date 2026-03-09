from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from copy import deepcopy
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

TABLE_SCHEMAS: dict[str, dict[str, Any]] = {
    "dim_associations": {
        "pk": "association_id",
        "columns": ["association_name"],
        "required": ["association_name"],
        "unique": ["association_name"],
    },
    "dim_divisions": {
        "pk": "division_id",
        "columns": ["division_name", "association_id"],
        "required": ["division_name", "association_id"],
        "unique": ["division_name"],
    },
    "dim_states": {
        "pk": "state_id",
        "columns": ["state_name", "state_abbreviation"],
        "required": ["state_name", "state_abbreviation"],
        "unique": ["state_abbreviation"],
    },
    "dim_cities": {
        "pk": "city_id",
        "columns": ["city_name", "state_id"],
        "required": ["city_name", "state_id"],
        "unique": ["city_name", "state_id"],
    },
    "dim_affiliations": {
        "pk": "affiliation_id",
        "columns": ["affiliation_type", "denomination"],
        "required": ["affiliation_type"],
        "unique": ["affiliation_type"],
    },
    "dim_sports": {
        "pk": "sport_id",
        "columns": ["sport_name_normalized"],
        "required": ["sport_name_normalized"],
        "unique": ["sport_name_normalized"],
    },
    "dim_membership_types": {
        "pk": "membership_type_id",
        "columns": ["type_name", "description"],
        "required": ["type_name"],
        "unique": ["type_name"],
    },
    "dim_universities": {
        "pk": "university_id",
        "columns": [
            "current_university_name",
            "founded_year",
            "current_enrollment",
            "current_colors",
            "main_campus_city_id",
            "main_campus_latitude",
            "main_campus_longitude",
            "current_affiliation_id",
        ],
        "required": ["current_university_name"],
        "unique": ["current_university_name"],
    },
    "dim_conferences": {
        "pk": "conference_id",
        "columns": ["current_conference_name", "short_name", "founded_year"],
        "required": ["current_conference_name"],
        "unique": ["current_conference_name"],
    },
    "bridge_university_names": {
        "pk": "university_name_history_id",
        "columns": ["university_id", "university_name", "start_year", "end_year"],
        "required": ["university_id", "university_name", "start_year"],
        "unique": ["university_id", "university_name", "start_year"],
    },
    "bridge_university_nicknames": {
        "pk": "uni_nickname_history_id",
        "columns": ["university_id", "nickname", "start_year", "end_year", "sport_id"],
        "required": ["university_id", "nickname", "start_year"],
        "unique": ["university_id", "nickname", "start_year", "sport_id"],
    },
    "bridge_university_sports": {
        "pk": "university_sport_history_id",
        "columns": ["university_id", "sport_id", "division_id", "start_year", "end_year", "is_varsity", "sport_notes"],
        "required": ["university_id", "sport_id", "start_year", "is_varsity"],
        "unique": ["university_id", "sport_id", "start_year", "division_id"],
    },
    "bridge_conference_names": {
        "pk": "conference_name_history_id",
        "columns": ["conference_id", "conference_name", "start_year", "end_year"],
        "required": ["conference_id", "conference_name", "start_year"],
        "unique": ["conference_id", "conference_name", "start_year"],
    },
    "bridge_conference_divisions": {
        "pk": "conf_div_history_id",
        "columns": ["conference_id", "division_id", "start_year", "end_year"],
        "required": ["conference_id", "division_id", "start_year"],
        "unique": ["conference_id", "division_id", "start_year"],
    },
    "fact_membership": {
        "pk": "membership_id",
        "columns": [
            "university_id",
            "conference_id",
            "membership_type_id",
            "joined_year",
            "left_year",
            "sport_id",
            "division_id",
            "primary_conference_for_sport_id",
            "previous_conference_id",
            "next_conference_id",
            "reason_for_change",
            "membership_notes",
        ],
        "required": ["university_id", "conference_id", "membership_type_id", "joined_year", "division_id"],
        "unique": ["university_id", "conference_id", "sport_id", "division_id", "joined_year", "left_year"],
    },
}

FK_TABLES: dict[str, dict[str, str]] = {
    "dim_divisions": {"association_id": "dim_associations"},
    "dim_cities": {"state_id": "dim_states"},
    "dim_universities": {
        "main_campus_city_id": "dim_cities",
        "current_affiliation_id": "dim_affiliations",
    },
    "bridge_university_names": {"university_id": "dim_universities"},
    "bridge_university_nicknames": {
        "university_id": "dim_universities",
        "sport_id": "dim_sports",
    },
    "bridge_university_sports": {
        "university_id": "dim_universities",
        "sport_id": "dim_sports",
        "division_id": "dim_divisions",
    },
    "bridge_conference_names": {"conference_id": "dim_conferences"},
    "bridge_conference_divisions": {
        "conference_id": "dim_conferences",
        "division_id": "dim_divisions",
    },
    "fact_membership": {
        "university_id": "dim_universities",
        "conference_id": "dim_conferences",
        "membership_type_id": "dim_membership_types",
        "sport_id": "dim_sports",
        "division_id": "dim_divisions",
        "primary_conference_for_sport_id": "dim_conferences",
        "previous_conference_id": "dim_conferences",
        "next_conference_id": "dim_conferences",
    },
}

REF_KEY_FIELDS: dict[str, list[str]] = {
    "dim_associations": ["association_name"],
    "dim_divisions": ["division_name"],
    "dim_states": ["state_abbreviation", "state_name"],
    "dim_cities": ["city_name", "state_id"],
    "dim_affiliations": ["affiliation_type"],
    "dim_sports": ["sport_name_normalized"],
    "dim_membership_types": ["type_name"],
    "dim_universities": ["current_university_name"],
    "dim_conferences": ["current_conference_name"],
}

ASSOCIATION_ALIASES = {
    "national collegiate athletic association": "NCAA",
    "national association of intercollegiate athletics": "NAIA",
    "national junior college athletic association": "NJCAA",
    "united states collegiate athletic association": "USCAA",
    "national christian college athletic association": "NCCAA",
}

MEMBERSHIP_TYPE_ALIASES = {
    "full member": "Full Member",
    "full member (all sports)": "Full Member",
    "full member (non-football)": "Full Member (non-football)",
    "associate member (football only)": "Associate Member (Football only)",
    "associate member (men's ice hockey only)": "Associate Member (Men's Ice Hockey only)",
    "associate member (other sport)": "Associate Member (Sport-Specific)",
    "associate member (sport)": "Associate Member (Sport-Specific)",
}

AFFILIATION_TYPE_ALIASES = {
    "christian & missionary alliance": "Christian and Missionary Alliance",
    "christian and missionary alliance": "Christian and Missionary Alliance",
    "federal/military": "Federal/Military",
    "private for-profit": "Private (For-Profit)",
    "private (for-profit)": "Private (For-Profit)",
    "private - non-denominational": "Private - Nondenominational",
    "private - nondenominational": "Private - Nondenominational",
    "private - nonsectarian": "Private (Nonsectarian)",
    "private": "Private",
    "quasi-governmental": "Quasigovernmental",
    "quasigovernmental": "Quasigovernmental",
    "tribal college": "Tribal College",
}

STATE_NAME_TO_ABBREV = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "washington, d.c.": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "british columbia": "BC",
    "ontario": "ON",
    "quebec": "QC",
    "alberta": "AB",
    "manitoba": "MB",
    "new brunswick": "NB",
    "nova scotia": "NS",
    "saskatchewan": "SK",
    "prince edward island": "PE",
    "newfoundland and labrador": "NL",
}

SPORT_EXACT_ALIASES = {
    "acrobatics and tumbling": "Acrobatics & Tumbling",
    "acrobatics & tumbling": "Acrobatics & Tumbling",
    "all sports (default)": "All Sports",
    "all sports": "All Sports",
    "archery": "Archery",
    "athletics (general)": "Athletics (General)",
    "baseball": "Baseball",
    "basketball": "Basketball",
    "beach volleyball": "Beach Volleyball",
    "bowling": "Bowling",
    "competitive cheer": "Competitive Cheer",
    "competitive dance": "Competitive Dance",
    "cricket": "Cricket",
    "cross country": "Cross Country",
    "cross-country": "Cross Country",
    "equestrian": "Equestrian",
    "esports": "Esports",
    "fencing": "Fencing",
    "field hockey": "Field Hockey",
    "football": "Football",
    "general athletics": "General Athletics",
    "general sports": "General Sports",
    "general varsity sports": "General Varsity Sports",
    "golf": "Golf",
    "gymnastics": "Gymnastics",
    "ice hockey": "Ice Hockey",
    "indoor track and field": "Indoor Track & Field",
    "indoor track & field": "Indoor Track & Field",
    "lacrosse": "Lacrosse",
    "men's and women's swimming": "Men's & Women's Swimming",
    "men's and women's swimming & diving": "Men's & Women's Swimming & Diving",
    "outdoor track and field": "Outdoor Track & Field",
    "outdoor track & field": "Outdoor Track & Field",
    "overall athletics": "Overall Athletics",
    "rifle": "Rifle",
    "rowing": "Rowing",
    "shotgun sports": "Shotgun Sports",
    "skiing": "Skiing",
    "soccer": "Soccer",
    "softball": "Softball",
    "stunt": "STUNT",
    "swimming": "Swimming",
    "swimming and diving": "Swimming & Diving",
    "swimming & diving": "Swimming & Diving",
    "tennis": "Tennis",
    "men's track & field outdoor": "Men's Outdoor Track & Field",
    "women's sports (general)": "Women's Sports (General)",
    "women's track & field outdoor": "Women's Outdoor Track & Field",
    "track and field": "Track & Field",
    "track & field": "Track & Field",
    "triathlon": "Triathlon",
    "volleyball": "Volleyball",
    "water polo": "Water Polo",
    "wrestling": "Wrestling",
}

GENDER_PREFIX_MAP = {
    "men": "Men's",
    "men's": "Men's",
    "mens": "Men's",
    "m": "Men's",
    "women": "Women's",
    "women's": "Women's",
    "womens": "Women's",
    "w": "Women's",
}


def normalize_space(value: str) -> str:
    return " ".join(str(value).replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'").split()).strip()


def title_case_preserving_small_words(value: str) -> str:
    small_words = {"and", "of", "the", "in", "for", "to", "a", "an"}
    parts: list[str] = []
    for idx, token in enumerate(value.split(" ")):
        if not token:
            continue
        lowered = token.casefold()
        if idx > 0 and lowered in small_words:
            parts.append(lowered)
        elif "/" in token:
            parts.append("/".join(piece.capitalize() for piece in token.split("/")))
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def normalize_state_abbreviation(value: str) -> str:
    return normalize_space(value).replace(".", "").upper()


def normalize_state_name(value: str) -> str:
    clean = normalize_space(value)
    lowered = clean.casefold()
    if lowered == "washington, d.c.":
        return "District of Columbia"
    return title_case_preserving_small_words(clean)


def normalize_affiliation_type(value: str) -> str | None:
    clean = normalize_space(value)
    if not clean:
        return None
    lowered = clean.casefold()
    if lowered in AFFILIATION_TYPE_ALIASES:
        return AFFILIATION_TYPE_ALIASES[lowered]
    if clean.islower():
        clean = title_case_preserving_small_words(clean)
    clean = clean.replace("Lds Church", "LDS Church")
    clean = clean.replace("Hbcu", "HBCU")
    clean = clean.replace("Usa", "USA")
    return clean


def normalize_denomination(value: str) -> str | None:
    clean = normalize_space(value)
    if not clean or clean == "NULL":
        return None
    lowered = clean.casefold()
    exact = {
        "non-denominational": "Nondenominational",
        "pcusa": "PCUSA",
        "jesuit": "Jesuit",
        "military": "Military",
        "art school": "Art School",
        "moravian church": "Moravian Church",
        "church of the nazarene": "Church of the Nazarene",
        "assemblies of god usa": "Assemblies of God USA",
        "american baptist churches usa": "American Baptist Churches USA",
        "evangelical lutheran church in america": "Evangelical Lutheran Church in America",
        "historically black colleges and universities (hbcu)": "Historically Black Colleges and Universities (HBCU)",
    }
    if lowered in exact:
        return exact[lowered]
    if clean.islower():
        return title_case_preserving_small_words(clean)
    return clean


def normalize_membership_type_name(value: str) -> str | None:
    clean = normalize_space(value)
    if not clean:
        return None
    lowered = clean.casefold()
    if lowered in MEMBERSHIP_TYPE_ALIASES:
        return MEMBERSHIP_TYPE_ALIASES[lowered]

    exact = {
        "full": "Full Member",
        "full member": "Full Member",
        "full (all sports)": "Full Member",
        "full (general)": "Full Member",
        "default conference membership (all sports)": "Full Member",
        "future full member": "Future Full Member",
        "future full member (all sports)": "Future Full Member",
        "future full member (non-football)": "Future Full Member (non-football)",
        "future full member (except football)": "Future Full Member (non-football)",
        "full member (except football)": "Full Member (non-football)",
        "full (non-football)": "Full Member (non-football)",
        "full member (non-football)": "Full Member (non-football)",
        "associate": "Associate Member",
        "associate member": "Associate Member",
        "associate (football only)": "Associate Member (Football only)",
        "associate (sport)": "Associate Member (Sport-Specific)",
        "associate (sport specific)": "Associate Member (Sport-Specific)",
        "associate (sport-specific)": "Associate Member (Sport-Specific)",
        "associate (specific sport)": "Associate Member (Sport-Specific)",
        "associate member (sport specific)": "Associate Member (Sport-Specific)",
        "associate member (sport-specific)": "Associate Member (Sport-Specific)",
        "associate member (specific sport)": "Associate Member (Sport-Specific)",
        "associate member (other sport)": "Associate Member (Sport-Specific)",
        "associate member (other sports)": "Associate Member (Sport-Specific)",
        "associate (other sport)": "Associate Member (Sport-Specific)",
        "associate (other sport(s))": "Associate Member (Sport-Specific)",
        "affiliate member (sport-specific)": "Associate Member (Sport-Specific)",
        "future associate": "Future Associate Member",
        "future affiliate member": "Future Associate Member",
        "future associate member": "Future Associate Member",
        "future associate member (sport)": "Future Associate Member (Sport-Specific)",
        "future associate member (sport-specific)": "Future Associate Member (Sport-Specific)",
        "former associate": "Former Associate Member",
        "former associate member": "Former Associate Member",
        "former associate member (sport)": "Former Associate Member",
        "former full": "Former Full Member",
        "former full member": "Former Full Member",
        "former full member (all sports)": "Former Full Member",
        "provisional": "Provisional Member",
        "provisional member": "Provisional Member",
        "transitional": "Transitioning Member",
        "transitioning member": "Transitioning Member",
        "other conference": "Other Conference",
        "other conference membership": "Other Conference",
        "other conference 1": "Other Conference",
        "other conference 2": "Other Conference",
        "closed": "Closed Institution",
        "closed institution": "Closed Institution",
        "closed university": "Closed Institution",
        "former (closed)": "Closed Institution",
        "left conference (closed)": "Closed Institution",
        "no athletics": "Dropped Athletics",
        "discontinued program": "Dropped Athletics",
        "naia independent": "NAIA Independent",
        "independent (naia)": "NAIA Independent",
        "d-ii independent": "NCAA Division II Independent",
        "independent (ncaa d-ii)": "NCAA Division II Independent",
        "ncaa division ii independent": "NCAA Division II Independent",
        "d-iii independent": "NCAA Division III Independent",
        "ncaa division iii independent": "NCAA Division III Independent",
        "independent (ncaa d-i)": "NCAA Division I Independent",
        "ncaa division i independent": "NCAA Division I Independent",
        "national christian college athletic association independent": "NCCAA Independent",
    }
    if lowered in exact:
        return exact[lowered]

    if re.fullmatch(r"associate member \((football|football-only|football only)\)", lowered) or re.fullmatch(r"associate \((football|football-only|football only)\)", lowered):
        return "Associate Member (Football only)"
    if re.fullmatch(r"affiliate \(football\)", lowered):
        return "Associate Member (Football only)"
    if re.fullmatch(r"associate member \((men'?s ice hockey only)\)", lowered):
        return "Associate Member (Men's Ice Hockey only)"
    if re.fullmatch(r"associate( member)? \((men'?s .+|women'?s .+|beach volleyball|softball|basketball only|bowling)\)", lowered):
        if "football" in lowered:
            return "Associate Member (Football only)"
        return "Associate Member (Sport-Specific)"
    if re.fullmatch(r"affiliate member \((dual sport|sport-specific)\)", lowered):
        return "Associate Member (Sport-Specific)"
    if re.fullmatch(r"future associate member \((sport|sport-specific)\)", lowered):
        return "Future Associate Member (Sport-Specific)"

    return clean.title() if clean.islower() else clean


def normalize_ref_key(table: str, key: dict[str, Any]) -> dict[str, Any]:
    if table == "dim_states":
        state_abbreviation = key.get("state_abbreviation")
        if isinstance(state_abbreviation, str) and state_abbreviation:
            return {"state_abbreviation": normalize_state_abbreviation(state_abbreviation)}
        state_name = key.get("state_name")
        if isinstance(state_name, str) and state_name:
            normalized_name = normalize_state_name(state_name)
            mapped_abbrev = STATE_NAME_TO_ABBREV.get(normalized_name.casefold())
            if mapped_abbrev:
                return {"state_abbreviation": mapped_abbrev}
            return {"state_name": normalized_name}
    if table == "dim_affiliations" and "affiliation_type" in key:
        return {"affiliation_type": normalize_affiliation_type(str(key["affiliation_type"]))}
    if table == "dim_membership_types" and "type_name" in key:
        return {"type_name": normalize_membership_type_name(str(key["type_name"]))}
    if table == "dim_sports" and "sport_name_normalized" in key:
        return {"sport_name_normalized": normalize_sport_name(str(key["sport_name_normalized"]))}
    return key


def titleize_words(value: str) -> str:
    parts: list[str] = []
    for token in value.split(" "):
        lowered = token.casefold()
        if lowered == "&":
            parts.append("&")
        elif lowered == "stunt":
            parts.append("STUNT")
        elif lowered == "esports":
            parts.append("Esports")
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def normalize_sport_core(value: str) -> str:
    clean = normalize_space(value)
    lowered = clean.casefold()
    lowered = lowered.replace("’", "'")
    lowered = re.sub(r"\band\b", "&", lowered)
    lowered = re.sub(r"\s*&\s*", " & ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip(" ,")
    if lowered in SPORT_EXACT_ALIASES:
        return SPORT_EXACT_ALIASES[lowered]
    return titleize_words(lowered)


def normalize_sport_name(value: str) -> str | None:
    clean = normalize_space(value)
    clean = clean.replace("\\'", "'")
    if not clean:
        return None
    if any(marker in clean for marker in ["), (", "''), (''", "'), ('"]):
        return None

    lowered = clean.casefold()
    lowered = lowered.replace("’", "'")
    lowered = re.sub(r"\s+", " ", lowered).strip()

    if lowered in SPORT_EXACT_ALIASES:
        return SPORT_EXACT_ALIASES[lowered]

    combined_match = re.fullmatch(r"(men'?s|women'?s) and (men'?s|women'?s) (.+)", lowered)
    if combined_match:
        core = normalize_sport_core(combined_match.group(3))
        if {combined_match.group(1)[0], combined_match.group(2)[0]} == {"m", "w"}:
            return f"Men's & Women's {core}"

    track_gender_match = re.fullmatch(r"track and field \((indoor|outdoor), (men'?s|women'?s)\)", lowered)
    if track_gender_match:
        season = track_gender_match.group(1).capitalize()
        gender_token = track_gender_match.group(2)
        gender = GENDER_PREFIX_MAP.get(gender_token, GENDER_PREFIX_MAP.get(gender_token.replace("'", "")))
        if gender is None:
            return None
        return f"{gender} {season} Track & Field"

    for pattern, fixed_prefix in [
        (r"(.+?) \((men'?s|men|m)\)$", "Men's"),
        (r"(.+?) \((women'?s|women|w)\)$", "Women's"),
    ]:
        match = re.fullmatch(pattern, lowered)
        if match:
            core = normalize_sport_core(match.group(1))
            return f"{fixed_prefix} {core}"

    hyphen_match = re.fullmatch(r"(.+?) - (men|women)$", lowered)
    if hyphen_match:
        gender = GENDER_PREFIX_MAP[hyphen_match.group(2)]
        core = normalize_sport_core(hyphen_match.group(1))
        return f"{gender} {core}"

    prefix_match = re.fullmatch(r"(men'?s|women'?s) (.+)$", lowered)
    if prefix_match:
        gender_token = prefix_match.group(1)
        gender = GENDER_PREFIX_MAP.get(gender_token, GENDER_PREFIX_MAP.get(gender_token.replace("'", "")))
        if gender:
            core = normalize_sport_core(prefix_match.group(2))
            return f"{gender} {core}"

    explicit_gender = re.fullmatch(r"(men|women)\'s (.+)", lowered)
    if explicit_gender:
        gender = GENDER_PREFIX_MAP[f"{explicit_gender.group(1)}'s"]
        core = normalize_sport_core(explicit_gender.group(2))
        return f"{gender} {core}"

    return normalize_sport_core(clean)


def alias_string(table: str, field: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    clean = normalize_space(value)
    lowered = clean.casefold()
    if table == "dim_associations" and field == "association_name":
        return ASSOCIATION_ALIASES.get(lowered, clean)
    if table == "dim_states" and field == "state_abbreviation":
        return normalize_state_abbreviation(clean)
    if table == "dim_states" and field == "state_name":
        return normalize_state_name(clean)
    if table == "dim_membership_types" and field == "type_name":
        return normalize_membership_type_name(clean)
    if table == "dim_membership_types" and field == "description":
        return None if clean == "NULL" else clean
    if table == "dim_affiliations" and field == "affiliation_type":
        return normalize_affiliation_type(clean)
    if table == "dim_affiliations" and field == "denomination":
        return normalize_denomination(clean)
    if table == "dim_sports" and field == "sport_name_normalized":
        return normalize_sport_name(clean)
    return clean


def is_unresolved(value: Any) -> bool:
    if isinstance(value, dict):
        kind = value.get("kind")
        if kind in {"unresolved_var", "sql", "call", "empty"}:
            return True
        if kind == "ref":
            return any(is_unresolved(v) for v in value.get("key", {}).values())
    return False


def canonical_key_obj(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_space(value).casefold()
    if isinstance(value, list):
        return [canonical_key_obj(v) for v in value]
    if isinstance(value, dict):
        if value.get("kind") == "ref" and "table" in value:
            ref_table = value["table"]
            raw_key = value.get("key", {})
            canonical_key = {k: canonical_key_obj(v) for k, v in sorted(raw_key.items())}
            normalized_key = normalize_ref_key(ref_table, canonical_key)
            return {
                "kind": "ref",
                "table": ref_table,
                "key": {k: canonical_key_obj(v) for k, v in sorted(normalized_key.items())},
            }
        return {k: canonical_key_obj(v) for k, v in sorted(value.items())}
    return value


def json_key(value: Any) -> str:
    return json.dumps(canonical_key_obj(value), sort_keys=True, ensure_ascii=False)


def load_records(input_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(input_path.read_text())
    rows: list[dict[str, Any]] = []
    for table, items in payload.items():
        if table not in TABLE_SCHEMAS:
            continue
        for item in items:
            rows.append(
                {
                    "table": table,
                    "row": item["row"],
                    "sources": item.get("sources", []),
                    "source_statement_indexes": item.get("source_statement_indexes", []),
                }
            )
    return rows


def apply_aliases_to_value(ref_table: str, field: str, value: Any) -> Any:
    if isinstance(value, dict) and value.get("kind") == "ref":
        nested_key = {k: apply_aliases_to_value(value["table"], k, v) for k, v in value.get("key", {}).items()}
        return {
            "kind": "ref",
            "table": value["table"],
            "key": normalize_ref_key(value["table"], nested_key),
        }
    return alias_string(ref_table, field, value)


def apply_aliases(record: dict[str, Any]) -> dict[str, Any]:
    table = record["table"]
    row = deepcopy(record["row"])
    aliased: dict[str, Any] = {}
    for field, value in row.items():
        if isinstance(value, dict) and value.get("kind") == "ref":
            nested_key = {k: apply_aliases_to_value(value["table"], k, v) for k, v in value.get("key", {}).items()}
            aliased[field] = {
                "kind": "ref",
                "table": value["table"],
                "key": normalize_ref_key(value["table"], nested_key),
            }
        else:
            aliased[field] = alias_string(table, field, value)
    record = record.copy()
    record["row"] = aliased
    return record


def build_id_maps(records: list[dict[str, Any]]) -> dict[str, dict[int, dict[str, Any]]]:
    candidates: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        table = record["table"]
        schema = TABLE_SCHEMAS[table]
        pk = schema["pk"]
        row = record["row"]
        pk_value = row.get(pk)
        if not isinstance(pk_value, int):
            continue
        ref_fields = REF_KEY_FIELDS.get(table)
        if not ref_fields:
            continue
        ref_key: dict[str, Any] = {}
        for field in ref_fields:
            if field not in row:
                continue
            value = row[field]
            if value is None or is_unresolved(value):
                continue
            ref_key[field] = value
        if not ref_key:
            continue
        candidates[table][pk_value].append(ref_key)

    resolved: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for table, by_id in candidates.items():
        for pk_value, refs in by_id.items():
            unique = {json_key(ref): ref for ref in refs}
            if len(unique) == 1:
                resolved[table][pk_value] = next(iter(unique.values()))
    return dict(resolved)


def resolve_ref_value(value: Any, ref_table: str, id_maps: dict[str, dict[int, dict[str, Any]]]) -> Any:
    if value is None:
        return None
    if isinstance(value, int):
        mapped = id_maps.get(ref_table, {}).get(value)
        if mapped is None:
            return None
        return {"kind": "ref", "table": ref_table, "key": deepcopy(mapped)}
    if isinstance(value, dict) and value.get("kind") == "ref":
        key: dict[str, Any] = {}
        for key_field, key_value in value.get("key", {}).items():
            nested_ref_table = FK_TABLES.get(ref_table, {}).get(key_field)
            if nested_ref_table:
                resolved_nested = resolve_ref_value(key_value, nested_ref_table, id_maps)
                if resolved_nested is None and key_value is not None:
                    return None
                key[key_field] = resolved_nested
            else:
                if is_unresolved(key_value):
                    return None
                key[key_field] = apply_alias_to_scalar_ref(ref_table, key_field, key_value)
        return {"kind": "ref", "table": ref_table, "key": normalize_ref_key(ref_table, key)}
    if is_unresolved(value):
        return None
    return value


def apply_alias_to_scalar_ref(table: str, field: str, value: Any) -> Any:
    if isinstance(value, str):
        return alias_string(table, field, value)
    return value


def transform_record(record: dict[str, Any], id_maps: dict[str, dict[int, dict[str, Any]]]) -> tuple[dict[str, Any] | None, str | None]:
    table = record["table"]
    schema = TABLE_SCHEMAS[table]
    row = deepcopy(record["row"])

    if any(is_unresolved(value) for value in row.values()):
        return None, "contains_unresolved_expression"

    row.pop(schema["pk"], None)
    transformed: dict[str, Any] = {}

    for field in schema["columns"]:
        if field not in row:
            continue
        value = row[field]
        ref_table = FK_TABLES.get(table, {}).get(field)
        if ref_table:
            resolved = resolve_ref_value(value, ref_table, id_maps)
            if resolved is None and value is not None:
                return None, f"unresolved_foreign_key:{field}"
            transformed[field] = resolved
        else:
            transformed[field] = alias_string(table, field, value)

    for required in schema["required"]:
        if required not in transformed or transformed[required] is None:
            return None, f"missing_required:{required}"

    if table == "dim_states" and transformed.get("state_abbreviation") is None:
        return None, "missing_required:state_abbreviation"

    if table == "dim_affiliations" and transformed.get("denomination") == "NULL":
        transformed["denomination"] = None

    if table == "dim_affiliations":
        if transformed.get("affiliation_type") == "Federal" and transformed.get("denomination") == "Military":
            transformed["affiliation_type"] = "Federal/Military"
            transformed["denomination"] = None
        if transformed.get("affiliation_type") == "Private" and transformed.get("denomination") == "Nonsectarian":
            transformed["affiliation_type"] = "Private (Nonsectarian)"
            transformed["denomination"] = None

    record = record.copy()
    record["row"] = transformed
    return record, None


def row_score(record: dict[str, Any]) -> tuple[int, int, int]:
    row = record["row"]
    non_null = sum(1 for value in row.values() if value is not None)
    source_count = len(record.get("sources", []))
    specificity_penalty = 0
    if record["table"] == "dim_affiliations" and row.get("denomination") is not None:
        specificity_penalty = -1
    return (source_count, non_null, specificity_penalty)


def unique_key_for_table(table: str, row: dict[str, Any]) -> str:
    unique_fields = TABLE_SCHEMAS[table]["unique"]
    key = {field: row.get(field) for field in unique_fields}
    return json_key(key)


def choose_representatives(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(record["table"], unique_key_for_table(record["table"], record["row"]))].append(record)

    chosen: list[dict[str, Any]] = []
    dropped_counts: dict[str, int] = defaultdict(int)
    for _, group in grouped.items():
        best = max(group, key=row_score)
        chosen.append(best)
        dropped_counts[best["table"]] += max(0, len(group) - 1)
    chosen.sort(key=lambda rec: (TABLE_ORDER.index(rec["table"]), json_key(rec["row"])))
    return chosen, dict(dropped_counts)


def prune_unused_dim_cities(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    referenced_city_keys: set[str] = set()
    for record in records:
        if record["table"] != "dim_universities":
            continue
        city_ref = record["row"].get("main_campus_city_id")
        if isinstance(city_ref, dict) and city_ref.get("kind") == "ref" and city_ref.get("table") == "dim_cities":
            referenced_city_keys.add(json_key(city_ref.get("key", {})))

    if not referenced_city_keys:
        return records, 0

    kept: list[dict[str, Any]] = []
    pruned = 0
    for record in records:
        if record["table"] != "dim_cities":
            kept.append(record)
            continue
        row_key = {field: record["row"].get(field) for field in REF_KEY_FIELDS["dim_cities"]}
        if json_key(row_key) in referenced_city_keys:
            kept.append(record)
        else:
            pruned += 1
    return kept, pruned


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ref_to_sql(ref: dict[str, Any]) -> str | None:
    table = ref["table"]
    key = ref.get("key", {})
    if table == "dim_associations" and "association_name" in key:
        val = sql_literal(str(key["association_name"]))
        return f"(SELECT association_id FROM dim_associations WHERE LOWER(association_name) = LOWER({val}))"
    if table == "dim_divisions" and "division_name" in key:
        val = sql_literal(str(key["division_name"]))
        return f"(SELECT division_id FROM dim_divisions WHERE LOWER(division_name) = LOWER({val}))"
    if table == "dim_states":
        if "state_abbreviation" in key and key["state_abbreviation"] is not None:
            val = sql_literal(str(key["state_abbreviation"]))
            return f"(SELECT state_id FROM dim_states WHERE LOWER(state_abbreviation) = LOWER({val}))"
        if "state_name" in key:
            val = sql_literal(str(key["state_name"]))
            return f"(SELECT state_id FROM dim_states WHERE LOWER(state_name) = LOWER({val}))"
    if table == "dim_cities" and "city_name" in key and "state_id" in key:
        city = sql_literal(str(key["city_name"]))
        state_sql = serialize_value(key["state_id"])
        if state_sql is None:
            return None
        return f"(SELECT city_id FROM dim_cities WHERE LOWER(city_name) = LOWER({city}) AND state_id = {state_sql})"
    if table == "dim_affiliations" and "affiliation_type" in key:
        val = sql_literal(str(key["affiliation_type"]))
        return f"(SELECT affiliation_id FROM dim_affiliations WHERE LOWER(affiliation_type) = LOWER({val}))"
    if table == "dim_universities" and "current_university_name" in key:
        val = sql_literal(str(key["current_university_name"]))
        return f"(SELECT university_id FROM dim_universities WHERE LOWER(current_university_name) = LOWER({val}))"
    if table == "dim_conferences" and "current_conference_name" in key:
        val = sql_literal(str(key["current_conference_name"]))
        return f"(SELECT conference_id FROM dim_conferences WHERE LOWER(current_conference_name) = LOWER({val}))"
    if table == "dim_sports" and "sport_name_normalized" in key:
        val = sql_literal(str(key["sport_name_normalized"]))
        return f"(SELECT sport_id FROM dim_sports WHERE LOWER(sport_name_normalized) = LOWER({val}))"
    if table == "dim_membership_types" and "type_name" in key:
        val = sql_literal(str(key["type_name"]))
        return f"(SELECT membership_type_id FROM dim_membership_types WHERE LOWER(type_name) = LOWER({val}))"
    return None


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
        return sql_literal(value)
    if isinstance(value, dict) and value.get("kind") == "ref":
        return ref_to_sql(value)
    return None


def build_insert_sql(table: str, row: dict[str, Any]) -> str | None:
    columns = []
    values = []
    for column in TABLE_SCHEMAS[table]["columns"]:
        if column not in row:
            continue
        sql_value = serialize_value(row[column])
        if sql_value is None:
            return None
        columns.append(column)
        values.append(sql_value)
    if not columns:
        return None
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)}) ON CONFLICT DO NOTHING;"


def write_sql(records: list[dict[str, Any]], output_path: Path) -> dict[str, int]:
    lines = ["BEGIN;", "SET search_path TO sports_conferences;", ""]
    skipped: dict[str, int] = defaultdict(int)
    for table in TABLE_ORDER:
        table_records = [record for record in records if record["table"] == table]
        if not table_records:
            continue
        lines.append(f"-- {table}")
        for record in table_records:
            sql = build_insert_sql(table, record["row"])
            if sql is None:
                skipped[table] += 1
                continue
            lines.append(sql)
        lines.append("")
    lines.append("COMMIT;")
    output_path.write_text("\n".join(lines))
    return dict(skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a schema-compatible executable SQL load script.")
    parser.add_argument(
        "--input",
        default="llm-request/processed-sql/deduped_records.json",
        help="Path to deduped records JSON.",
    )
    parser.add_argument(
        "--output-sql",
        default="llm-request/processed-sql/final_executable_load.sql",
        help="Path to write the final executable SQL script.",
    )
    parser.add_argument(
        "--output-summary",
        default="llm-request/processed-sql/final_executable_summary.json",
        help="Path to write the final executable SQL summary.",
    )
    args = parser.parse_args()

    raw_records = [apply_aliases(record) for record in load_records(Path(args.input))]
    id_maps = build_id_maps(raw_records)

    valid_records: list[dict[str, Any]] = []
    skipped_reasons: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in raw_records:
        transformed, reason = transform_record(record, id_maps)
        if transformed is None:
            skipped_reasons[record["table"]][reason or "unknown"] += 1
            continue
        valid_records.append(transformed)

    chosen_records, dedupe_dropped = choose_representatives(valid_records)
    chosen_records, pruned_unused_cities = prune_unused_dim_cities(chosen_records)
    sql_skipped = write_sql(chosen_records, Path(args.output_sql))

    summary = {
        "raw_records_considered": len(raw_records),
        "valid_records_after_schema_filter": len(valid_records),
        "records_in_final_sql": len(chosen_records) - sum(sql_skipped.values()),
        "records_deduped_away_by_unique_key": dedupe_dropped,
        "records_pruned_after_reference_check": {"dim_cities": pruned_unused_cities},
        "records_skipped_during_sql_generation": sql_skipped,
        "skipped_reasons": {table: dict(reasons) for table, reasons in skipped_reasons.items()},
    }
    Path(args.output_summary).write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"Wrote SQL to {args.output_sql}")
    print(f"Wrote summary to {args.output_summary}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
