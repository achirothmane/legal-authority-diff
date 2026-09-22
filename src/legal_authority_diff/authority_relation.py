"""Target-aware precedent-relation classifier for V0.8.

The V0.7 authority-role signal can overreact when a later opinion legitimately
applies or reaffirms an earlier precedent. V0.8 therefore separates two axes:

1. what kind of evidence window was retrieved;
2. how the current source locally treats a specific earlier authority.

This module only classifies explicit local cues. It is not a citator and it does
not determine whether a precedent remains good law outside the inspected source.
"""

from __future__ import annotations

import re
from typing import Any

from .govinfo import parse_us_reports_citation


def normalize_source_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\u00ad", "")
    value = value.replace("\u2018", "'").replace("\u2019", "'")
    value = value.replace("\u201c", '"').replace("\u201d", '"')
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _citation_pattern(citation: str) -> re.Pattern[str]:
    volume, page = parse_us_reports_citation(citation)
    return re.compile(
        rf"\b{volume}\s+U\.?\s*S\.?\s*,?\s*{page}\b",
        re.IGNORECASE,
    )


def extract_anchor_context(
    source_text: str,
    anchor: str,
    *,
    radius: int = 320,
) -> str:
    source = normalize_source_text(source_text)
    needle = normalize_source_text(anchor)
    if not source or not needle:
        return ""

    index = source.lower().find(needle.lower())
    if index < 0:
        return ""

    span = max(0, int(radius))
    start = max(0, index - span)
    end = min(len(source), index + len(needle) + span)
    return source[start:end]


def _target_present(
    context: str,
    *,
    target_citation: str,
    target_term: str | None,
) -> bool:
    if _citation_pattern(target_citation).search(context):
        return True
    if target_term:
        term = normalize_source_text(target_term)
        if term and term.lower() in context.lower():
            return True
    return False


AFFIRMATIVE_PATTERNS = [
    re.compile(r"\bdeclines?\s+to\s+overrule\b", re.IGNORECASE),
    re.compile(r"\breaffirm(?:s|ed|ing)?\b", re.IGNORECASE),
    re.compile(r"\bis\s+governed\s+by\b", re.IGNORECASE),
    re.compile(r"\bapplies?\s+to\b", re.IGNORECASE),
    re.compile(r"\bapply(?:ing|ied)?\b.{0,80}\bframework\b", re.IGNORECASE),
    re.compile(r"\bprevail\s+on\s+(?:his|her|the)\b.{0,60}\bclaim\b", re.IGNORECASE),
    re.compile(r"\bgatekeeping\b.{0,80}\bapplies?\b", re.IGNORECASE),
]

DISTINGUISH_PATTERNS = [
    re.compile(r"\bin\s+contrast\s+to\b", re.IGNORECASE),
    re.compile(r"\bunlike\b", re.IGNORECASE),
    re.compile(r"\bdistinguish(?:ed|es|ing)?\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+mandate\b", re.IGNORECASE),
    re.compile(r"\bdoes\s+not\s+apply\b", re.IGNORECASE),
    re.compile(r"\bdid\s+not\s+apply\b", re.IGNORECASE),
    re.compile(r"\bnot\s+triggered\b", re.IGNORECASE),
]

NEGATIVE_TREATMENT_PATTERNS = [
    re.compile(r"\bshould\s+be\s+and\s+now\s+is\s+overruled\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:therefore\s+)?overrule\b", re.IGNORECASE),
    re.compile(r"\bis\s+hereby\s+overruled\b", re.IGNORECASE),
    re.compile(r"\bis\s+overruled\b", re.IGNORECASE),
]


def _matches(patterns: list[re.Pattern[str]], text: str) -> list[str]:
    values: list[str] = []
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            values.append(match.group(0))
    return values


def classify_precedent_relation(
    context: str,
    *,
    target_citation: str,
    target_term: str | None = None,
) -> dict[str, Any]:
    """Classify explicit local treatment of one target precedent.

    Labels:
    - AFFIRMATIVE_USE: applies, reaffirms, or expressly keeps the precedent.
    - DISTINGUISHES_OR_LIMITS: contrasts or limits the target in this context.
    - NEGATIVE_TREATMENT: expressly overrules the target.
    - MENTION_ONLY: target is present but no stronger local cue is found.
    - UNKNOWN: target is absent or context is unusable.
    """
    text = normalize_source_text(context)
    if not text:
        return {"relation": "UNKNOWN", "confidence": "low", "cues": []}

    if not _target_present(
        text,
        target_citation=target_citation,
        target_term=target_term,
    ):
        return {"relation": "UNKNOWN", "confidence": "low", "cues": []}

    affirmative = _matches(AFFIRMATIVE_PATTERNS, text)
    if affirmative:
        return {
            "relation": "AFFIRMATIVE_USE",
            "confidence": "high",
            "cues": affirmative,
        }

    negative = _matches(NEGATIVE_TREATMENT_PATTERNS, text)
    if negative:
        return {
            "relation": "NEGATIVE_TREATMENT",
            "confidence": "high",
            "cues": negative,
        }

    distinguish = _matches(DISTINGUISH_PATTERNS, text)
    if distinguish:
        return {
            "relation": "DISTINGUISHES_OR_LIMITS",
            "confidence": "high",
            "cues": distinguish,
        }

    return {
        "relation": "MENTION_ONLY",
        "confidence": "medium",
        "cues": ["target authority present without stronger local cue"],
    }
