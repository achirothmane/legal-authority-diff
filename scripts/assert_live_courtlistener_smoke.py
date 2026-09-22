import json
import sys
from pathlib import Path


def read_one(path):
    lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) != 1:
        raise SystemExit(f"{path}: expected exactly one JSONL row, got {len(lines)}")
    return json.loads(lines[0])


baseline = read_one(sys.argv[1])
candidate = read_one(sys.argv[2])
report = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

base_auth = baseline.get("authority", {})
cand_auth = candidate.get("authority", {})

assert base_auth.get("exists") is True, baseline
assert cand_auth.get("exists") is False, candidate

base_v = base_auth.get("verification", {})
cand_v = cand_auth.get("verification", {})

assert base_v.get("provider") == "courtlistener", base_v
assert base_v.get("lookup_status") == "FOUND", base_v
assert cand_v.get("provider") == "courtlistener", cand_v
assert cand_v.get("lookup_status") == "NOT_FOUND", cand_v

summary = report.get("summary", {})
assert summary.get("regressions") == 1, summary
assert summary.get("decision") == "BLOCK", summary

cases = report.get("cases", [])
assert len(cases) == 1, cases
assert cases[0].get("classification") == "REGRESSION", cases[0]
assert any(
    change.get("kind") == "citation_existence"
    for change in cases[0].get("changes", [])
), cases[0]

print("LIVE COURTLISTENER SMOKE: PASS")
print("baseline citation resolved; candidate citation not found; diff decision BLOCK")
