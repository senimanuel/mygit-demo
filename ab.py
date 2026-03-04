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
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    """Pre-load all DataSync location URIs into a {location-id: uri} dict."""
    r = subprocess.run(["aws", "datasync", "list-locations"], capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    return {
        loc["LocationArn"].split("/")[-1]: loc["LocationUri"]
        for loc in json.loads(r.stdout).get("Locations", [])
    }


# Maps LocationType (from summary) to the correct describe CLI subcommand
_DESCRIBE_CMD = {
    "Amazon S3":                             "describe-location-s3",
    "Amazon NFS":                            "describe-location-nfs",
    "Amazon EFS":                            "describe-location-efs",
    "Amazon SMB":                            "describe-location-smb",
    "Amazon FSx for Windows File Server":    "describe-location-fsx-windows",
    "Amazon FSx for Lustre":                 "describe-location-fsx-lustre",
    "Amazon FSx for OpenZFS":                "describe-location-fsx-open-zfs",
    "Amazon FSx for NetApp ONTAP (NFS)":     "describe-location-fsx-ontap",
    "Amazon FSx for NetApp ONTAP (SMB)":     "describe-location-fsx-ontap",
}


def resolve_location_uri(location_id, location_type, account_id, region, cache):
    """
    Return the URI for a DataSync location.
    Tries the pre-loaded cache first; falls back to a direct describe call
    so we always get the human-readable path (e.g. /CBlueDev/) even when
    list-locations is paginated or the cache is empty.
    """
    if location_id in cache:
        return cache[location_id]

    cmd = _DESCRIBE_CMD.get(location_type)
    if cmd:
        arn = f"arn:aws:datasync:{region}:{account_id}:location/{location_id}"
        r = subprocess.run(["aws", "datasync", cmd, "--location-arn", arn],
                           capture_output=True, text=True)
        if r.returncode == 0:
            uri = json.loads(r.stdout).get("LocationUri", location_id)
            cache[location_id] = uri   # save for next time
            return uri

    return location_id   # last resort: return the raw ID


def find_summary_keys(bucket, base_prefix):
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/{base_prefix}Summary-Reports/"])
    return [
        line.split(maxsplit=3)[3]
        for line in output.splitlines()
        if len(line.split(maxsplit=3)) == 4 and "summary-v1.json" in line
    ]


def uri_path(uri):
    """Extract just the path portion from a location URI.
    e.g. 's3://my-bucket/cbluedev/data/' -> '/cbluedev/data/'
         'ontap://svm-xxx/vol/cbluetest'  -> '/vol/cbluetest'
    """
    if "://" in uri:
        after_scheme = uri.split("://", 1)[1]       # 'my-bucket/cbluedev/data/'
        after_host   = after_scheme.split("/", 1)   # ['my-bucket', 'cbluedev/data/']
        path = "/" + after_host[1] if len(after_host) > 1 else "/"
        return path.rstrip("/") or "/"
    return uri


def fetch_files_from_detailed(bucket, summary_key):
    """Fetch per-file transferred list from Detailed-Reports for one execution."""
    detailed_prefix = summary_key.replace("Summary-Reports", "Detailed-Reports").rsplit("/", 1)[0]
    ls_output = cli(["s3", "ls", f"s3://{bucket}/{detailed_prefix}/"])

    # Collect all report file keys first, then fetch them in parallel
    report_keys = [
        f"{detailed_prefix}/{parts[3].strip()}"
        for line in ls_output.splitlines()
        if len((parts := line.split(maxsplit=3))) == 4
        and "files-transferred" in parts[3]
        and parts[3].endswith(".json")
    ]

    def read_report(key):
        report = json.loads(cli(["s3", "cp", f"s3://{bucket}/{key}", "-"]))
        return [
            e["RelativePath"].lstrip("/")
            for e in report.get("Transferred", [])
            if e.get("TransferStatus", "").upper() == "SUCCESS" and e.get("RelativePath")
        ]

    all_files = []
    with ThreadPoolExecutor(max_workers=min(len(report_keys), 8) or 1) as ex:
        for files in ex.map(read_report, report_keys):
            all_files.extend(files)
    return all_files


def process_execution(bucket, summary_key, location_uris, region):
    """Returns (output_lines, files) so prints don't interleave across threads."""
    summary  = json.loads(cli(["s3", "cp", f"s3://{bucket}/{summary_key}", "-"]))
    exec_id  = summary.get("TaskExecutionId", "")
    result   = summary.get("Result", {})
    count    = result.get("FilesTransferred", 0)
    skipped  = result.get("FilesSkipped", 0)
    status   = summary.get("OverallStatus", "")
    account_id = summary.get("AccountId", "")

    src_id   = summary.get("SourceLocation", {}).get("LocationId", "")
    dst_id   = summary.get("DestinationLocation", {}).get("LocationId", "")
    src_type = summary.get("SourceLocation", {}).get("LocationType", "")
    dst_type = summary.get("DestinationLocation", {}).get("LocationType", "")
    src_uri  = resolve_location_uri(src_id, src_type, account_id, region, location_uris)
    dst_uri  = resolve_location_uri(dst_id, dst_type, account_id, region, location_uris)

    lines = [
        f"\n  {exec_id}  [{status}]",
        f"    Source      : {src_uri}  ({src_type})",
        f"    Source path : {uri_path(src_uri)}",
        f"    Destination : {dst_uri}  ({dst_type})",
        f"    Dest path   : {uri_path(dst_uri)}",
        f"    Transferred : {count} file(s)  |  Skipped: {skipped}",
    ]

    files = fetch_files_from_detailed(bucket, summary_key) if count > 0 else []
    return lines, files


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    bucket, base_prefix = find_report_bucket()
    print(f"\nBucket : {bucket}")

    region = subprocess.run(["aws", "configure", "get", "region"],
                            capture_output=True, text=True).stdout.strip() or "us-east-1"
    location_uris = load_location_uris()   # shared cache, also updated by resolve_location_uri

    summary_keys = find_summary_keys(bucket, base_prefix)
    if not summary_keys:
        sys.exit("No summary reports found.")
    print(f"Executions found: {len(summary_keys)}")

    # Process all executions in parallel, preserving print order
    all_files = []
    results = [None] * len(summary_keys)
    with ThreadPoolExecutor(max_workers=min(len(summary_keys), 8)) as ex:
        futures = {ex.submit(process_execution, bucket, key, location_uris, region): i
                   for i, key in enumerate(summary_keys)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    for lines, files in results:
        for line in lines:
            print(line)
        all_files.extend(files)

    print(f"\nTotal successfully transferred: {len(all_files)} file(s)\n")

    if output_json:
        print(json.dumps(all_files, indent=2))
    else:
        for f in all_files:
            print(f)


if __name__ == "__main__":
    main()
