"""V0.11 development replay using schema-constrained model extraction.

IMPORTANT: benchmarks/structured-relation-v0.10/heldout.jsonl is NOT held out
for V0.11. Its labels and failures were already observed during V0.10. This
script uses it only as a development set for the new architecture.

No V0.11 promotion claim may be based on this replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.openai_relation_v011 import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    SYSTEM_PROMPT,
    extract_relation_openai,
)
from legal_authority_diff.schema_relation_v011 import (
    RELATION_EXTRACTION_JSON_SCHEMA,
)
from legal_authority_diff.structured_relation_v010_frozen import (
    build_relation_context,
)


DATASET = Path("benchmarks/structured-relation-v0.10/heldout.jsonl")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_rows() -> list[dict]:
    return [
        json.loads(raw)
        for raw in DATASET.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=["low", "medium", "high", "xhigh", "max"],
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/v0.11-schema-relation-dev.json"),
    )
    args = parser.parse_args()

    rows = load_rows()
    if args.limit > 0:
        rows = rows[: args.limit]

    cache = {}
    results = []

    for row in rows:
        citation = row["source_citation"]
        if citation not in cache:
            cache[citation] = fetch_us_reports_text(citation)

        source_text, source_metadata = cache[citation]
        context_info = build_relation_context(
            source_text,
            anchor=row["anchor"],
            target_citation=row["target_citation"],
            target_term=row["target_term"],
            radius=int(row["radius"]),
            max_target_gap=2400,
        )
        context = context_info["text"]

        model_result = extract_relation_openai(
            context=context,
            target_name=row["target_case"],
            target_citation=row["target_citation"],
            claim=row.get("claim"),
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )

        predicted = model_result["policy_input"]["treatment"]
        correct = predicted == row["expected_relation"]

        results.append(
            {
                **row,
                "context": context,
                "context_resolution": context_info,
                "source": source_metadata,
                "predicted_relation": predicted,
                "correct": correct,
                **model_result,
            }
        )

        print(
            f"{row['challenge_id']} "
            f"expected={row['expected_relation']} "
            f"predicted={predicted} "
            f"valid={model_result['validation']['valid']} "
            f"abstain={model_result['extraction'].get('abstain')}"
        )

    total = len(results)
    correct = sum(1 for row in results if row["correct"])
    valid = sum(1 for row in results if row["validation"]["valid"])
    abstained = sum(
        1
        for row in results
        if row["extraction"].get("abstain") is True
    )
    invalid = total - valid

    by_expected = {}
    for label in sorted({row["expected_relation"] for row in results}):
        subset = [row for row in results if row["expected_relation"] == label]
        by_expected[label] = {
            "total": len(subset),
            "correct": sum(1 for row in subset if row["correct"]),
        }

    confusion = Counter(
        (row["expected_relation"], row["predicted_relation"])
        for row in results
    )

    report = {
        "benchmark": {
            "name": "v0.11-schema-constrained-development-replay",
            "status": "development replay; NOT held-out for V0.11",
            "source_dataset": str(DATASET),
            "pairs": total,
            "source": "govinfo",
            "requested_model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "system_prompt_sha256": _sha(SYSTEM_PROMPT),
            "json_schema_sha256": _sha(
                json.dumps(
                    RELATION_EXTRACTION_JSON_SCHEMA,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
        },
        "metrics": {
            "correct": correct,
            "accuracy": (correct / total) if total else 0.0,
            "valid_schema_and_grounding": valid,
            "invalid_schema_or_grounding": invalid,
            "abstained": abstained,
        },
        "by_expected": by_expected,
        "confusion": [
            {
                "expected": expected,
                "predicted": predicted,
                "count": count,
            }
            for (expected, predicted), count in sorted(confusion.items())
        ],
        "rows": results,
    }

    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("V0.11 SCHEMA-CONSTRAINED DEVELOPMENT REPLAY")
    print(
        f"correct={correct}/{total} "
        f"accuracy={(correct / total) if total else 0.0:.3f}"
    )
    print(
        f"validated={valid}/{total} invalid={invalid} "
        f"abstained={abstained}"
    )
    for label, stats in by_expected.items():
        print(f"{label}: {stats['correct']}/{stats['total']}")

    print("NOTE: this dataset was observed during V0.10; this is not V0.11 held-out evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
