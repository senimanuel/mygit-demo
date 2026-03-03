"""
List files successfully transferred in a DataSync task report.

Auto-discovers any S3 bucket whose name contains 'datasync', finds all
Detailed-Reports inside it, and prints successfully transferred file paths.

Uses the currently active AWS CLI profile — no config needed.

Usage:
  python read_datasync_report.py
  python read_datasync_report.py --output json
"""

import json
import subprocess
import sys


def cli(args: list[str]) -> str:
    result = subprocess.run(
        ["aws"] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"AWS CLI error: {result.stderr.strip()}")
    return result.stdout


def find_datasync_buckets() -> list[str]:
    buckets = json.loads(cli(["s3api", "list-buckets"]))["Buckets"]
    return [b["Name"] for b in buckets if "datasync" in b["Name"].lower()]


def find_report_keys(bucket: str) -> list[str]:
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/"])
    keys = []
    for line in output.splitlines():
        # line format: "2024-01-01 00:00:00    1234 some/key.json"
        parts = line.split(maxsplit=3)
        if len(parts) == 4:
            key = parts[3]
            fname = key.split("/")[-1]
            # Actual DataSync filename pattern: exec-<id>.files-transferred-v1-<seq>.json
            if "Detailed-Reports" in key and "files-transferred" in fname and fname.endswith(".json"):
                keys.append(key)
    return keys


def get_transferred_files(bucket: str, key: str) -> list[str]:
    report = json.loads(cli(["s3", "cp", f"s3://{bucket}/{key}", "-"]))
    return [
        e["RelativePath"].lstrip("/")
        for e in report.get("Transferred", [])
        if e.get("TransferStatus", "").upper() == "SUCCESS" and e.get("RelativePath")
    ]


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    buckets = find_datasync_buckets()
    if not buckets:
        sys.exit("No S3 bucket with 'datasync' in the name found.")

    all_files = []
    for bucket in buckets:
        print(f"Scanning s3://{bucket} ...", file=sys.stderr)
        for key in find_report_keys(bucket):
            files = get_transferred_files(bucket, key)
            print(f"  {key}: {len(files)} transferred", file=sys.stderr)
            all_files.extend(files)

    print(f"\nTotal: {len(all_files)} file(s)\n", file=sys.stderr)

    if output_json:
        print(json.dumps(all_files, indent=2))
    else:
        for f in all_files:
            print(f)


if __name__ == "__main__":
    main()
