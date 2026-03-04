"""
Read a DataSync task report JSON and list successfully transferred files.

Usage:
  python list_transferred_files.py exec.json
"""

import json
import sys

if len(sys.argv) < 2:
    sys.exit("Usage: python list_transferred_files.py <path/to/report.json>")

report = json.loads(open(sys.argv[1]).read())

files = [
    e["RelativePath"]
    for e in report.get("Verified", [])
    if e.get("VerifyStatus") == "SUCCESS"
]

exec_id = report.get("TaskExecutionId", "unknown")
print(f"\nTask Execution : {exec_id}")
print(f"Successfully transferred: {len(files)} file(s)\n")
for f in files:
    print(f)
