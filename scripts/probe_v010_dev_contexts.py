import json
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import extract_anchor_context
from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.structured_relation import extract_structured_relation


MISSES = {
    "H04", "H06", "H07", "H08", "H10", "H11", "H12",
    "H13", "H14", "H16", "H17", "H18", "H19",
}

rows = [
    json.loads(raw)
    for raw in Path("benchmarks/authority-relation-v0.9/heldout.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if raw.strip()
]

cache = {}
for row in rows:
    if row["challenge_id"] not in MISSES:
        continue
    citation = row["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)[0]
    source = cache[citation]
    context = extract_anchor_context(
        source,
        row["anchor"],
        radius=int(row["radius"]),
    )
    result = extract_structured_relation(
        context,
        target_citation=row["target_citation"],
        target_term=row["target_term"],
    )
    print("=" * 120)
    print(
        row["challenge_id"],
        "EXPECTED=", row["expected_relation"],
        "TARGET=", row["target_case"],
        row["target_citation"],
    )
    print("STRUCTURED=", json.dumps(result, ensure_ascii=False))
    print("CONTEXT=", context)
