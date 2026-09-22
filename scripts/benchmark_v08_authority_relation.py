import json
from collections import Counter
from pathlib import Path

from legal_authority_diff.authority_relation import (
    classify_precedent_relation,
    extract_anchor_context,
)
from legal_authority_diff.govinfo import fetch_us_reports_text


DATASET = Path("benchmarks/authority-relation-v0.8/challenges.jsonl")
OUTPUT = Path("/tmp/v0.8-authority-relation-report.json")


def load_rows():
    rows = []
    for raw in DATASET.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


rows = load_rows()
expected_counts = Counter(row["expected_relation"] for row in rows)
assert len(rows) == 12, len(rows)
assert expected_counts == Counter(
    {
        "AFFIRMATIVE_USE": 5,
        "DISTINGUISHES_OR_LIMITS": 2,
        "NEGATIVE_TREATMENT": 1,
        "MENTION_ONLY": 3,
        "UNKNOWN": 1,
    }
), expected_counts

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
        predicted = {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": ["anchor_not_found"],
        }
    else:
        predicted = classify_precedent_relation(
            context,
            target_citation=row["target_citation"],
            target_term=row.get("target_term"),
        )

    results.append(
        {
            **row,
            "predicted_relation": predicted["relation"],
            "confidence": predicted["confidence"],
            "cues": predicted["cues"],
            "correct": predicted["relation"] == row["expected_relation"],
            "context": context,
            "source": metadata,
        }
    )

correct = sum(1 for row in results if row["correct"])
confusion = {}
for row in results:
    key = f"{row['expected_relation']}->{row['predicted_relation']}"
    confusion[key] = confusion.get(key, 0) + 1

by_expected = {}
for label in sorted(expected_counts):
    subset = [row for row in results if row["expected_relation"] == label]
    by_expected[label] = {
        "total": len(subset),
        "correct": sum(1 for row in subset if row["correct"]),
    }

report = {
    "benchmark": {
        "name": "authority-relation-v0.8",
        "pairs": len(results),
        "unique_source_citations": len(cache),
        "source": "govinfo",
        "frozen_before_first_run": True,
        "scope": "local precedent relationship cues; not current-law validation",
    },
    "expected_distribution": dict(expected_counts),
    "accuracy": correct / len(results),
    "correct": correct,
    "incorrect": len(results) - correct,
    "by_expected": by_expected,
    "confusion": confusion,
    "rows": results,
}

OUTPUT.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.8 AUTHORITY RELATION CHALLENGE")
print(f"correct={correct}/{len(results)} accuracy={report['accuracy']:.3f}")
for label, stats in by_expected.items():
    print(f"{label}: {stats['correct']}/{stats['total']}")

for row in results:
    if not row["correct"]:
        print(
            "MISS "
            f"{row['challenge_id']} "
            f"expected={row['expected_relation']} "
            f"predicted={row['predicted_relation']} "
            f"confidence={row['confidence']} "
            f"cues={row['cues']}"
        )
