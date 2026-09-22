import json
from pathlib import Path

from legal_authority_diff.authority_relation_v09 import normalize_source_text
from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.schema_relation_v011 import safe_treatment


CANDIDATES = Path("benchmarks/blinded-relation-v0.12/candidates.jsonl")
PREDICTIONS = Path("benchmarks/blinded-relation-v0.12/predictions.jsonl")
OUTPUT = Path("/tmp/v0.12-prediction-validation.json")


def load_jsonl(path):
    return [
        json.loads(raw)
        for raw in path.read_text(encoding="utf-8").splitlines()
        if raw.strip()
    ]


candidates = {row["challenge_id"]: row for row in load_jsonl(CANDIDATES)}
predictions = load_jsonl(PREDICTIONS)

assert len(candidates) == 20
assert len(predictions) == 20
assert set(row["challenge_id"] for row in predictions) == set(candidates)
assert all("expected_relation" not in row for row in candidates.values())
assert all("expected_relation" not in row for row in predictions)

cache = {}
results = []

for item in predictions:
    case_id = item["challenge_id"]
    spec = candidates[case_id]

    citation = spec["source_citation"]
    if citation not in cache:
        cache[citation] = fetch_us_reports_text(citation)

    source_text, source_meta = cache[citation]
    normalized = normalize_source_text(source_text)
    term = spec["target_term"]
    index = normalized.lower().find(term.lower())

    if index < 0:
        context = ""
        context_state = "TARGET_TERM_NOT_FOUND"
    else:
        radius = int(spec["radius"])
        start = max(0, index - radius)
        end = min(len(normalized), index + len(term) + radius)
        context = normalized[start:end]
        context_state = "FOUND"

    envelope = safe_treatment(
        item["extraction"],
        context=context,
        expected_target_name=spec["target_case"],
        expected_target_citation=spec["target_citation"],
    )

    results.append(
        {
            "challenge_id": case_id,
            "context_state": context_state,
            "predicted_treatment": item["extraction"]["treatment"],
            "validated_treatment": envelope["treatment"],
            "usable": envelope["usable"],
            "reason": envelope["reason"],
            "validation": envelope["validation"],
            "source": source_meta,
        }
    )

valid = sum(1 for row in results if row["validation"]["valid"])
usable = sum(1 for row in results if row["usable"])
abstentions = sum(
    1
    for item in predictions
    if item["extraction"]["abstain"] is True
)
unresolved = sum(
    1
    for row in results
    if row["context_state"] == "TARGET_TERM_NOT_FOUND"
)

print("V0.12 PREDICTION FREEZE VALIDATION")
print(
    f"schema_valid={valid}/20 usable={usable}/20 "
    f"abstentions={abstentions} unresolved_contexts={unresolved}"
)

for row in results:
    print(
        f"{row['challenge_id']} "
        f"context={row['context_state']} "
        f"prediction={row['predicted_treatment']} "
        f"validated={row['validated_treatment']} "
        f"valid={row['validation']['valid']} "
        f"usable={row['usable']} "
        f"errors={row['validation']['errors']}"
    )

OUTPUT.write_text(
    json.dumps(
        {
            "status": "prediction freeze validation; no gold labels exist",
            "schema_valid": valid,
            "usable": usable,
            "abstentions": abstentions,
            "unresolved_contexts": unresolved,
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)

if valid != 20:
    raise SystemExit("Prediction freeze contains schema/grounding failures.")
if abstentions != unresolved:
    raise SystemExit("Unresolved-context count must match explicit abstentions.")
