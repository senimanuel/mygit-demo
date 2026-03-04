"""
List files successfully transferred in a DataSync task report.

Auto-discovers the correct S3 bucket by looking for a Summary-Reports folder.
Shows FSx source/destination context per execution, plus total file count.

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
    r = subprocess.run(["aws", "s3", "ls", uri], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def find_report_bucket():
    buckets = json.loads(cli(["s3api", "list-buckets"]))["Buckets"]
    for b in buckets:
        bucket = b["Name"]
        top_lines = s3_ls(f"s3://{bucket}/")
        top_prefixes = [""] + [
            line.split()[-1]
            for line in top_lines
            if line.split() and line.split()[-1].endswith("/")
        ]
        for prefix in top_prefixes:
            if any("Summary-Reports/" in l for l in s3_ls(f"s3://{bucket}/{prefix}")):
                return bucket, prefix
    sys.exit("No bucket with a DataSync Summary-Reports structure found.")


def load_location_uris():
    """
    Fetch all DataSync locations and return a dict of {location-id: uri}.
    Used to resolve human-readable FSx paths from the summary LocationId.
    """
    r = subprocess.run(["aws", "datasync", "list-locations"], capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    return {
        loc["LocationArn"].split("/")[-1]: loc["LocationUri"]
        for loc in json.loads(r.stdout).get("Locations", [])
    }


def find_summary_keys(bucket, base_prefix):
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/{base_prefix}Summary-Reports/"])
    return [
        line.split(maxsplit=3)[3]
        for line in output.splitlines()
        if len(line.split(maxsplit=3)) == 4 and "summary-v1.json" in line
    ]


def process_execution(bucket, summary_key, location_uris):
    summary = json.loads(cli(["s3", "cp", f"s3://{bucket}/{summary_key}", "-"]))
    exec_id   = summary.get("TaskExecutionId", "")
    result    = summary.get("Result", {})
    count     = result.get("FilesTransferred", 0)
    skipped   = result.get("FilesSkipped", 0)
    status    = summary.get("OverallStatus", "")

    src_id    = summary.get("SourceLocation", {}).get("LocationId", "")
    dst_id    = summary.get("DestinationLocation", {}).get("LocationId", "")
    src_type  = summary.get("SourceLocation", {}).get("LocationType", "")
    dst_type  = summary.get("DestinationLocation", {}).get("LocationType", "")
    src_uri   = location_uris.get(src_id, src_id)
    dst_uri   = location_uris.get(dst_id, dst_id)

    print(f"\n  {exec_id}  [{status}]")
    print(f"    Source      : {src_uri}  ({src_type})")
    print(f"    Destination : {dst_uri}  ({dst_type})")
    print(f"    Transferred : {count} file(s)  |  Skipped: {skipped}")

    if count == 0:
        return []

    # Fetch per-file list from Detailed-Reports
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


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    bucket, base_prefix = find_report_bucket()
    print(f"\nBucket : {bucket}")

    location_uris = load_location_uris()

    summary_keys = find_summary_keys(bucket, base_prefix)
    if not summary_keys:
        sys.exit("No summary reports found.")
    print(f"Executions found: {len(summary_keys)}")

    all_files = []
    for key in summary_keys:
        all_files.extend(process_execution(bucket, key, location_uris))

    print(f"\nTotal successfully transferred: {len(all_files)} file(s)\n")

    if output_json:
        print(json.dumps(all_files, indent=2))
    else:
        for f in all_files:
            print(f)


if __name__ == "__main__":
    main()
