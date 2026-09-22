"""Deterministic differential engine for legal-authority regressions."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


AUTHORITY_STRENGTH = {
    "controlling": 3,
    "binding": 3,
    "mandatory": 3,
    "persuasive": 2,
    "secondary": 1,
    "unknown": 0,
}

SUPPORT_STRENGTH = {
    "contradicted": 0,
    "unsupported": 1,
    "partial": 2,
    "supported": 3,
}

NEGATIVE_TREATMENTS = {
    "overruled",
    "superseded",
    "reversed",
    "vacated",
    "invalid",
    "negative",
}


def _norm(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    return str(value).strip().lower().replace(" ", "_")


def _authority(case: dict[str, Any]) -> dict[str, Any]:
    value = case.get("authority")
    return value if isinstance(value, dict) else {}


def _change(kind: str, before: Any, after: Any, reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "before": before,
        "after": after,
        "reason": reason,
    }


def classify_pair(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Classify one baseline/candidate pair.

    V0.1 is intentionally conservative. It blocks only deterministic
    regressions and returns UNKNOWN when legal equivalence cannot be inferred
    from the supplied metadata.
    """
    case_id = baseline.get("case_id") or candidate.get("case_id")
    base_auth = _authority(baseline)
    cand_auth = _authority(candidate)

    if bool(candidate.get("world_change")):
        return {
            "case_id": case_id,
            "classification": "WORLD_CHANGE",
            "blocking": False,
            "changes": [
                _change(
                    "world_change",
                    baseline.get("world_change", False),
                    True,
                    candidate.get("world_change_reason")
                    or "Candidate marks a change in the underlying law or legal world state.",
                )
            ],
        }

    changes: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []

    base_exists = base_auth.get("exists", True)
    cand_exists = cand_auth.get("exists", True)

    if base_exists is True and cand_exists is False:
        regressions.append(
            _change(
                "citation_existence",
                True,
                False,
                "A citation that existed in the baseline is missing or fabricated in the candidate.",
            )
        )
    elif base_exists is False and cand_exists is True:
        improvements.append(
            _change(
                "citation_existence",
                False,
                True,
                "The candidate resolves a citation that did not exist in the baseline.",
            )
        )

    base_treatment = _norm(base_auth.get("treatment"))
    cand_treatment = _norm(cand_auth.get("treatment"))

    if (
        base_treatment not in NEGATIVE_TREATMENTS
        and cand_treatment in NEGATIVE_TREATMENTS
    ):
        regressions.append(
            _change(
                "treatment",
                base_treatment,
                cand_treatment,
                "The candidate relies on authority with newly negative treatment.",
            )
        )
    elif (
        base_treatment in NEGATIVE_TREATMENTS
        and cand_treatment not in NEGATIVE_TREATMENTS
        and cand_treatment != "unknown"
    ):
        improvements.append(
            _change(
                "treatment",
                base_treatment,
                cand_treatment,
                "The candidate improves the authority treatment status.",
            )
        )

    base_status = _norm(base_auth.get("status"))
    cand_status = _norm(cand_auth.get("status"))
    base_rank = AUTHORITY_STRENGTH.get(base_status, 0)
    cand_rank = AUTHORITY_STRENGTH.get(cand_status, 0)

    if base_status != cand_status:
        if cand_rank < base_rank:
            regressions.append(
                _change(
                    "authority_strength",
                    base_status,
                    cand_status,
                    "The candidate weakened the authority class.",
                )
            )
        elif cand_rank > base_rank:
            improvements.append(
                _change(
                    "authority_strength",
                    base_status,
                    cand_status,
                    "The candidate strengthened the authority class.",
                )
            )
        elif base_rank == cand_rank == 0:
            unknowns.append(
                _change(
                    "authority_strength",
                    base_status,
                    cand_status,
                    "Authority classes differ but V0.1 cannot rank them.",
                )
            )

    base_support = _norm(baseline.get("support"))
    cand_support = _norm(candidate.get("support"))
    base_support_rank = SUPPORT_STRENGTH.get(base_support)
    cand_support_rank = SUPPORT_STRENGTH.get(cand_support)

    if base_support != cand_support:
        if base_support_rank is None or cand_support_rank is None:
            unknowns.append(
                _change(
                    "proposition_support",
                    base_support,
                    cand_support,
                    "Proposition support changed but V0.1 cannot rank one of the values.",
                )
            )
        elif cand_support_rank < base_support_rank:
            regressions.append(
                _change(
                    "proposition_support",
                    base_support,
                    cand_support,
                    "The candidate weakened support for the tested legal proposition.",
                )
            )
        elif cand_support_rank > base_support_rank:
            improvements.append(
                _change(
                    "proposition_support",
                    base_support,
                    cand_support,
                    "The candidate strengthened support for the tested legal proposition.",
                )
            )

    base_jurisdiction = _norm(base_auth.get("jurisdiction"))
    cand_jurisdiction = _norm(cand_auth.get("jurisdiction"))
    if (
        base_jurisdiction != cand_jurisdiction
        and base_jurisdiction != "unknown"
        and cand_jurisdiction != "unknown"
        and not any(c["kind"] == "authority_strength" for c in regressions)
    ):
        unknowns.append(
            _change(
                "jurisdiction",
                base_jurisdiction,
                cand_jurisdiction,
                "Jurisdiction changed without a deterministic authority-strength downgrade; legal equivalence requires review.",
            )
        )

    base_citation = base_auth.get("citation")
    cand_citation = cand_auth.get("citation")
    if base_citation != cand_citation:
        changes.append(
            _change(
                "citation",
                base_citation,
                cand_citation,
                "The cited authority changed.",
            )
        )

    changes = regressions + improvements + unknowns + changes

    if regressions:
        classification = "REGRESSION"
        blocking = True
    elif unknowns:
        classification = "UNKNOWN"
        blocking = False
    elif improvements:
        classification = "IMPROVEMENT"
        blocking = False
    else:
        classification = "UNCHANGED"
        blocking = False

    return {
        "case_id": case_id,
        "classification": classification,
        "blocking": blocking,
        "changes": changes,
    }


def _index(cases: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = case.get("case_id")
        if not case_id:
            raise ValueError("Every JSONL object must contain a non-empty case_id.")
        if case_id in indexed:
            raise ValueError(f"Duplicate case_id: {case_id}")
        indexed[str(case_id)] = case
    return indexed


def diff_runs(
    baseline_cases: Iterable[dict[str, Any]],
    candidate_cases: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two runs by case_id and return a machine-readable report."""
    baseline = _index(baseline_cases)
    candidate = _index(candidate_cases)

    results: list[dict[str, Any]] = []

    for case_id, base_case in baseline.items():
        cand_case = candidate.get(case_id)
        if cand_case is None:
            results.append(
                {
                    "case_id": case_id,
                    "classification": "UNKNOWN",
                    "blocking": False,
                    "changes": [
                        _change(
                            "missing_candidate_case",
                            "present",
                            "missing",
                            "The candidate run does not contain this baseline case.",
                        )
                    ],
                }
            )
            continue
        results.append(classify_pair(base_case, cand_case))

    for case_id in candidate.keys() - baseline.keys():
        results.append(
            {
                "case_id": case_id,
                "classification": "UNKNOWN",
                "blocking": False,
                "changes": [
                    _change(
                        "new_candidate_case",
                        "missing",
                        "present",
                        "The candidate contains a case with no baseline for differential comparison.",
                    )
                ],
            }
        )

    counts = Counter(item["classification"] for item in results)
    blocking = any(item["blocking"] for item in results)

    if blocking:
        decision = "BLOCK"
    elif counts["UNKNOWN"] or counts["WORLD_CHANGE"]:
        decision = "REVIEW"
    else:
        decision = "PASS"

    summary = {
        "cases_evaluated": len(results),
        "regressions": counts["REGRESSION"],
        "improvements": counts["IMPROVEMENT"],
        "unchanged": counts["UNCHANGED"],
        "unknown": counts["UNKNOWN"],
        "world_change": counts["WORLD_CHANGE"],
        "decision": decision,
    }

    return {"summary": summary, "cases": results}
