"""V0.7 differential combination of lexical support and authority role."""

from __future__ import annotations

from typing import Any

from .authority_role import compare_authority_roles


def classify_evidence_transition(
    *,
    baseline_score: float,
    candidate_score: float,
    baseline_role: str,
    candidate_role: str,
    lexical_threshold: float = 0.34,
) -> dict[str, Any]:
    """Classify a support-evidence transition conservatively.

    Lexical support remains the first signal. Authority role is only allowed to
    create a regression when both sides clear the frozen lexical threshold and a
    high-confidence primary-like baseline degrades to attributed/secondary text.
    """
    baseline_supported = float(baseline_score) >= float(lexical_threshold)
    candidate_supported = float(candidate_score) >= float(lexical_threshold)

    if baseline_supported and not candidate_supported:
        return {
            "classification": "REGRESSION",
            "reason": "lexical_support",
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
        }

    if not baseline_supported:
        return {
            "classification": "UNKNOWN",
            "reason": "baseline_below_lexical_threshold",
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
        }

    role_diff = compare_authority_roles(baseline_role, candidate_role)
    if candidate_supported and role_diff["classification"] == "REGRESSION":
        return {
            "classification": "REGRESSION",
            "reason": "authority_role",
            "baseline_score": baseline_score,
            "candidate_score": candidate_score,
            "baseline_role": baseline_role,
            "candidate_role": candidate_role,
        }

    return {
        "classification": "NO_REGRESSION_DETECTED",
        "reason": "no_high_confidence_downgrade",
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "baseline_role": baseline_role,
        "candidate_role": candidate_role,
    }
