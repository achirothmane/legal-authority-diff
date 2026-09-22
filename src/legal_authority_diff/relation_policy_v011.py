"""Policy bridge for V0.11 structured relation extraction.

The extractor never returns a CI verdict directly. This bridge converts only a
validated, grounded, non-abstaining treatment into the existing experimental
relation-aware policy. Invalid or abstaining extraction always becomes UNKNOWN.
"""

from __future__ import annotations

from typing import Any

from .relation_policy_v09 import classify_relation_aware_transition
from .schema_relation_v011 import safe_treatment


def classify_v011_transition(
    *,
    baseline_score: float,
    candidate_score: float,
    baseline_role: str,
    candidate_role: str,
    extraction: dict[str, Any],
    context: str,
    target_name: str,
    target_citation: str,
    lexical_threshold: float = 0.34,
) -> dict[str, Any]:
    envelope = safe_treatment(
        extraction,
        context=context,
        expected_target_name=target_name,
        expected_target_citation=target_citation,
    )

    if not envelope["usable"]:
        return {
            "classification": "UNKNOWN",
            "reason": f"v0.11:{envelope['reason']}",
            "candidate_relation": "UNKNOWN",
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
            "extraction_validation": envelope["validation"],
        }

    result = classify_relation_aware_transition(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_role=baseline_role,
        candidate_role=candidate_role,
        candidate_relation=envelope["treatment"],
        lexical_threshold=lexical_threshold,
    )
    result = dict(result)
    result["reason"] = f"v0.11:{result['reason']}"
    result["extraction_validation"] = envelope["validation"]
    return result
