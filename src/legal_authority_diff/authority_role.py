"""Conservative authority-role evidence classifier for V0.7.

V0.7 does not try to decide the legal holding from arbitrary opinion text.
It classifies a small retrieved evidence window by observable provenance cues so
that a differential test can notice when evidence shifts from the source case's
own rule/holding language to secondary material or attributed prior authority.

The classifier intentionally returns UNKNOWN rather than guessing.
"""

from __future__ import annotations

import re
from typing import Any


US_REPORTER_RE = re.compile(
    r"\b\d+\s+U\.?\s*S\.?\s+(?:\d+|,\s*at\s+\d+)\b",
    re.IGNORECASE,
)

CASE_NAME_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9.&'’\- ]{1,60}\s+v\.\s+"
    r"[A-Z][A-Za-z0-9.&'’\- ]{1,60}\b"
)

SECONDARY_PATTERNS = [
    re.compile(r"\bL\.\s*Rev\.", re.IGNORECASE),
    re.compile(r"\bLaw Review\b", re.IGNORECASE),
    re.compile(r"\bLaw Journal\b", re.IGNORECASE),
    re.compile(r"\bA\.L\.R\.", re.IGNORECASE),
    re.compile(r"\bAm\.\s*Jur\.", re.IGNORECASE),
    re.compile(r"\bC\.J\.S\.", re.IGNORECASE),
    re.compile(r"\bTreatise\b", re.IGNORECASE),
]

SELF_HOLDING_PATTERNS = [
    re.compile(r"\bwe\s+(?:therefore\s+|now\s+)?hold\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:therefore\s+|now\s+)?conclude\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:therefore\s+|now\s+)?decide\b", re.IGNORECASE),
    re.compile(r"\bwe\s+(?:therefore\s+|now\s+)?determine\b", re.IGNORECASE),
    re.compile(r"\bwe\s+think\s+that\b", re.IGNORECASE),
    re.compile(r"\bthe\s+court\s+(?:therefore\s+)?holds\b", re.IGNORECASE),
]

ATTRIBUTION_PATTERNS = [
    re.compile(r"\bwe\s+(?:previously\s+)?held\s+in\b", re.IGNORECASE),
    re.compile(r"\bas\s+we\s+held\s+in\b", re.IGNORECASE),
    re.compile(r"\bour\s+decision\s+in\b", re.IGNORECASE),
    re.compile(r"\bquoting\b", re.IGNORECASE),
    re.compile(r"\bquoted\s+in\b", re.IGNORECASE),
    re.compile(r"\bciting\b", re.IGNORECASE),
    re.compile(r"\bsee\s+[A-Z][A-Za-z0-9.&'’\- ]+\s+v\.\s+", re.IGNORECASE),
]


def _matched(patterns: list[re.Pattern[str]], text: str) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            matches.append(found.group(0))
    return matches


def classify_authority_role(window: str) -> dict[str, Any]:
    """Classify observable provenance cues in one source window.

    Roles:
    - REPORTER_SYLLABUS_HOLDING: official reporter syllabus says Held:.
    - COURT_SELF_HOLDING: first-person / court holding cue in the source case.
    - SECONDARY_SOURCE: law review/treatise-style material embedded in the opinion.
    - ATTRIBUTED_PRIOR_AUTHORITY: text points to another judicial authority.
    - UNKNOWN: no sufficiently specific cue.

    A window may contain prior citations while the source court states its own rule.
    Therefore self-holding cues take precedence over generic citation detection.
    """
    text = str(window or "").strip()
    if not text:
        return {
            "role": "UNKNOWN",
            "confidence": "low",
            "cues": [],
            "external_citations": [],
            "case_names": [],
        }

    secondary = _matched(SECONDARY_PATTERNS, text)
    self_holding = _matched(SELF_HOLDING_PATTERNS, text)
    attribution = _matched(ATTRIBUTION_PATTERNS, text)
    citations = US_REPORTER_RE.findall(text)
    case_names = CASE_NAME_RE.findall(text)

    if re.search(r"\bHeld\s*:", text, re.IGNORECASE):
        role = "REPORTER_SYLLABUS_HOLDING"
        confidence = "high"
        cues = ["Held:"]
    elif self_holding:
        role = "COURT_SELF_HOLDING"
        confidence = "high"
        cues = self_holding
    elif secondary:
        role = "SECONDARY_SOURCE"
        confidence = "high"
        cues = secondary
    elif attribution and (citations or case_names):
        role = "ATTRIBUTED_PRIOR_AUTHORITY"
        confidence = "high"
        cues = attribution
    elif citations or case_names:
        role = "ATTRIBUTED_PRIOR_AUTHORITY"
        confidence = "medium"
        cues = ["external judicial citation/name"]
    else:
        role = "UNKNOWN"
        confidence = "low"
        cues = []

    return {
        "role": role,
        "confidence": confidence,
        "cues": cues,
        "external_citations": citations,
        "case_names": case_names,
    }


ROLE_STRENGTH = {
    "COURT_SELF_HOLDING": 3,
    "REPORTER_SYLLABUS_HOLDING": 2,
    "UNKNOWN": 1,
    "ATTRIBUTED_PRIOR_AUTHORITY": 0,
    "SECONDARY_SOURCE": 0,
}


def compare_authority_roles(before: str, after: str) -> dict[str, Any]:
    """Compare two observable authority roles without inventing legal hierarchy."""
    if before not in ROLE_STRENGTH or after not in ROLE_STRENGTH:
        return {
            "classification": "UNKNOWN",
            "before": before,
            "after": after,
        }

    before_strength = ROLE_STRENGTH[before]
    after_strength = ROLE_STRENGTH[after]

    if before_strength >= 2 and after_strength == 0:
        classification = "REGRESSION"
    elif before_strength == 0 and after_strength >= 2:
        classification = "IMPROVEMENT"
    elif before == after:
        classification = "UNCHANGED"
    else:
        classification = "UNKNOWN"

    return {
        "classification": classification,
        "before": before,
        "after": after,
    }
