import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

_lock = threading.Lock()


def step(msg):
    with _lock:
        print(f"  {msg}", flush=True)


def cli(args):
    result = subprocess.run(["aws"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"AWS CLI error: {result.stderr.strip()}")
    return result.stdout


def s3_ls(uri):
    r = subprocess.run(["aws", "s3", "ls", uri], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def find_report_bucket():
    step("Scanning S3 buckets for DataSync reports...")
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


def load_location_uris(region):
    step("Loading DataSync locations...")
    r = subprocess.run(["aws", "datasync", "list-locations", "--region", region],
                       capture_output=True, text=True)
    if r.returncode != 0:
        step(f"Warning: list-locations failed: {r.stderr.strip()}")
        return {}
    locations = json.loads(r.stdout).get("Locations", [])
    step(f"Found {len(locations)} DataSync location(s) in {region}")
    return {
        loc["LocationArn"].split("/")[-1]: loc["LocationUri"]
        for loc in locations
    }


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
    if location_id in cache:
        return cache[location_id]

    cmd = _DESCRIBE_CMD.get(location_type)
    if cmd:
        arn = f"arn:aws:datasync:{region}:{account_id}:location/{location_id}"
        r = subprocess.run(["aws", "datasync", cmd, "--location-arn", arn, "--region", region],
                           capture_output=True, text=True)
        if r.returncode == 0:
            uri = json.loads(r.stdout).get("LocationUri", location_id)
            cache[location_id] = uri
            return uri
        else:
            step(f"Warning: {cmd} failed for {location_id}: {r.stderr.strip()}")
    else:
        step(f"Warning: Unknown location type '{location_type}' — cannot resolve {location_id}")

    return location_id


def vol_name(uri):
    if "://" in uri:
        path = uri.split("://", 1)[1]
        path = path.split("/", 1)[1] if "/" in path else ""
        first_segment = path.strip("/").split("/")[0]
        return first_segment if first_segment else uri
    return uri


def find_summary_keys(bucket, base_prefix):
    step("Scanning execution summary reports...")
    output = cli(["s3", "ls", "--recursive", f"s3://{bucket}/{base_prefix}Summary-Reports/"])
    return [
        line.split(maxsplit=3)[3]
        for line in output.splitlines()
        if len(line.split(maxsplit=3)) == 4 and "summary-v1.json" in line
    ]


def fetch_files_from_detailed(bucket, summary_key, exec_id):
    step(f"Reading transferred file list for {exec_id}...")
    detailed_prefix = summary_key.replace("Summary-Reports", "Detailed-Reports").rsplit("/", 1)[0]
    ls_output = cli(["s3", "ls", f"s3://{bucket}/{detailed_prefix}/"])

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
    step(f"Reading summary: {summary_key.split('/')[-1]}")
    summary    = json.loads(cli(["s3", "cp", f"s3://{bucket}/{summary_key}", "-"]))
    exec_id    = summary.get("TaskExecutionId", "")
    result     = summary.get("Result", {})
    count      = result.get("FilesTransferred", 0)
    skipped    = result.get("FilesSkipped", 0)
    status     = summary.get("OverallStatus", "")
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
        f"    Volume/Path : {vol_name(src_uri)}",
        f"    Destination : {dst_uri}  ({dst_type})",
        f"    Volume/Path : {vol_name(dst_uri)}",
        f"    Transferred : {count} file(s)  |  Skipped: {skipped}",
    ]

    files = fetch_files_from_detailed(bucket, summary_key, exec_id) if count > 0 else []
    return lines, files


def main():
    output_json = "--output" in sys.argv and sys.argv[sys.argv.index("--output") + 1] == "json"

    print("\n[1/4] Finding report bucket...")
    bucket, base_prefix = find_report_bucket()
    print(f"      Bucket : {bucket}")

    print("\n[2/4] Loading DataSync location names...")
    region = subprocess.run(["aws", "configure", "get", "region"],
                            capture_output=True, text=True).stdout.strip() or "us-west-2"
    location_uris = load_location_uris(region)

    print("\n[3/4] Finding execution reports...")
    summary_keys = find_summary_keys(bucket, base_prefix)
    if not summary_keys:
        sys.exit("No summary reports found.")
    print(f"      Found {len(summary_keys)} execution(s)")

    print(f"\n[4/4] Processing executions (up to 8 in parallel)...")
    results = [None] * len(summary_keys)
    with ThreadPoolExecutor(max_workers=min(len(summary_keys), 8)) as ex:
        futures = {ex.submit(process_execution, bucket, key, location_uris, region): i
                   for i, key in enumerate(summary_keys)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    print("\n--- Results ---")
    all_files = []
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
