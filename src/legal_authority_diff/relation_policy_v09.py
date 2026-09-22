"""V0.9 relation-aware differential policy.

This policy is experimental and intentionally separate from the mandatory core
gate. It uses target-scoped precedent relationship as a guardrail around
the V0.7 authority-role signal.
"""

from __future__ import annotations

from typing import Any

from .role_diff import classify_evidence_transition


def classify_relation_aware_transition(
    *,
    baseline_score: float,
    candidate_score: float,
    baseline_role: str,
    candidate_role: str,
    candidate_relation: str,
    lexical_threshold: float = 0.34,
) -> dict[str, Any]:
    """Combine lexical support, authority role, and precedent relationship.

    Rules are deliberately conservative:

    - explicit negative treatment of the baseline authority is WORLD_CHANGE,
      not a model regression;
    - explicit affirmative use/reaffirmation can suppress a role-only downgrade,
      but never rescues a candidate that fails lexical support;
    - distinguish/limit and mixed/conflicting relationships are UNKNOWN because
      proposition-level consequences depend on facts and claim scope;
    - mention-only/unknown relationships fall back to V0.7 behavior.
    """
    baseline_supported = float(baseline_score) >= float(lexical_threshold)
    candidate_supported = float(candidate_score) >= float(lexical_threshold)

    if candidate_relation == "NEGATIVE_TREATMENT":
        return {
            "classification": "WORLD_CHANGE",
            "reason": "explicit_negative_treatment",
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
            "candidate_relation": candidate_relation,
        }

    if candidate_relation in {
        "DISTINGUISHES_OR_LIMITS",
        "MIXED_OR_CONFLICTING",
    }:
        return {
            "classification": "UNKNOWN",
            "reason": (
                "mixed_or_conflicting_relation"
                if candidate_relation == "MIXED_OR_CONFLICTING"
                else "distinguished_or_limited_authority"
            ),
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
            "candidate_relation": candidate_relation,
        }

    if candidate_relation == "AFFIRMATIVE_USE":
        if baseline_supported and not candidate_supported:
            return {
                "classification": "REGRESSION",
                "reason": "lexical_support",
                "baseline_score": baseline_score,
                "candidate_score": candidate_score,
                "baseline_role": baseline_role,
                "candidate_role": candidate_role,
                "candidate_relation": candidate_relation,
            }

        if baseline_supported and candidate_supported:
            return {
                "classification": "NO_REGRESSION_DETECTED",
                "reason": "affirmative_precedent_use",
                "baseline_score": baseline_score,
                "candidate_score": candidate_score,
                "baseline_role": baseline_role,
                "candidate_role": candidate_role,
                "candidate_relation": candidate_relation,
            }

    fallback = classify_evidence_transition(
        baseline_score=baseline_score,
        candidate_score=candidate_score,
        baseline_role=baseline_role,
        candidate_role=candidate_role,
        lexical_threshold=lexical_threshold,
    )
    fallback = dict(fallback)
    fallback["candidate_relation"] = candidate_relation
    fallback["reason"] = f"v0.7_fallback:{fallback['reason']}"
    return fallback
