
import json
import os
from dotenv import load_dotenv
from google import genai


load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"
OUTPUT_PATH = "llm-request/data/extracted_wiki_data_responses.json"


def to_json_safe(value):
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json_safe(v) for v in value]
    if hasattr(value, "model_dump"):
        return to_json_safe(value.model_dump())
    if hasattr(value, "to_dict"):
        return to_json_safe(value.to_dict())
    return str(value)


def save_results(results):
    temp_path = f"{OUTPUT_PATH}.tmp"
    with open(temp_path, "w") as f:
        json.dump(results, f, indent=2)
    os.replace(temp_path, OUTPUT_PATH)


def strip_fences(text):
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def parse_model_json(text):
    cleaned = strip_fences(text)
    if not cleaned:
        return None
    try:
        parsed = json.loads(cleaned)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def merge_membership_rows(rows):
    # Expected row shape:
    # [university_wikipedia_href, conference_name, start_year, end_year]
    grouped = {}
    preserved_unknown_rows = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        href, conf_name, start_year, end_year = row[:4]
        if href is None or conf_name is None:
            continue
        if start_year is None:
            preserved_unknown_rows.append([href, conf_name, start_year, end_year])
            continue
        key = (href, conf_name)
        grouped.setdefault(key, []).append([href, conf_name, start_year, end_year])

    merged_rows = []
    for (_, _), items in grouped.items():
        items.sort(key=lambda r: int(r[2]))
        current = items[0]

        for nxt in items[1:]:
            curr_end = current[3]
            next_start = int(nxt[2])
            next_end = nxt[3]

            if curr_end is None:
                # Already open-ended; absorb subsequent fragments.
                continue

            curr_end_int = int(curr_end)
            # Merge when periods overlap or are contiguous by year.
            if next_start <= curr_end_int + 1:
                if next_end is None:
                    current[3] = None
                else:
                    current[3] = max(curr_end_int, int(next_end))
            else:
                merged_rows.append(current)
                current = nxt

        merged_rows.append(current)

    preserved_unknown_rows.sort(
        key=lambda r: (r[1], r[0], 9999 if r[3] is None else int(r[3]))
    )
    merged_rows.extend(preserved_unknown_rows)
    merged_rows.sort(
        key=lambda r: (
            r[1],
            r[0],
            -1 if r[2] is None else int(r[2]),
            9999 if r[3] is None else int(r[3]),
        )
    )
    return merged_rows


def normalize_extracted_payload(payload):
    memberships = payload.get("university_conference_memberships")
    if not isinstance(memberships, dict):
        return payload

    columns = memberships.get("columns") or []
    rows = memberships.get("rows") or []
    expected = ["university_wikipedia_href", "conference_name", "start_year", "end_year"]
    if columns != expected or not isinstance(rows, list):
        return payload

    normalized = payload.copy()
    memberships_copy = memberships.copy()
    memberships_copy["rows"] = merge_membership_rows(rows)
    normalized["university_conference_memberships"] = memberships_copy
    return normalized


def validate_extracted_payload(payload):
    issues = []
    if not isinstance(payload, dict):
        return ["Payload is not a JSON object"]

    expected_tables = {
        "universities": ["university_name", "university_wikipedia_href", "city", "state"],
        "conferences": ["conference_name", "conference_wikipedia_href", "conference_start_year", "conference_end_year"],
        "university_conference_memberships": ["university_wikipedia_href", "conference_name", "start_year", "end_year"],
    }

    for table_name, expected_columns in expected_tables.items():
        table = payload.get(table_name)
        if not isinstance(table, dict):
            issues.append(f"Missing or invalid table: {table_name}")
            continue

        columns = table.get("columns")
        rows = table.get("rows")
        if columns != expected_columns:
            issues.append(
                f"Unexpected columns for {table_name}: expected {expected_columns}, got {columns}"
            )
        if not isinstance(rows, list):
            issues.append(f"Rows for {table_name} are not a list")

    universities = payload.get("universities", {})
    memberships = payload.get("university_conference_memberships", {})
    uni_rows = universities.get("rows") if isinstance(universities, dict) else None
    mem_rows = memberships.get("rows") if isinstance(memberships, dict) else None

    if isinstance(uni_rows, list) and isinstance(mem_rows, list):
        uni_hrefs = {
            row[1]
            for row in uni_rows
            if isinstance(row, list) and len(row) >= 2 and isinstance(row[1], str)
        }
        mem_hrefs = {
            row[0]
            for row in mem_rows
            if isinstance(row, list) and len(row) >= 1 and isinstance(row[0], str)
        }

        missing_memberships = sorted(uni_hrefs - mem_hrefs)
        if missing_memberships:
            sample = ", ".join(missing_memberships[:5])
            issues.append(
                "universities missing membership rows: "
                f"{len(missing_memberships)} (sample: {sample})"
            )

    return issues


with open("data-assembly/json/final_data.json", "r") as f:
    conferences_data = json.load(f)

with open("llm-request/prompts/extract_wiki_data_prompt.md", "r") as f:
    extract_wiki_data_prompt = f.read()




# extract relevant fields and reformat for easier use in LLM prompting
formatted_conferences = {}
for conf_name, conf_data in conferences_data.items():

    member_schools = conf_data.get("member_schools") or []
    conference_history = conf_data.get("conference_history") or []
    timeline_map = conf_data.get("timeline_map") or {}

    member_school_text = (
        member_schools[0].get("content")
        if member_schools and isinstance(member_schools[0], dict)
        else None
    )

    conference_history_text = (
        conference_history[0].get("content")
        if conference_history and isinstance(conference_history[0], dict)
        else None
    )

    timeline_map_text = (
        timeline_map.get("map_text")
        if timeline_map and isinstance(timeline_map, dict)
        else None
    )


    formatted_conferences[conf_name] = {
        "name": conf_data.get("name"),
        "member_schools": member_school_text,
        "conference_history": conference_history_text,
        "timeline_map": timeline_map_text,
    }




# loop over the formatted conferences, submitting to LLM and saving the response for each. Use the extract_wiki_data_prompt.md
# as part of the prompt alongside the information in formatted_conferences. Save results to a json file as you go, so you can
# pick up where you left off if needed. Also save any failed attempts with error messages for later review.
if os.path.exists(OUTPUT_PATH):
    with open(OUTPUT_PATH, "r") as f:
        responses = json.load(f)
else:
    responses = {}


# Backfill normalize already-saved successful responses.
normalized_existing = 0
for conf_name, payload in responses.items():
    if not isinstance(payload, dict) or payload.get("error") is not None:
        continue

    existing_text = payload.get("response_text")
    parsed_existing = parse_model_json(existing_text)
    if parsed_existing is None:
        continue

    normalized_existing_payload = normalize_extracted_payload(parsed_existing)
    normalized_existing_text = json.dumps(normalized_existing_payload, indent=2)
    if normalized_existing_text != existing_text:
        payload["response_text"] = normalized_existing_text
        normalized_existing += 1

if normalized_existing:
    save_results(responses)
    print(f"Normalized existing saved responses: {normalized_existing}")


for conf_name, conf_data in formatted_conferences.items():
    if (
        conf_name in responses
        and isinstance(responses[conf_name], dict)
        and responses[conf_name].get("error") is None
    ):
        print(f"Skipping {conf_name}; already processed")
        continue

    content = [
        extract_wiki_data_prompt,
        json.dumps(conf_data, indent=2)
    ]


    raw_response_text = None
    response_metadata = None
    try:
        response = client.models.generate_content(
            model=model,
            contents=content
        )

        raw_response_text = response.text
        response_metadata = to_json_safe(response.usage_metadata)
        parsed = parse_model_json(raw_response_text)
        if parsed is None:
            raise ValueError(
                "Model response is not valid JSON object (possible truncation or malformed fenced output)"
            )

        normalized_payload = normalize_extracted_payload(parsed)
        validation_issues = validate_extracted_payload(normalized_payload)
        if validation_issues:
            raise ValueError("Validation failed: " + " | ".join(validation_issues))

        response_text_to_save = json.dumps(normalized_payload, indent=2)

        responses[conf_name] = {
            "response_text": response_text_to_save,
            "raw_response_text": raw_response_text,
            "error": None,
            "metadata": response_metadata,
            "validation_issues": []
        }
        save_results(responses)
        print(f"Processed {conf_name}")
    except Exception as e:
        responses[conf_name] = {
            "response_text": raw_response_text,
            "raw_response_text": raw_response_text,
            "error": str(e),
            "metadata": response_metadata,
        }
        save_results(responses)
        print(f"Failed to process {conf_name}: {e}")




