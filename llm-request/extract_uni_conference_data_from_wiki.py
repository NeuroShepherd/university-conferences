
# This script will be the first approach to extracting conference data from Wikipedia.


import argparse
import json
import os
from dotenv import load_dotenv
from google import genai



load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"Using key {api_key[:6]}...")

client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"

OUTPUT_PATH = "llm-request/extracted_data_responses.json"


def to_json_safe(value):
    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "dict"):
        return value.dict()

    return value


def clean_response_text(response_text):
    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```"):
        lines = cleaned_text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned_text = "\n".join(lines).strip()

    return cleaned_text


def is_completed_result(result):
    if not isinstance(result, dict):
        return False

    if result.get("error") is not None:
        return False

    sql_text = result.get("sql_text")
    if isinstance(sql_text, str) and sql_text.strip() != "":
        return True

    parsed_response = result.get("parsed_response")
    return isinstance(parsed_response, dict)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract structured conference data from Wikipedia payloads using Gemini."
    )
    parser.add_argument(
        "--output-path",
        default=OUTPUT_PATH,
        help="Path to extraction results JSON.",
    )
    parser.add_argument(
        "--conference",
        action="append",
        default=[],
        help="Conference name to process. Can be passed multiple times.",
    )
    parser.add_argument(
        "--conference-list-file",
        default=None,
        help="Optional text file with one conference name per line.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess conferences even if they have completed results.",
    )
    parser.add_argument(
        "--require-fact-membership",
        action="store_true",
        help="Mark extraction as failed if parsed payload is missing fact_membership table.",
    )
    return parser.parse_args()


def parse_payload_json(cleaned_response_text):
    try:
        payload = json.loads(cleaned_response_text)
    except Exception:
        return None, "response_not_json"

    if not isinstance(payload, dict):
        return None, "response_not_json_object"

    return payload, None


def payload_has_fact_membership(payload):
    if not isinstance(payload, dict):
        return False
    fact_membership = payload.get("fact_membership")
    return isinstance(fact_membership, dict)


def save_results(all_results, output_path):
    temp_output_path = f"{output_path}.tmp"

    with open(temp_output_path, "w") as f:
        json.dump(all_results, f, indent=2)

    os.replace(temp_output_path, output_path)


def load_conference_names_from_file(file_path):
    if not file_path:
        return []
    with open(file_path, "r") as f:
        lines = [line.strip() for line in f.readlines()]
    return [line for line in lines if line and not line.startswith("#")]


def filter_conferences(conferences_data, selected_names):
    if not selected_names:
        return conferences_data

    selected = {}
    missing = []
    for name in selected_names:
        if name in conferences_data:
            selected[name] = conferences_data[name]
        else:
            missing.append(name)

    if missing:
        print(f"Warning: {len(missing)} requested conferences were not found in source data")
        for name in missing:
            print(f"  - {name}")

    return selected


def main():
    args = parse_args()


    with open("data-assembly/json/final_data.json", "r") as f:
        conferences_data = json.load(f)


    for conf in conferences_data.values():
        # Remove fields from each dict in member_schools (list of dicts)
        if "member_schools" in conf:
            for school in conf["member_schools"]:
                school.pop("content_length", None)
                school.pop("h2", None)
        # Remove fields from each dict in conference_history (list of dicts)
        if "conference_history" in conf:
            for hist in conf["conference_history"]:
                hist.pop("content_length", None)
                hist.pop("h2", None)
        # Remove edit_url from timeline_map (dict)
        if "timeline_map" in conf and isinstance(conf["timeline_map"], dict):
            conf["timeline_map"].pop("edit_url", None)




    with open("llm-request/extract_data_wiki_prompt.md", "r") as f:
        prompt = f.read()

    with open("llm-request/database_design_response.md", "r") as f:
        database_design_notes = f.read()

    if os.path.exists(args.output_path):
        with open(args.output_path, "r") as f:
            all_results = json.load(f)
    else:
        all_results = {}

    selected_names = []
    selected_names.extend(args.conference)
    selected_names.extend(load_conference_names_from_file(args.conference_list_file))
    if selected_names:
        conferences_data = filter_conferences(conferences_data, selected_names)
        print(f"Processing {len(conferences_data)} selected conferences")
    else:
        print(f"Processing all conferences: {len(conferences_data)}")

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    for conf_name, conf_data in conferences_data.items():
        existing_result = all_results.get(conf_name)
        if not args.force and is_completed_result(existing_result):
            print(f"Skipping {conf_name}; already processed")
            skipped_count += 1
            continue

        content = [
            database_design_notes,
            prompt,
            json.dumps(conf_data, indent=2)
        ]

        response = None

        try:
            response = client.models.generate_content(
                model=model,
                contents=content
            )

            cleaned_response_text = clean_response_text(response.text)

            if not cleaned_response_text:
                raise ValueError("response.text was empty")

            parsed_payload, parse_error = parse_payload_json(cleaned_response_text)
            if parse_error:
                raise ValueError(parse_error)

            if args.require_fact_membership and not payload_has_fact_membership(parsed_payload):
                raise ValueError("missing_required_table:fact_membership")

            all_results[conf_name] = {
                "conf_name": conf_name,
                "sql_text": cleaned_response_text,
                "response_text": response.text,
                "usage_metadata": to_json_safe(response.usage_metadata),
                "error": None,
            }

            save_results(all_results, args.output_path)
            processed_count += 1
            print(f"Processed {conf_name}")

        except Exception as exc:
            all_results[conf_name] = {
                "conf_name": conf_name,
                "sql_text": None,
                "response_text": None if response is None else response.text,
                "usage_metadata": None if response is None else to_json_safe(response.usage_metadata),
                "error": str(exc),
            }

            save_results(all_results, args.output_path)
            failed_count += 1
            print(f"Failed {conf_name}: {exc}")

    print(
        f"Done. processed={processed_count}, skipped={skipped_count}, failed={failed_count}, total={len(conferences_data)}"
    )


if __name__ == "__main__":
    main()

