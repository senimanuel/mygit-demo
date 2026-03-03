"""
List files successfully transferred in a DataSync task report.

Auto-discovers any S3 bucket whose name contains 'datasync'.
Reads Summary-Reports to find executions with transfers, then fetches
the per-file list from the corresponding Detailed-Reports.

Uses the currently active AWS CLI profile — no config needed.

Usage:
  python read_datasync_report.py
  python read_datasync_report.py --output json
"""

import json
import subprocess
import sys


def cli(args: list[str]) -> str:
    result = subprocess.run(["aws"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"AWS CLI error: {result.stderr.strip()}")
    return result.stdout


def find_datasync_buckets() -> list[str]:
    buckets = json.loads(cli(["s3api", "list-buckets"]))["Buckets"]
    return [b["Name"] for b in buckets if "datasync" in b["Name"].lower()]


def find_summary_keys(bucket: str) -> list[str]:
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/"])
    return [
        line.split(maxsplit=3)[3]
        for line in output.splitlines()
        if len(line.split(maxsplit=3)) == 4
        and "Summary-Reports" in line
        and "summary-v1.json" in line
    ]


def get_transferred_file_paths(bucket: str, summary_key: str) -> list[str]:
    summary = json.loads(cli(["s3", "cp", f"s3://{bucket}/{summary_key}", "-"]))
    exec_id = summary.get("TaskExecutionId", "")
    files_transferred = summary.get("Result", {}).get("FilesTransferred", 0)

    print(f"  {exec_id}  →  FilesTransferred: {files_transferred}", file=sys.stderr)

    if files_transferred == 0:
        return []

    # Derive the Detailed-Reports prefix from the Summary-Reports key
    # e.g. reports/Summary-Reports/<task>/<exec>/exec.summary-v1.json
    #   -> reports/Detailed-Reports/<task>/<exec>/
    detailed_prefix = summary_key.replace("Summary-Reports", "Detailed-Reports").rsplit("/", 1)[0]

    # List files-transferred reports under that prefix
    ls_output = cli(["s3", "ls", f"s3://{bucket}/{detailed_prefix}/"])
    transferred_keys = [
        f"{detailed_prefix}/{parts[3].strip()}"
        for line in ls_output.splitlines()
        if len((parts := line.split(maxsplit=3))) == 4
        and "files-transferred" in parts[3]
        and parts[3].strip().endswith(".json")
    ]

    if not transferred_keys:
        print(f"    [WARN] No files-transferred report found in Detailed-Reports", file=sys.stderr)
        return []

    all_files = []
    for key in transferred_keys:
        report = json.loads(cli(["s3", "cp", f"s3://{bucket}/{key}", "-"]))
        all_files += [
            e["RelativePath"].lstrip("/")
            for e in report.get("Transferred", [])
            if e.get("TransferStatus", "").upper() == "SUCCESS" and e.get("RelativePath")
        ]
    return all_files


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    buckets = find_datasync_buckets()
    if not buckets:
        sys.exit("No S3 bucket with 'datasync' in the name found.")

    all_files = []
    for bucket in buckets:
        print(f"\nBucket: {bucket}", file=sys.stderr)
        summary_keys = find_summary_keys(bucket)
        if not summary_keys:
            print("  No summary reports found.", file=sys.stderr)
            continue
        print(f"  Found {len(summary_keys)} execution(s):", file=sys.stderr)
        for key in summary_keys:
            all_files.extend(get_transferred_file_paths(bucket, key))

    print(f"\nTotal successfully transferred: {len(all_files)} file(s)\n", file=sys.stderr)

    if output_json:
        print(json.dumps(all_files, indent=2))
    else:
        for f in all_files:
            print(f)


if __name__ == "__main__":
    main()
