import json
from collections import Counter
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import classify_precedent_relation
from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.structured_relation_v010_frozen import (
    build_relation_context,
    extract_structured_relation,
)


DATASET = Path("benchmarks/structured-relation-v0.10/heldout.jsonl")
OUTPUT = Path("/tmp/v0.10-structured-relation-heldout.json")

EXPECTED_DISTRIBUTION = Counter(
    {
        "AFFIRMATIVE_USE": 9,
        "DISTINGUISHES_OR_LIMITS": 4,
        "NEGATIVE_TREATMENT": 1,
        "MENTION_ONLY": 1,
        "UNKNOWN": 1,
    }
)


def load_rows():
    rows = [
        json.loads(raw)
        for raw in DATASET.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]
    assert len(rows) == 16, len(rows)
    assert len({row["challenge_id"] for row in rows}) == len(rows)
    assert Counter(row["expected_relation"] for row in rows) == EXPECTED_DISTRIBUTION
    return rows


def safe_v09(context, row):
    if not context:
        return {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": ["empty_context"],
        }
    return classify_precedent_relation(
        context,
        target_citation=row["target_citation"],
        target_term=row["target_term"],
    )


rows = load_rows()
cache = {}
results = []

for row in rows:
    source_citation = row["source_citation"]
    if source_citation not in cache:
        cache[source_citation] = fetch_us_reports_text(source_citation)

    source_text, source_metadata = cache[source_citation]

    context_info = build_relation_context(
        source_text,
        anchor=row["anchor"],
        target_citation=row["target_citation"],
        target_term=row["target_term"],
        radius=int(row["radius"]),
        max_target_gap=2400,
    )
    context = context_info["text"]

    v09 = safe_v09(context, row)
    v10 = extract_structured_relation(
        context,
        target_citation=row["target_citation"],
        target_term=row["target_term"],
        target_resolution=context_info["target_resolution"],
    )

    gold_suspect = (
        row["expected_relation"] != "UNKNOWN"
        and not context_info["target_found_near_anchor"]
    )

    results.append(
        {
            **row,
            "gold_suspect": gold_suspect,
            "gold_suspect_reason": (
                context_info["gold_suspect_reason"]
                if gold_suspect
                else None
            ),
            "context_resolution": context_info,
            "source": source_metadata,
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
                "target_resolution": v10["target_resolution"],
                "attribution_owner": v10["attribution_owner"],
                "attributed_proposition": v10["attributed_proposition"],
                "current_court_actions": v10["current_court_actions"],
                "current_court_cues": v10["current_court_cues"],
                "abstention_reason": v10["abstention_reason"],
            },
            "context": context,
        }
    )


def accuracy(items, version):
    if not items:
        return 0.0
    return sum(1 for row in items if row[version]["correct"]) / len(items)


resolved = [row for row in results if not row["gold_suspect"]]
suspect = [row for row in results if row["gold_suspect"]]

raw_v09 = accuracy(results, "v0.9")
raw_v10 = accuracy(results, "v0.10")
resolved_v09 = accuracy(resolved, "v0.9")
resolved_v10 = accuracy(resolved, "v0.10")

high_confidence_wrong = [
    row["challenge_id"]
    for row in resolved
    if (
        not row["v0.10"]["correct"]
        and row["v0.10"]["confidence"] == "high"
    )
]

s15 = next(row for row in results if row["challenge_id"] == "S15")
s15_safe = s15["v0.10"]["predicted_relation"] not in {
    "NEGATIVE_TREATMENT",
    "DISTINGUISHES_OR_LIMITS",
    "MIXED_OR_CONFLICTING",
}

criteria = {
    "resolved_accuracy_at_least_0_75": resolved_v10 >= 0.75,
    "not_worse_than_v0_9": resolved_v10 >= resolved_v09,
    "attribution_trap_safe": s15_safe,
    "at_most_one_high_confidence_wrong": len(high_confidence_wrong) <= 1,
}
advance = all(criteria.values())

by_expected = {}
for label in sorted(EXPECTED_DISTRIBUTION):
    subset = [row for row in resolved if row["expected_relation"] == label]
    by_expected[label] = {
        "resolved_total": len(subset),
        "v0.9_correct": sum(1 for row in subset if row["v0.9"]["correct"]),
        "v0.10_correct": sum(1 for row in subset if row["v0.10"]["correct"]),
    }

report = {
    "benchmark": {
        "name": "structured-relation-v0.10-heldout",
        "pairs": len(results),
        "resolved_pairs": len(resolved),
        "gold_suspect_pairs": len(suspect),
        "source": "govinfo",
        "target_search_gap_chars": 2400,
        "frozen_before_first_run": True,
        "structured_relation_blob_sha": "b2e53647079bede921183514f0afff921d31ed44",
        "status": "first held-out run",
    },
    "raw": {
        "v0.9_accuracy": raw_v09,
        "v0.10_accuracy": raw_v10,
    },
    "resolved": {
        "v0.9_accuracy": resolved_v09,
        "v0.10_accuracy": resolved_v10,
    },
    "gold_suspect_ids": [row["challenge_id"] for row in suspect],
    "high_confidence_wrong_ids": high_confidence_wrong,
    "by_expected": by_expected,
    "success_criteria": criteria,
    "advance_to_next_falsification_stage": advance,
    "rows": results,
}

OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.10 STRUCTURED RELATION HELD-OUT")
print(
    f"raw: v0.9={raw_v09:.3f} v0.10={raw_v10:.3f} "
    f"pairs={len(results)}"
)
print(
    f"resolved: v0.9={resolved_v09:.3f} v0.10={resolved_v10:.3f} "
    f"pairs={len(resolved)}"
)
print(f"gold_suspect_ids={[row['challenge_id'] for row in suspect]}")
print(f"high_confidence_wrong_ids={high_confidence_wrong}")
for label, stats in by_expected.items():
    print(
        f"{label}: "
        f"v0.9={stats['v0.9_correct']}/{stats['resolved_total']} "
        f"v0.10={stats['v0.10_correct']}/{stats['resolved_total']}"
    )
print(f"success_criteria={criteria}")
print(f"advance_to_next_falsification_stage={advance}")

for row in results:
    if row["gold_suspect"]:
        print(
            "GOLD_SUSPECT "
            f"{row['challenge_id']} "
            f"expected={row['expected_relation']} "
            f"reason={row['gold_suspect_reason']}"
        )
    elif not row["v0.10"]["correct"]:
        print(
            "MISS "
            f"{row['challenge_id']} "
            f"difficulty={row['difficulty']} "
            f"expected={row['expected_relation']} "
            f"predicted={row['v0.10']['predicted_relation']} "
            f"confidence={row['v0.10']['confidence']} "
            f"owner={row['v0.10']['attribution_owner']} "
            f"actions={row['v0.10']['current_court_actions']}"
        )
