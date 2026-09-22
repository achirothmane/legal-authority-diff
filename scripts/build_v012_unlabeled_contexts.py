import json
from pathlib import Path

from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.authority_relation_v09 import normalize_source_text


CANDIDATES = Path("benchmarks/blinded-relation-v0.12/candidates.jsonl")
OUTPUT = Path("/tmp/v0.12-unlabeled-contexts.jsonl")


def load_jsonl(path):
    return [
        json.loads(raw)
        for raw in path.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]


rows = load_jsonl(CANDIDATES)
assert len(rows) == 20
assert all("expected_relation" not in row for row in rows)

cache = {}
output = []

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
        state = "TARGET_TERM_NOT_FOUND"
    else:
        radius = int(row["radius"])
        start = max(0, index - radius)
        end = min(len(normalized), index + len(term) + radius)
        context = normalized[start:end]
        state = "FOUND"

    result = {
        **row,
        "context_state": state,
        "context": context,
        "source": source_meta,
    }
    output.append(result)

    print("=" * 100)
    print(
        f"{row['challenge_id']} "
        f"{row['source_case']} -> {row['target_case']} "
        f"state={state}"
    )
    print(context)

OUTPUT.write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output),
    encoding="utf-8",
)

print("V0.12 UNLABELED CONTEXT FREEZE")
print(f"rows={len(output)} found={sum(1 for row in output if row['context_state'] == 'FOUND')}")
