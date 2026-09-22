import json
import re
from pathlib import Path

from legal_authority_diff.govinfo import fetch_us_reports_text


def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


for dataset in [
    "benchmarks/real-claim-citation-v0.5/pairs.jsonl",
    "benchmarks/semantic-v0.6/heldout.jsonl",
]:
    rows = load(dataset)
    positives = {row["claim_id"]: row for row in rows if row["expected_support"] == "supported"}
    negatives = [row for row in rows if row["expected_support"] == "unsupported"]
    cache = {}
    print("=" * 100)
    print(dataset)
    for row in negatives:
        citation = row["citation"]
        if citation not in cache:
            cache[citation] = fetch_us_reports_text(citation)[0]
        text = normalize(cache[citation])
        positive = positives[row["claim_id"]]
        source_citation = normalize(positive["citation"])
        source_name = normalize(positive["case_name"])
        citation_hit = source_citation in text
        name_hit = source_name in text
        print(
            row["pair_id"],
            "negative=", row["case_name"],
            "origin=", positive["case_name"],
            "origin_citation=", positive["citation"],
            "citation_hit=", citation_hit,
            "name_hit=", name_hit,
        )
