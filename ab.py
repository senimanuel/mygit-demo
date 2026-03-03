"""
List files successfully transferred in a DataSync task report.

Auto-discovers the correct S3 bucket by looking for a Summary-Reports folder
structure — no bucket name or naming convention needed.

Uses the currently active AWS CLI profile — no config needed.

Usage:
  python read_datasync_report.py
  python read_datasync_report.py --output json
"""

import json
import subprocess
import sys


def cli(args):
    result = subprocess.run(["aws"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"AWS CLI error: {result.stderr.strip()}")
    return result.stdout


def s3_ls(uri):
    """Run aws s3 ls and return output lines. Returns [] on any error."""
    r = subprocess.run(["aws", "s3", "ls", uri], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def find_report_bucket():
    """
    Scan all buckets for one containing a Summary-Reports folder.
    Uses aws s3 ls (same as the rest of the script). Checks root and one
    level deep (e.g. reports/Summary-Reports/).
    Returns (bucket, base_prefix).
    """
    buckets = json.loads(cli(["s3api", "list-buckets"]))["Buckets"]
    for b in buckets:
        bucket = b["Name"]
        top_lines = s3_ls(f"s3://{bucket}/")
        # Collect root + any top-level folders as candidate prefixes
        top_prefixes = [""] + [
            line.split()[-1]
            for line in top_lines
            if line.split() and line.split()[-1].endswith("/")
        ]
        for prefix in top_prefixes:
            sub_lines = s3_ls(f"s3://{bucket}/{prefix}")
            if any("Summary-Reports/" in line for line in sub_lines):
                return bucket, prefix

    sys.exit("No bucket with a DataSync Summary-Reports structure found.")


def find_summary_keys(bucket, base_prefix):
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/{base_prefix}Summary-Reports/"])
    return [
        line.split(maxsplit=3)[3]
        for line in output.splitlines()
        if len(line.split(maxsplit=3)) == 4 and "summary-v1.json" in line
    ]


def get_transferred_files(bucket, summary_key):
    summary = json.loads(cli(["s3", "cp", f"s3://{bucket}/{summary_key}", "-"]))
    exec_id = summary.get("TaskExecutionId", "")
    count = summary.get("Result", {}).get("FilesTransferred", 0)
    print(f"  {exec_id}  →  FilesTransferred: {count}", file=sys.stderr)
    if count == 0:
        return []

    # Swap Summary-Reports for Detailed-Reports in the key path
    detailed_prefix = summary_key.replace("Summary-Reports", "Detailed-Reports").rsplit("/", 1)[0]
    ls_output = cli(["s3", "ls", f"s3://{bucket}/{detailed_prefix}/"])

    all_files = []
    for line in ls_output.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) == 4 and "files-transferred" in parts[3] and parts[3].endswith(".json"):
            key = f"{detailed_prefix}/{parts[3].strip()}"
            report = json.loads(cli(["s3", "cp", f"s3://{bucket}/{key}", "-"]))
            all_files += [
                e["RelativePath"].lstrip("/")
                for e in report.get("Transferred", [])
                if e.get("TransferStatus", "").upper() == "SUCCESS" and e.get("RelativePath")
            ]
    return all_files


def resolve_bucket(name):
    """
    Given a bucket name, find the base prefix that contains Summary-Reports/.
    Returns (bucket, base_prefix) or prints a warning and returns (None, None).
    """
    top_lines = s3_ls(f"s3://{name}/")
    if not top_lines and not s3_ls(f"s3://{name}/"):
        print(f"  [!] Cannot access s3://{name}/ — check the name and permissions.")
        return None, None

    top_prefixes = [""] + [
        line.split()[-1]
        for line in top_lines
        if line.split() and line.split()[-1].endswith("/")
    ]
    for prefix in top_prefixes:
        sub_lines = s3_ls(f"s3://{name}/{prefix}")
        if any("Summary-Reports/" in line for line in sub_lines):
            return name, prefix

    print(f"  [!] No Summary-Reports/ folder found in s3://{name}/")
    return None, None


def prompt_buckets():
    """
    Interactive prompt: auto-discover a bucket, then let the user add more
    or override with a manual name.
    Returns a list of (bucket, base_prefix) tuples.
    """
    print("\nAuto-discovering DataSync report bucket...", flush=True)
    discovered_bucket, discovered_prefix = find_report_bucket()
    print(f"  Found: {discovered_bucket}  (prefix: '{discovered_prefix or 'root'}')")

    use = input("\nUse this bucket? [Y/n]: ").strip().lower()
    buckets = []
    if use != "n":
        buckets.append((discovered_bucket, discovered_prefix))

    while True:
        add = input("Add another bucket? [y/N]: ").strip().lower()
        if add != "y":
            break
        name = input("  Bucket name: ").strip()
        if not name:
            continue
        bucket, prefix = resolve_bucket(name)
        if bucket:
            print(f"  OK — prefix: '{prefix or 'root'}'")
            buckets.append((bucket, prefix))

    if not buckets:
        sys.exit("No buckets selected. Exiting.")
    return buckets


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    selected = prompt_buckets()

    all_files = []
    for bucket, base_prefix in selected:
        print(f"\nBucket : {bucket}", flush=True)
        summary_keys = find_summary_keys(bucket, base_prefix)
        if not summary_keys:
            print("  No summary reports found.")
            continue
        print(f"  Found {len(summary_keys)} execution(s):")
        for key in summary_keys:
            all_files.extend(get_transferred_files(bucket, key))

    print(f"\nTotal successfully transferred: {len(all_files)} file(s)\n")

    if output_json:
        print(json.dumps(all_files, indent=2))
    else:
        for f in all_files:
            print(f)


if __name__ == "__main__":
    main()
