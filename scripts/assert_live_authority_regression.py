import json
import sys
from pathlib import Path


def read_one(path):
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1:
        raise SystemExit(f"{path}: expected exactly one JSONL row, got {len(rows)}")
    return rows[0]


baseline = read_one(sys.argv[1])
candidate = read_one(sys.argv[2])
report = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

base_auth = baseline["authority"]
cand_auth = candidate["authority"]
base_v = base_auth["verification"]
cand_v = cand_auth["verification"]

assert base_auth.get("exists") is True, baseline
assert cand_auth.get("exists") is True, candidate

assert base_v.get("source_court_id") == "scotus", base_v
assert cand_v.get("source_court_id") == "ca9", cand_v
assert base_v.get("target_court_id") == "ca2", base_v
assert cand_v.get("target_court_id") == "ca2", cand_v

assert base_auth.get("status") == "controlling", base_auth
assert cand_auth.get("status") == "persuasive", cand_auth

summary = report["summary"]
assert summary["regressions"] == 1, summary
assert summary["decision"] == "BLOCK", summary

case = report["cases"][0]
assert case["classification"] == "REGRESSION", case
assert any(
    change["kind"] == "authority_strength"
    and change["before"] == "controlling"
    and change["after"] == "persuasive"
    for change in case["changes"]
), case

assert not any(
    change["kind"] == "citation_existence"
    for change in case["changes"]
), case

print("LIVE AUTHORITY REGRESSION: PASS")
print("both citations FOUND")
print("baseline source court: scotus -> controlling for target ca2")
print("candidate source court: ca9 -> persuasive for target ca2")
print("diff decision: BLOCK")
