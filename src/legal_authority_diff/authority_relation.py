"""Target-scoped precedent-relation classifier for V0.9.

V0.8 proved that precedent relationship is a useful guardrail around
authority-role provenance. V0.9 hardens that idea against a harder failure:
relation words such as "overrule", "apply", or "distinguish" may refer to a
different authority that merely appears in the same passage.

The classifier therefore links relation cues to the requested target citation or
target name. It remains a local textual signal, not a citator and not a current-
law determination.
"""

from __future__ import annotations

import re
from typing import Any

from .govinfo import parse_us_reports_citation


def normalize_source_text(text: str) -> str:
    value = str(text or "")
    value = value.replace("\u00ad", "")
    value = value.replace("\u2010", "-").replace("\u2011", "-")
    value = value.replace("\u2012", "-").replace("\u2013", "-").replace("\u2014", "-")
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


def _ocr_tolerant_anchor_pattern(anchor: str) -> re.Pattern[str]:
    """Fallback matcher for PDF OCR that inserts whitespace inside words."""
    normalized = normalize_source_text(anchor)
    pieces: list[str] = []
    for char in normalized:
        if char.isalnum():
            pieces.append(re.escape(char))
            pieces.append(r"\s*")
        elif char.isspace():
            pieces.append(r"\s*")
        else:
            pieces.append(r"[^\w]*")
    return re.compile("".join(pieces), re.IGNORECASE)


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
    match_length = len(needle)

    if index < 0:
        fuzzy = _ocr_tolerant_anchor_pattern(needle).search(source)
        if fuzzy is None:
            return ""
        index = fuzzy.start()
        match_length = fuzzy.end() - fuzzy.start()

    span = max(0, int(radius))
    start = max(0, index - span)
    end = min(len(source), index + match_length + span)
    return source[start:end]


def _target_regex_source(
    target_citation: str,
    target_term: str | None,
) -> str:
    sources = [f"(?:{_citation_pattern(target_citation).pattern})"]
    if target_term:
        sources.append(f"(?:{_ocr_tolerant_anchor_pattern(target_term).pattern})")
    return "(?:" + "|".join(sources) + ")"


def _target_present(
    context: str,
    *,
    target_citation: str,
    target_term: str | None,
) -> bool:
    target = re.compile(
        _target_regex_source(target_citation, target_term),
        re.IGNORECASE,
    )
    return target.search(context) is not None


def _compile_target_patterns(
    target_source: str,
) -> dict[str, list[re.Pattern[str]]]:
    target = target_source
    flags = re.IGNORECASE

    affirmative = [
        re.compile(
            rf"\bdeclines?\s+to\s+overrule\s+(?:[^.;:]{{0,40}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"\breaffirm(?:s|ed|ing)?\s+(?:[^.;:]{{0,50}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"\b(?:is|are|was|were)\s+governed\s+by\s+{target}",
            flags,
        ),
        re.compile(
            rf"\b(?:under|following|pursuant\s+to)\s+{target}",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:applies?|governs?|controls?)\b",
            flags,
        ),
        re.compile(
            rf"\b(?:apply|applies|applied|applying)\s+(?:[^.;:]{{0,50}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,120}}\b(?:framework|rule|standard)\b.{{0,80}}"
            rf"\b(?:applies?|governs?|controls?)\b",
            flags,
        ),
    ]

    distinguish = [
        re.compile(rf"\bin\s+contrast\s+to\s+{target}", flags),
        re.compile(rf"\bunlike\s+(?:in\s+)?{target}", flags),
        re.compile(
            rf"\bdistinguish(?:ed|es|ing)?\s+(?:[^.;:]{{0,40}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:does|did)\s+not\s+"
            rf"(?:apply|mandate|control|govern|require)\b",
            flags,
        ),
        re.compile(
            rf"\bdeclines?\s+to\s+extend\s+(?:[^.;:]{{0,30}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was)\s+distinguishable\b",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was)\s+limited\s+to\b",
            flags,
        ),
    ]

    negative = [
        re.compile(
            rf"{target}.{{0,90}}\bshould\s+be\s+and\s+now\s+is\s+overruled\b",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was|has\s+been)\s+"
            rf"(?:expressly\s+)?overruled\b",
            flags,
        ),
        re.compile(
            rf"\bwe\s+(?:therefore\s+)?overrule\s+(?:[^.;:]{{0,40}}\s+)?{target}",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was|has\s+been)\s+abrogated\b",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was)\s+no\s+longer\s+controlling\b",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:has\s+been|was)\s+undermined\b",
            flags,
        ),
        re.compile(
            rf"{target}.{{0,90}}\b(?:is|was)\s+disapproved\b",
            flags,
        ),
    ]

    return {
        "AFFIRMATIVE_USE": affirmative,
        "DISTINGUISHES_OR_LIMITS": distinguish,
        "NEGATIVE_TREATMENT": negative,
    }


def _matches(
    patterns: list[re.Pattern[str]],
    text: str,
) -> list[str]:
    values: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = match.group(0)
            if value not in values:
                values.append(value)
    return values


def classify_precedent_relation(
    context: str,
    *,
    target_citation: str,
    target_term: str | None = None,
) -> dict[str, Any]:
    """Classify explicit local treatment of one target precedent.

    Labels:
    - AFFIRMATIVE_USE
    - DISTINGUISHES_OR_LIMITS
    - NEGATIVE_TREATMENT
    - MIXED_OR_CONFLICTING
    - MENTION_ONLY
    - UNKNOWN

    V0.9 only credits relation cues that are syntactically linked to the target
    citation/name. Relation words about a different authority are ignored.
    """
    text = normalize_source_text(context)
    if not text:
        return {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": [],
            "categories": [],
        }

    if not _target_present(
        text,
        target_citation=target_citation,
        target_term=target_term,
    ):
        return {
            "relation": "UNKNOWN",
            "confidence": "low",
            "cues": [],
            "categories": [],
        }

    target_source = _target_regex_source(target_citation, target_term)
    compiled = _compile_target_patterns(target_source)

    matched: dict[str, list[str]] = {
        label: _matches(patterns, text)
        for label, patterns in compiled.items()
    }
    categories = [
        label
        for label, cues in matched.items()
        if cues
    ]

    if len(categories) > 1:
        cues: list[str] = []
        for label in categories:
            cues.extend(matched[label])
        return {
            "relation": "MIXED_OR_CONFLICTING",
            "confidence": "high",
            "cues": cues,
            "categories": categories,
        }

    if len(categories) == 1:
        relation = categories[0]
        return {
            "relation": relation,
            "confidence": "high",
            "cues": matched[relation],
            "categories": categories,
        }

    return {
        "relation": "MENTION_ONLY",
        "confidence": "medium",
        "cues": ["target authority present without target-linked relation cue"],
        "categories": [],
    }
