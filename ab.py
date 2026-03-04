"""
Read a DataSync task report JSON and list successfully transferred files.

Usage:
  python list_transferred_files.py exec.json
"""

import json
import sys

report = json.loads(open(sys.argv[1]).read())

files = [
    e["RelativePath"]
    for e in report.get("Verified", [])
    if e.get("VerifyStatus") == "SUCCESS"
]

print(f"\nSuccessfully transferred: {len(files)} file(s)\n")
for f in files:
    print(f)
