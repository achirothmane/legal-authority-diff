import json
from collections import Counter, defaultdict
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import (
    classify_precedent_relation,
    extract_anchor_context,
)
from legal_authority_diff.govinfo import fetch_us_reports_text


DATASET = Path("benchmarks/authority-relation-v0.9/heldout.jsonl")
OUTPUT = Path("/tmp/v0.9-authority-relation-report.json")

EXPECTED_DISTRIBUTION = Counter(
    {
        "AFFIRMATIVE_USE": 7,
        "DISTINGUISHES_OR_LIMITS": 5,
        "NEGATIVE_TREATMENT": 4,
        "MIXED_OR_CONFLICTING": 2,
        "MENTION_ONLY": 1,
        "UNKNOWN": 1,
    }
)


def load_rows():
    rows = []
    for line_number, raw in enumerate(
        DATASET.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        row = json.loads(raw)
        required = {
            "challenge_id",
            "source_case",
            "source_citation",
            "target_case",
            "target_citation",
            "target_term",
            "anchor",
            "radius",
            "expected_relation",
            "difficulty",
        }
        missing = sorted(required - set(row))
        if missing:
            raise AssertionError(
                f"{DATASET}:{line_number}: missing fields {missing}"
            )
        rows.append(row)
    return rows


rows = load_rows()
expected_counts = Counter(row["expected_relation"] for row in rows)

assert len(rows) == 20, len(rows)
assert expected_counts == EXPECTED_DISTRIBUTION, expected_counts
assert len({row["challenge_id"] for row in rows}) == len(rows)
assert all(str(row["challenge_id"]).startswith("H") for row in rows)

cache = {}
results = []

for row in rows:
    citation = row["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)

    source_text, source_metadata = cache[citation]
    context = extract_anchor_context(
        source_text,
        row["anchor"],
        radius=int(row["radius"]),
    )

    if not context:
        predicted = {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": ["anchor_not_found"],
            "categories": [],
        }
        anchor_state = "NOT_FOUND"
    else:
        predicted = classify_precedent_relation(
            context,
            target_citation=row["target_citation"],
            target_term=row.get("target_term"),
        )
        anchor_state = "FOUND"

    result = {
        **row,
        "anchor_state": anchor_state,
        "predicted_relation": predicted["relation"],
        "confidence": predicted["confidence"],
        "cues": predicted.get("cues", []),
        "categories": predicted.get("categories", []),
        "correct": predicted["relation"] == row["expected_relation"],
        "context": context,
        "source": source_metadata,
    }
    results.append(result)

correct = sum(1 for row in results if row["correct"])
anchor_failures = [
    row["challenge_id"]
    for row in results
    if row["anchor_state"] != "FOUND"
]

by_expected = {}
for label in sorted(expected_counts):
    subset = [row for row in results if row["expected_relation"] == label]
    by_expected[label] = {
        "total": len(subset),
        "correct": sum(1 for row in subset if row["correct"]),
        "accuracy": (
            sum(1 for row in subset if row["correct"]) / len(subset)
            if subset
            else 0.0
        ),
    }

by_difficulty = defaultdict(lambda: {"total": 0, "correct": 0})
for row in results:
    bucket = by_difficulty[row["difficulty"]]
    bucket["total"] += 1
    bucket["correct"] += int(row["correct"])

for stats in by_difficulty.values():
    stats["accuracy"] = (
        stats["correct"] / stats["total"]
        if stats["total"]
        else 0.0
    )

confusion = {}
for row in results:
    key = f"{row['expected_relation']}->{row['predicted_relation']}"
    confusion[key] = confusion.get(key, 0) + 1

report = {
    "benchmark": {
        "name": "authority-relation-v0.9-heldout",
        "pairs": len(results),
        "unique_source_citations": len(cache),
        "source": "govinfo",
        "frozen_before_first_run": True,
        "scope": "local precedent relationship cues; not current-law validation",
    },
    "expected_distribution": dict(expected_counts),
    "correct": correct,
    "incorrect": len(results) - correct,
    "accuracy": correct / len(results),
    "anchor_failures": anchor_failures,
    "by_expected": by_expected,
    "by_difficulty": dict(sorted(by_difficulty.items())),
    "confusion": confusion,
    "rows": results,
}

OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.9 AUTHORITY RELATION HELD-OUT")
print(
    f"correct={correct}/{len(results)} "
    f"accuracy={report['accuracy']:.3f} "
    f"anchor_failures={len(anchor_failures)}"
)

for label, stats in by_expected.items():
    print(
        f"{label}: {stats['correct']}/{stats['total']} "
        f"accuracy={stats['accuracy']:.3f}"
    )

if anchor_failures:
    print(f"ANCHOR_FAILURES {anchor_failures}")

for row in results:
    if not row["correct"]:
        print(
            "MISS "
            f"{row['challenge_id']} "
            f"difficulty={row['difficulty']} "
            f"expected={row['expected_relation']} "
            f"predicted={row['predicted_relation']} "
            f"confidence={row['confidence']} "
            f"anchor={row['anchor_state']} "
            f"cues={row['cues']}"
        )
