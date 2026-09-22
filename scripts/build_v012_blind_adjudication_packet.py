import json
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import normalize_source_text
from legal_authority_diff.govinfo import fetch_us_reports_text


CANDIDATES = Path("benchmarks/blinded-relation-v0.12/candidates.jsonl")
OUTPUT = Path("/tmp/v0.12-blind-adjudication-packet.jsonl")


rows = [
    json.loads(raw)
    for raw in CANDIDATES.read_text(encoding="utf-8").splitlines()
    if raw.strip()
]

cache = {}
packet = []

for row in rows:
    citation = row["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)

    source_text, source_meta = cache[citation]
    normalized = normalize_source_text(source_text)
    term = row["target_term"]
    index = normalized.lower().find(term.lower())

    if index < 0:
        context = ""
        context_state = "TARGET_TERM_NOT_FOUND"
    else:
        radius = int(row["radius"])
        start = max(0, index - radius)
        end = min(len(normalized), index + len(term) + radius)
        context = normalized[start:end]
        context_state = "FOUND"

    packet.append(
        {
            "challenge_id": row["challenge_id"],
            "source_case": row["source_case"],
            "source_citation": row["source_citation"],
            "target_case": row["target_case"],
            "target_citation": row["target_citation"],
            "context_state": context_state,
            "context": context,
            "review": {
                "gold_treatment": None,
                "confidence": None,
                "evidence_span": None,
                "notes": None,
                "reviewer": None,
            },
            "source": source_meta,
        }
    )

OUTPUT.write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in packet),
    encoding="utf-8",
)

print("V0.12 BLIND ADJUDICATION PACKET")
print(f"rows={len(packet)}")
print(
    "IMPORTANT: packet contains no V0.12 prediction fields. "
    "Review it without opening predictions.jsonl."
)
