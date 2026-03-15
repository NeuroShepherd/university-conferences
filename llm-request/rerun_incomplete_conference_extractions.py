import argparse
import json
import subprocess
import sys
from pathlib import Path

OUTPUT_PATH = Path("llm-request/extracted_data_responses.json")
REPORT_PATH = Path("llm-request/processed-json/extraction_completeness_report.json")
RERUN_RESULTS_PATH = Path("llm-request/processed-json/incomplete_rerun_results.json")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit conference extraction completeness and optionally re-run incomplete conferences."
    )
    parser.add_argument(
        "--input",
        default=str(OUTPUT_PATH),
        help="Path to extracted conference responses JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_PATH),
        help="Path to write completeness report JSON.",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="Re-run extraction for conferences missing fact_membership table.",
    )
    parser.add_argument(
        "--python-bin",
        default=None,
        help="Python executable to use for rerun command. Defaults to current interpreter.",
    )
    parser.add_argument(
        "--rerun-results",
        default=str(RERUN_RESULTS_PATH),
        help="Path to write per-conference rerun outcomes.",
    )
    return parser.parse_args()


def load_extractions(path: Path) -> dict:
    return json.loads(path.read_text())


def parse_payload(entry: dict):
    sql_text = entry.get("sql_text")
    if not isinstance(sql_text, str) or not sql_text.strip():
        return None
    try:
        payload = json.loads(sql_text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def build_report(data: dict) -> dict:
    missing_fact_membership = []
    parse_failures = []
    complete = []

    for conf_name, entry in data.items():
        payload = parse_payload(entry)
        if payload is None:
            parse_failures.append(conf_name)
            continue

        if not isinstance(payload.get("fact_membership"), dict):
            missing_fact_membership.append(conf_name)
            continue

        complete.append(conf_name)

    return {
        "total_conferences": len(data),
        "complete_fact_membership": len(complete),
        "missing_fact_membership": len(missing_fact_membership),
        "parse_failures_or_empty": len(parse_failures),
        "missing_fact_membership_conferences": sorted(missing_fact_membership),
        "parse_failure_or_empty_conferences": sorted(parse_failures),
    }


def rerun_incomplete(conferences: list[str], python_bin: str | None, rerun_results_path: Path):
    if not conferences:
        print("No incomplete conferences to rerun.")
        rerun_results_path.parent.mkdir(parents=True, exist_ok=True)
        rerun_results_path.write_text(json.dumps({"results": []}, indent=2))
        return []

    names_file = Path("llm-request/processed-json/incomplete_conferences.txt")
    names_file.parent.mkdir(parents=True, exist_ok=True)
    names_file.write_text("\n".join(conferences) + "\n")

    py = python_bin or sys.executable
    results = []

    for conference in conferences:
        cmd = [
            py,
            "llm-request/extract_uni_conference_data_from_wiki.py",
            "--conference",
            conference,
            "--force",
            "--require-fact-membership",
        ]
        print("Running:", " ".join(cmd))
        completed = subprocess.run(cmd, capture_output=True, text=True)

        stdout_tail = "\n".join(completed.stdout.strip().splitlines()[-20:]) if completed.stdout else ""
        stderr_tail = "\n".join(completed.stderr.strip().splitlines()[-20:]) if completed.stderr else ""

        result = {
            "conference": conference,
            "returncode": completed.returncode,
            "status": "success" if completed.returncode == 0 else "failed",
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
        }
        results.append(result)

    rerun_results_path.parent.mkdir(parents=True, exist_ok=True)
    rerun_results_path.write_text(json.dumps({"results": results}, indent=2))

    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - succeeded
    print(f"Rerun complete. succeeded={succeeded}, failed={failed}, total={len(results)}")
    print(f"Wrote rerun results to {rerun_results_path}")

    return results


def main():
    args = parse_args()

    input_path = Path(args.input)
    report_path = Path(args.report)
    rerun_results_path = Path(args.rerun_results)

    data = load_extractions(input_path)
    report = build_report(data)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    print(f"Wrote report to {report_path}")

    if args.rerun:
        rerun_incomplete(report["missing_fact_membership_conferences"], args.python_bin, rerun_results_path)

        refreshed_data = load_extractions(input_path)
        refreshed_report = build_report(refreshed_data)
        report_path.write_text(json.dumps(refreshed_report, indent=2))
        print("Post-rerun completeness:")
        print(json.dumps(refreshed_report, indent=2))
        print(f"Updated report at {report_path}")


if __name__ == "__main__":
    main()
