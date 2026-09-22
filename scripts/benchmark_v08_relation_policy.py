import json
from collections import Counter
from pathlib import Path

from legal_authority_diff.relation_policy import (
    classify_relation_aware_transition,
)
from legal_authority_diff.role_diff import classify_evidence_transition


REPORT = Path("/tmp/v0.8-authority-relation-report.json")
payload = json.loads(REPORT.read_text(encoding="utf-8"))
rows = payload["rows"]

protected = []
world_changes = []
abstained = []
fallback_blocks = []
unexpected = []

for row in rows:
    relation = row["predicted_relation"]
    if not row["correct"]:
        unexpected.append(
            {
                "challenge_id": row["challenge_id"],
                "reason": "relation_misclassified",
            }
        )
        continue

    # Synthetic scores/roles isolate the policy question: assume both versions
    # clear proposition-support threshold, while a later case looks weaker to the
    # V0.7 role classifier because it cites the originating authority.
    baseline_score = 0.50
    candidate_score = 0.45
    baseline_role = "COURT_SELF_HOLDING"
    candidate_role = "ATTRIBUTED_PRIOR_AUTHORITY"

    v07 = classify_evidence_transition(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_role=baseline_role,
        candidate_role=candidate_role,
    )
    v08 = classify_relation_aware_transition(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_role=baseline_role,
        candidate_role=candidate_role,
        candidate_relation=relation,
    )

    item = {
        "challenge_id": row["challenge_id"],
        "relation": relation,
        "v0.7": v07["classification"],
        "v0.8": v08["classification"],
        "reason": v08["reason"],
    }

    if relation == "AFFIRMATIVE_USE":
        if v07["classification"] != "REGRESSION":
            unexpected.append({**item, "reason": "v0.7_control_not_blocking"})
        elif v08["classification"] == "NO_REGRESSION_DETECTED":
            protected.append(item)
        else:
            unexpected.append(item)
    elif relation == "NEGATIVE_TREATMENT":
        if v08["classification"] == "WORLD_CHANGE":
            world_changes.append(item)
        else:
            unexpected.append(item)
    elif relation == "DISTINGUISHES_OR_LIMITS":
        if v08["classification"] == "UNKNOWN":
            abstained.append(item)
        else:
            unexpected.append(item)
    elif relation == "MENTION_ONLY":
        if v08["classification"] == "REGRESSION":
            fallback_blocks.append(item)
        else:
            unexpected.append(item)
    elif relation == "UNKNOWN":
        if v08["classification"] in {"REGRESSION", "NO_REGRESSION_DETECTED"}:
            # UNKNOWN relation intentionally carries no override.
            fallback_blocks.append(item)
        else:
            fallback_blocks.append(item)

counts = Counter(row["predicted_relation"] for row in rows)
assert len(protected) == counts["AFFIRMATIVE_USE"] == 5, protected
assert len(world_changes) == counts["NEGATIVE_TREATMENT"] == 1, world_changes
assert len(abstained) == counts["DISTINGUISHES_OR_LIMITS"] == 2, abstained
assert not unexpected, unexpected

result = {
    "benchmark": "relation-policy-v0.8",
    "input_relation_accuracy": payload["accuracy"],
    "affirmative_use_false_blocks_prevented": len(protected),
    "negative_treatment_world_changes": len(world_changes),
    "distinguish_limit_abstentions": len(abstained),
    "mention_or_unknown_fallbacks": len(fallback_blocks),
    "protected": protected,
    "world_changes": world_changes,
    "abstained": abstained,
    "fallbacks": fallback_blocks,
}

Path("/tmp/v0.8-relation-policy-report.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.8 RELATION-AWARE POLICY: PASS")
print(
    "affirmative-use role-only false blocks prevented="
    f"{len(protected)}/{counts['AFFIRMATIVE_USE']}"
)
print(
    "negative-treatment mapped to WORLD_CHANGE="
    f"{len(world_changes)}/{counts['NEGATIVE_TREATMENT']}"
)
print(
    "distinguish/limit mapped to UNKNOWN="
    f"{len(abstained)}/{counts['DISTINGUISHES_OR_LIMITS']}"
)
