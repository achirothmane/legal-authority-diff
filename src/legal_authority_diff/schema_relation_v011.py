"""V0.11 schema-constrained precedent relation extraction.

This module defines the contract between an LLM extractor and the deterministic
policy layer. The model is allowed to extract discourse structure; it is not
allowed to decide the CI consequence directly.

Key design rule:

    model output -> strict validation -> deterministic treatment mapping -> policy

The validator requires evidence spans to be grounded in the supplied context and
rejects treatment labels that disagree with the declared current-court stance.
"""

from __future__ import annotations

import re
from typing import Any

from .authority_relation_v09 import normalize_source_text


PROPOSITION_OWNERS = {
    "CURRENT_COURT",
    "TARGET_AUTHORITY",
    "OTHER_AUTHORITY",
    "PARTY",
    "SEPARATE_OPINION",
    "UNKNOWN",
}

CURRENT_COURT_STANCES = {
    "ADOPTS",
    "APPLIES",
    "RELIES_ON",
    "REAFFIRMS",
    "DECLINES_TO_OVERRULE",
    "DISTINGUISHES",
    "DECLINES_TO_EXTEND",
    "LIMITS",
    "OVERRULES",
    "WEAKENS",
    "DISAPPROVES",
    "DESCRIBES",
    "CITES",
    "QUOTES",
    "UNRESOLVED",
}

TREATMENTS = {
    "AFFIRMATIVE_USE",
    "DISTINGUISHES_OR_LIMITS",
    "NEGATIVE_TREATMENT",
    "MENTION_ONLY",
    "UNKNOWN",
}

CLAIM_CONSEQUENCES = {
    "SUPPORTS",
    "LIMITS",
    "INVALIDATES",
    "NONE",
    "UNKNOWN",
}

EVIDENCE_ROLES = {
    "TARGET_MENTION",
    "PROPOSITION",
    "STANCE",
    "CONSEQUENCE",
}

CONFIDENCE_LEVELS = {"low", "medium", "high"}

AFFIRMATIVE_STANCES = {
    "ADOPTS",
    "APPLIES",
    "RELIES_ON",
    "REAFFIRMS",
    "DECLINES_TO_OVERRULE",
}

LIMITING_STANCES = {
    "DISTINGUISHES",
    "DECLINES_TO_EXTEND",
    "LIMITS",
}

NEGATIVE_STANCES = {
    "OVERRULES",
    "WEAKENS",
    "DISAPPROVES",
}

MENTION_STANCES = {
    "DESCRIBES",
    "CITES",
    "QUOTES",
}


RELATION_EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_authority": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "citation": {"type": "string"},
                "resolved": {"type": "boolean"},
            },
            "required": ["name", "citation", "resolved"],
            "additionalProperties": False,
        },
        "proposition": {"type": "string"},
        "proposition_owner": {
            "type": "string",
            "enum": sorted(PROPOSITION_OWNERS),
        },
        "current_court_stance": {
            "type": "string",
            "enum": sorted(CURRENT_COURT_STANCES),
        },
        "treatment": {
            "type": "string",
            "enum": sorted(TREATMENTS),
        },
        "claim_consequence": {
            "type": "string",
            "enum": sorted(CLAIM_CONSEQUENCES),
        },
        "evidence_spans": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "role": {
                        "type": "string",
                        "enum": sorted(EVIDENCE_ROLES),
                    },
                },
                "required": ["text", "role"],
                "additionalProperties": False,
            },
        },
        "confidence": {
            "type": "string",
            "enum": sorted(CONFIDENCE_LEVELS),
        },
        "abstain": {"type": "boolean"},
        "abstention_reason": {
            "type": ["string", "null"],
        },
    },
    "required": [
        "target_authority",
        "proposition",
        "proposition_owner",
        "current_court_stance",
        "treatment",
        "claim_consequence",
        "evidence_spans",
        "confidence",
        "abstain",
        "abstention_reason",
    ],
    "additionalProperties": False,
}


EXPECTED_TOP_LEVEL_KEYS = set(RELATION_EXTRACTION_JSON_SCHEMA["required"])
EXPECTED_TARGET_KEYS = {"name", "citation", "resolved"}
EXPECTED_EVIDENCE_KEYS = {"text", "role"}


def treatment_from_stance(stance: str) -> str:
    if stance in AFFIRMATIVE_STANCES:
        return "AFFIRMATIVE_USE"
    if stance in LIMITING_STANCES:
        return "DISTINGUISHES_OR_LIMITS"
    if stance in NEGATIVE_STANCES:
        return "NEGATIVE_TREATMENT"
    if stance in MENTION_STANCES:
        return "MENTION_ONLY"
    return "UNKNOWN"


def _citation_key(value: str) -> str:
    value = value.lower().replace("u. s.", "u.s.").replace("u. s", "u.s")
    return re.sub(r"[^a-z0-9]+", "", value)


def _grounded_span(context: str, span: str) -> bool:
    haystack = normalize_source_text(context).lower()
    needle = normalize_source_text(span).lower()
    return bool(needle) and needle in haystack


def validate_relation_extraction(
    extraction: dict[str, Any],
    *,
    context: str,
    expected_target_name: str,
    expected_target_citation: str,
) -> dict[str, Any]:
    """Validate an LLM extraction without repairing or guessing its semantics.

    Returns:
        {
          "valid": bool,
          "errors": [...],
          "derived_treatment": str,
          "grounded_evidence_count": int,
        }

    Invalid model output must not be silently converted into a blocking result.
    """
    errors: list[str] = []

    if not isinstance(extraction, dict):
        return {
            "valid": False,
            "errors": ["extraction_not_object"],
            "derived_treatment": "UNKNOWN",
            "grounded_evidence_count": 0,
        }

    keys = set(extraction)
    missing = sorted(EXPECTED_TOP_LEVEL_KEYS - keys)
    extra = sorted(keys - EXPECTED_TOP_LEVEL_KEYS)
    if missing:
        errors.append("missing_keys:" + ",".join(missing))
    if extra:
        errors.append("extra_keys:" + ",".join(extra))

    target = extraction.get("target_authority")
    if not isinstance(target, dict):
        errors.append("target_authority_not_object")
        target = {}
    else:
        target_keys = set(target)
        target_missing = sorted(EXPECTED_TARGET_KEYS - target_keys)
        target_extra = sorted(target_keys - EXPECTED_TARGET_KEYS)
        if target_missing:
            errors.append("target_missing_keys:" + ",".join(target_missing))
        if target_extra:
            errors.append("target_extra_keys:" + ",".join(target_extra))

    target_name = target.get("name")
    target_citation = target.get("citation")
    target_resolved = target.get("resolved")

    if not isinstance(target_name, str):
        errors.append("target_name_not_string")
    if not isinstance(target_citation, str):
        errors.append("target_citation_not_string")
    elif _citation_key(target_citation) != _citation_key(expected_target_citation):
        errors.append("target_citation_mismatch")
    if not isinstance(target_resolved, bool):
        errors.append("target_resolved_not_boolean")

    proposition = extraction.get("proposition")
    if not isinstance(proposition, str):
        errors.append("proposition_not_string")

    owner = extraction.get("proposition_owner")
    if owner not in PROPOSITION_OWNERS:
        errors.append("invalid_proposition_owner")

    stance = extraction.get("current_court_stance")
    if stance not in CURRENT_COURT_STANCES:
        errors.append("invalid_current_court_stance")
        derived = "UNKNOWN"
    else:
        derived = treatment_from_stance(stance)

    treatment = extraction.get("treatment")
    if treatment not in TREATMENTS:
        errors.append("invalid_treatment")
    elif treatment != derived:
        errors.append(
            f"treatment_stance_mismatch:{treatment}!={derived}"
        )

    consequence = extraction.get("claim_consequence")
    if consequence not in CLAIM_CONSEQUENCES:
        errors.append("invalid_claim_consequence")

    confidence = extraction.get("confidence")
    if confidence not in CONFIDENCE_LEVELS:
        errors.append("invalid_confidence")

    abstain = extraction.get("abstain")
    if not isinstance(abstain, bool):
        errors.append("abstain_not_boolean")

    abstention_reason = extraction.get("abstention_reason")
    if abstention_reason is not None and not isinstance(abstention_reason, str):
        errors.append("abstention_reason_not_string_or_null")

    if abstain is True:
        if treatment != "UNKNOWN":
            errors.append("abstain_requires_unknown_treatment")
        if confidence != "low":
            errors.append("abstain_requires_low_confidence")
        if not isinstance(abstention_reason, str) or not abstention_reason.strip():
            errors.append("abstain_requires_reason")
    elif abstain is False:
        if isinstance(abstention_reason, str) and abstention_reason.strip():
            errors.append("non_abstain_must_not_have_reason")

    if target_resolved is False:
        if abstain is not True:
            errors.append("unresolved_target_requires_abstain")
        if stance != "UNRESOLVED":
            errors.append("unresolved_target_requires_unresolved_stance")

    evidence = extraction.get("evidence_spans")
    grounded_count = 0
    roles: set[str] = set()
    if not isinstance(evidence, list):
        errors.append("evidence_spans_not_array")
        evidence = []
    elif len(evidence) > 8:
        errors.append("too_many_evidence_spans")

    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            errors.append(f"evidence_{index}_not_object")
            continue

        item_keys = set(item)
        item_missing = sorted(EXPECTED_EVIDENCE_KEYS - item_keys)
        item_extra = sorted(item_keys - EXPECTED_EVIDENCE_KEYS)
        if item_missing:
            errors.append(
                f"evidence_{index}_missing_keys:" + ",".join(item_missing)
            )
        if item_extra:
            errors.append(
                f"evidence_{index}_extra_keys:" + ",".join(item_extra)
            )

        text = item.get("text")
        role = item.get("role")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"evidence_{index}_empty_text")
        elif not _grounded_span(context, text):
            errors.append(f"evidence_{index}_not_grounded")
        else:
            grounded_count += 1

        if role not in EVIDENCE_ROLES:
            errors.append(f"evidence_{index}_invalid_role")
        else:
            roles.add(role)

    if abstain is False and derived != "UNKNOWN":
        if grounded_count == 0:
            errors.append("non_unknown_requires_grounded_evidence")
        if "STANCE" not in roles:
            errors.append("non_unknown_requires_stance_evidence")

    if target_resolved is True and abstain is False and "TARGET_MENTION" not in roles:
        errors.append("resolved_target_requires_target_evidence")

    if (
        owner == "TARGET_AUTHORITY"
        and isinstance(proposition, str)
        and proposition.strip()
        and "PROPOSITION" not in roles
    ):
        errors.append("target_owned_proposition_requires_proposition_evidence")

    return {
        "valid": not errors,
        "errors": errors,
        "derived_treatment": derived,
        "grounded_evidence_count": grounded_count,
    }


def safe_treatment(
    extraction: dict[str, Any],
    *,
    context: str,
    expected_target_name: str,
    expected_target_citation: str,
) -> dict[str, Any]:
    """Return a fail-open treatment envelope for downstream policy.

    Invalid extractions become UNKNOWN rather than a guessed legal conclusion.
    """
    validation = validate_relation_extraction(
        extraction,
        context=context,
        expected_target_name=expected_target_name,
        expected_target_citation=expected_target_citation,
    )
    if not validation["valid"]:
        return {
            "treatment": "UNKNOWN",
            "usable": False,
            "reason": "schema_or_grounding_failure",
            "validation": validation,
        }

    if extraction.get("abstain") is True or validation["derived_treatment"] == "UNKNOWN":
        return {
            "treatment": "UNKNOWN",
            "usable": False,
            "reason": "validated_abstention",
            "validation": validation,
        }

    return {
        "treatment": validation["derived_treatment"],
        "usable": True,
        "reason": "validated_structured_extraction",
        "validation": validation,
    }
