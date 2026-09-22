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
base_support = base_v["support_verification"]
cand_support = cand_v["support_verification"]

assert base_auth.get("exists") is True, baseline
assert cand_auth.get("exists") is True, candidate
assert base_auth.get("status") == "controlling", base_auth
assert cand_auth.get("status") == "controlling", cand_auth

assert base_v.get("source_court_id") == "scotus", base_v
assert cand_v.get("source_court_id") == "scotus", cand_v

assert base_support.get("state") == "RESOLVED", base_support
assert cand_support.get("state") == "RESOLVED", cand_support
assert baseline.get("support") == "supported", baseline
assert candidate.get("support") == "unsupported", candidate

assert set(base_support.get("matched_phrases", [])) == {"same-sex couples", "marry"}, base_support
assert set(cand_support.get("missing_phrases", [])) == {"same-sex couples", "marry"}, cand_support

summary = report["summary"]
assert summary["regressions"] == 1, summary
assert summary["decision"] == "BLOCK", summary

case = report["cases"][0]
assert case["classification"] == "REGRESSION", case

support_changes = [
    change for change in case["changes"]
    if change["kind"] == "proposition_support"
]
assert len(support_changes) == 1, case
assert support_changes[0]["before"] == "supported", support_changes[0]
assert support_changes[0]["after"] == "unsupported", support_changes[0]

assert not any(
    change["kind"] == "citation_existence"
    for change in case["changes"]
), case
assert not any(
    change["kind"] == "authority_strength"
    for change in case["changes"]
), case

print("LIVE PROPOSITION SUPPORT REGRESSION: PASS")
print("both citations FOUND and controlling for target ca2")
print("baseline source text satisfies required support anchors")
print("candidate source text misses required support anchors")
print("support: supported -> unsupported")
print("diff decision: BLOCK")
