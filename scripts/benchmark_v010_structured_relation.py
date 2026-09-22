import json
from collections import Counter
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import (
    classify_precedent_relation as classify_v09,
    extract_anchor_context,
)
from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.structured_relation import extract_structured_relation


DATASET = Path("benchmarks/authority-relation-v0.9/heldout.jsonl")
OUTPUT = Path("/tmp/v0.10-structured-relation-dev-replay.json")


def load_rows():
    return [
        json.loads(raw)
        for raw in DATASET.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]


rows = load_rows()
cache = {}
results = []

for row in rows:
    citation = row["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)

    source_text, metadata = cache[citation]
    context = extract_anchor_context(
        source_text,
        row["anchor"],
        radius=int(row["radius"]),
    )

    if not context:
        v09 = {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": ["anchor_not_found"],
        }
        v10 = {
            "relation": "UNKNOWN",
            "confidence": "low",
            "target_present": False,
            "attribution_owner": "UNKNOWN",
            "attributed_proposition": "",
            "current_court_actions": [],
            "current_court_cues": [],
            "abstention_reason": "anchor_not_found",
        }
    else:
        v09 = classify_v09(
            context,
            target_citation=row["target_citation"],
            target_term=row["target_term"],
        )
        v10 = extract_structured_relation(
            context,
            target_citation=row["target_citation"],
            target_term=row["target_term"],
        )

    results.append(
        {
            **row,
            "context": context,
            "source": metadata,
            "v0.9": {
                "predicted_relation": v09["relation"],
                "confidence": v09["confidence"],
                "correct": v09["relation"] == row["expected_relation"],
                "cues": v09.get("cues", []),
            },
            "v0.10": {
                "predicted_relation": v10["relation"],
                "confidence": v10["confidence"],
                "correct": v10["relation"] == row["expected_relation"],
                "target_present": v10["target_present"],
                "attribution_owner": v10["attribution_owner"],
                "attributed_proposition": v10["attributed_proposition"],
                "current_court_actions": v10["current_court_actions"],
                "current_court_cues": v10["current_court_cues"],
                "abstention_reason": v10["abstention_reason"],
            },
        }
    )

v09_correct = sum(1 for row in results if row["v0.9"]["correct"])
v10_correct = sum(1 for row in results if row["v0.10"]["correct"])
fixed = [
    row["challenge_id"]
    for row in results
    if not row["v0.9"]["correct"] and row["v0.10"]["correct"]
]
broken = [
    row["challenge_id"]
    for row in results
    if row["v0.9"]["correct"] and not row["v0.10"]["correct"]
]

by_expected = {}
for label in sorted({row["expected_relation"] for row in results}):
    subset = [row for row in results if row["expected_relation"] == label]
    by_expected[label] = {
        "total": len(subset),
        "v0.9_correct": sum(1 for row in subset if row["v0.9"]["correct"]),
        "v0.10_correct": sum(1 for row in subset if row["v0.10"]["correct"]),
    }

attribution_owner_counts = Counter(
    row["v0.10"]["attribution_owner"]
    for row in results
)

report = {
    "benchmark": {
        "name": "v0.10-structured-relation-dev-replay",
        "source_dataset": str(DATASET),
        "pairs": len(results),
        "status": "development replay; not held-out",
        "source": "govinfo",
    },
    "v0.9_correct": v09_correct,
    "v0.10_correct": v10_correct,
    "v0.9_accuracy": v09_correct / len(results),
    "v0.10_accuracy": v10_correct / len(results),
    "fixed_by_v0.10": fixed,
    "broken_by_v0.10": broken,
    "by_expected": by_expected,
    "attribution_owner_counts": dict(attribution_owner_counts),
    "rows": results,
}

OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.10 STRUCTURED RELATION DEV REPLAY")
print(
    f"v0.9={v09_correct}/{len(results)} "
    f"v0.10={v10_correct}/{len(results)}"
)
print(f"fixed_by_v0.10={fixed}")
print(f"broken_by_v0.10={broken}")
for label, stats in by_expected.items():
    print(
        f"{label}: "
        f"v0.9={stats['v0.9_correct']}/{stats['total']} "
        f"v0.10={stats['v0.10_correct']}/{stats['total']}"
    )

for row in results:
    if not row["v0.10"]["correct"]:
        print(
            "MISS "
            f"{row['challenge_id']} "
            f"expected={row['expected_relation']} "
            f"v0.10={row['v0.10']['predicted_relation']} "
            f"owner={row['v0.10']['attribution_owner']} "
            f"actions={row['v0.10']['current_court_actions']} "
            f"abstain={row['v0.10']['abstention_reason']}"
        )
