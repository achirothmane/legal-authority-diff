import json
from pathlib import Path

from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.schema_relation_v011 import safe_treatment
from legal_authority_diff.structured_relation_v010_frozen import (
    build_relation_context,
)


SPEC = Path("benchmarks/structured-relation-v0.10/heldout.jsonl")
EXTRACTIONS = Path(
    "benchmarks/schema-relation-v0.11/interactive-development.jsonl"
)


def load_jsonl(path):
    return [
        json.loads(raw)
        for raw in path.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]


spec_rows = {row["challenge_id"]: row for row in load_jsonl(SPEC)}
extractions = load_jsonl(EXTRACTIONS)

assert len(extractions) == 16
assert len({row["challenge_id"] for row in extractions}) == 16
assert set(row["challenge_id"] for row in extractions) == set(spec_rows)

cache = {}
results = []

for item in extractions:
    case_id = item["challenge_id"]
    spec = spec_rows[case_id]

    citation = spec["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)

    source_text, source_metadata = cache[citation]
    context_info = build_relation_context(
        source_text,
        anchor=spec["anchor"],
        target_citation=spec["target_citation"],
        target_term=spec["target_term"],
        radius=int(spec["radius"]),
        max_target_gap=2400,
    )
    context = context_info["text"]

    envelope = safe_treatment(
        item["extraction"],
        context=context,
        expected_target_name=spec["target_case"],
        expected_target_citation=spec["target_citation"],
    )

    expected = spec["expected_relation"]
    intended_fit = envelope["treatment"] == expected

    results.append(
        {
            "challenge_id": case_id,
            "expected_relation": expected,
            "validated_treatment": envelope["treatment"],
            "usable": envelope["usable"],
            "reason": envelope["reason"],
            "valid": envelope["validation"]["valid"],
            "errors": envelope["validation"]["errors"],
            "grounded_evidence_count": envelope["validation"][
                "grounded_evidence_count"
            ],
            "label_fit": intended_fit,
            "context_resolution": context_info,
            "source": source_metadata,
        }
    )

valid_count = sum(1 for row in results if row["valid"])
fit_count = sum(1 for row in results if row["label_fit"])
usable_count = sum(1 for row in results if row["usable"])
abstain_count = sum(
    1
    for row in extractions
    if row["extraction"]["abstain"] is True
)

assert valid_count == 16, results
assert fit_count == 16, results
assert usable_count == 15, results
assert abstain_count == 1

report = {
    "status": (
        "label-visible interactive development replay; "
        "NOT model accuracy and NOT held-out evidence"
    ),
    "cases": len(results),
    "schema_valid": valid_count,
    "intended_label_fit": fit_count,
    "usable_for_experimental_policy": usable_count,
    "validated_abstentions": abstain_count,
    "results": results,
}

Path("/tmp/v0.11-interactive-development-report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.11 INTERACTIVE DEVELOPMENT REPLAY: PASS")
print("NOTE: label-visible development exercise; not a model benchmark.")
print(
    f"schema_valid={valid_count}/16 "
    f"intended_label_fit={fit_count}/16 "
    f"usable={usable_count}/16 "
    f"validated_abstentions={abstain_count}"
)

for row in results:
    print(
        f"{row['challenge_id']} "
        f"expected={row['expected_relation']} "
        f"validated={row['validated_treatment']} "
        f"valid={row['valid']} usable={row['usable']} "
        f"evidence={row['grounded_evidence_count']}"
    )
