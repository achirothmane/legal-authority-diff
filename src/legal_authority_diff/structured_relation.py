"""Structured precedent-relation extraction experiment for V0.10.

V0.9 failed because phrase-level patterns could not reliably answer a more basic
question: whose proposition is being stated?

V0.10 extracts a small discourse frame before assigning a relation:

    target authority
        -> attribution owner
        -> proposition span
        -> current-court treatment cues
        -> relation

The extractor is intentionally conservative. It can abstain and it keeps
attributed holding content separate from treatment by the current court.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .authority_relation_v09 import (
    _citation_pattern,
    _ocr_tolerant_anchor_pattern,
    normalize_source_text,
)


@dataclass
class RelationFrame:
    target_present: bool
    attribution_owner: str
    attributed_proposition: str
    current_court_actions: list[str]
    current_court_cues: list[str]
    relation: str
    confidence: str
    abstention_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _target_source(
    target_citation: str,
    target_term: str | None,
) -> str:
    parts = [f"(?:{_citation_pattern(target_citation).pattern})"]
    if target_term:
        parts.append(f"(?:{_ocr_tolerant_anchor_pattern(target_term).pattern})")
    return "(?:" + "|".join(parts) + ")"


def _target_present(
    text: str,
    *,
    target_citation: str,
    target_term: str | None,
) -> bool:
    pattern = re.compile(
        _target_source(target_citation, target_term),
        re.IGNORECASE,
    )
    return pattern.search(text) is not None


def _sentenceish_chunks(text: str) -> list[str]:
    # U.S. Reports PDF text can contain abbreviations such as U.S. and v.
    # Use punctuation plus a capital/quote lookahead rather than splitting every period.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", text)
    return [part.strip() for part in parts if part.strip()]


def _target_chunks(
    text: str,
    *,
    target_citation: str,
    target_term: str | None,
    neighbor_count: int = 1,
) -> list[str]:
    chunks = _sentenceish_chunks(text)
    target = re.compile(
        _target_source(target_citation, target_term),
        re.IGNORECASE,
    )

    selected: list[str] = []
    for index, chunk in enumerate(chunks):
        if not target.search(chunk):
            continue
        start = max(0, index - neighbor_count)
        end = min(len(chunks), index + neighbor_count + 1)
        window = " ".join(chunks[start:end])
        if window not in selected:
            selected.append(window)
    return selected


ATTRIBUTED_HOLDING_PATTERNS = [
    re.compile(
        r"\b(?:specifically,\s*)?in\s+(?P<target>.+?),\s+"
        r"(?:this\s+Court|the\s+Court)\s+(?:had\s+)?held\s+(?:that\s+)?"
        r"(?P<prop>.+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<target>.+?)\s+(?:held|stated|explained)\s+(?:that\s+)?"
        r"(?P<prop>.+)",
        re.IGNORECASE,
    ),
]

CURRENT_COURT_AFFIRMATIVE = [
    ("APPLY", re.compile(r"\bunder\b.{0,110}", re.IGNORECASE)),
    ("APPLY", re.compile(r"\bin\s+light\s+of\b.{0,110}", re.IGNORECASE)),
    ("APPLY", re.compile(r"\bas\s+we\s+(?:stated|explained|held)\s+in\b.{0,110}", re.IGNORECASE)),
    ("APPLY", re.compile(r"\bwe\s+hold\b.{0,180}", re.IGNORECASE)),
    ("APPLY", re.compile(r"\b(?:framework|rule|standard)\b.{0,100}\b(?:applies?|governs?|controls?)\b", re.IGNORECASE)),
    ("APPLY", re.compile(r"\b(?:applies?|governs?|controls?)\b.{0,80}", re.IGNORECASE)),
    ("KEEP", re.compile(r"\bdeclines?\s+to\s+overrule\b.{0,120}", re.IGNORECASE)),
    ("KEEP", re.compile(r"\breaffirm(?:s|ed|ing)?\b.{0,120}", re.IGNORECASE)),
]

CURRENT_COURT_LIMIT = [
    ("LIMIT", re.compile(r"\bdeclines?\s+to\s+extend\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bin\s+contrast\s+to\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bunlike\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bdistinguish(?:ed|es|ing)?\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bprovides?\s+no\s+support\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bdeparts?\s+from\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\b(?:does|did)\s+not\s+(?:apply|mandate|control|govern|require)\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\birrelevant\s+to\b.{0,120}", re.IGNORECASE)),
    ("LIMIT", re.compile(r"\bnot\s+relevant\s+to\b.{0,120}", re.IGNORECASE)),
]

CURRENT_COURT_NEGATIVE = [
    ("OVERRULE", re.compile(r"\bshould\s+be\s+and\s+now\s+is\s+overruled\b", re.IGNORECASE)),
    ("OVERRULE", re.compile(r"\bwe\s+(?:therefore\s+)?overrule\b.{0,140}", re.IGNORECASE)),
    ("OVERRULE", re.compile(r"\b(?:is|are|was|were|has\s+been)\s+(?:expressly\s+)?overruled\b", re.IGNORECASE)),
    ("ABROGATE", re.compile(r"\b(?:is|are|was|were|has\s+been)\s+abrogated\b", re.IGNORECASE)),
    ("DISAPPROVE", re.compile(r"\b(?:is|are|was|were)\s+disapproved\b", re.IGNORECASE)),
    ("WEAKEN", re.compile(r"\bno\s+longer\s+(?:controlling|binding|good\s+law)\b", re.IGNORECASE)),
    ("WEAKEN", re.compile(r"\bshould\s+no\s+longer\s+be\s+regarded\s+as\s+mandatory\b", re.IGNORECASE)),
]


def _strip_attributed_holding_content(
    chunk: str,
    *,
    target_pattern: re.Pattern[str],
) -> tuple[str, str]:
    """Return (remaining treatment text, attributed proposition).

    If the chunk says that the target itself "held that X", X is proposition
    content owned by the target authority. It must not be reinterpreted as the
    current court limiting that target merely because X contains words such as
    "does not require".
    """
    normalized = chunk.strip()

    target_match = target_pattern.search(normalized)
    if target_match is None:
        return normalized, ""

    after_target = normalized[target_match.start():]

    holder = re.search(
        r"(?:,\s*)?(?:this\s+Court|the\s+Court)?\s*"
        r"(?:had\s+)?held\s+(?:that\s+)?",
        after_target,
        re.IGNORECASE,
    )
    if holder is None:
        return normalized, ""

    absolute_start = target_match.start() + holder.end()
    proposition = normalized[absolute_start:].strip()

    # Keep text before the attributed proposition for treatment analysis. This
    # preserves clauses such as "we now overrule X" that occur before it.
    remaining = normalized[:absolute_start].strip()
    return remaining, proposition


def _collect_actions(
    text: str,
    *,
    target_pattern: re.Pattern[str],
) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    cues: list[str] = []

    if not text:
        return actions, cues

    target_spans = [match.span() for match in target_pattern.finditer(text)]
    if not target_spans:
        return actions, cues

    patterns = (
        CURRENT_COURT_NEGATIVE
        + CURRENT_COURT_LIMIT
        + CURRENT_COURT_AFFIRMATIVE
    )

    for action, pattern in patterns:
        for match in pattern.finditer(text):
            # Require the treatment cue to live close to a target mention.
            # This is relation linking, not mere passage-level keyword matching.
            cue_start, cue_end = match.span()
            distance = min(
                min(abs(cue_start - target_end), abs(target_start - cue_end))
                for target_start, target_end in target_spans
            )
            if distance > 180:
                continue

            value = match.group(0).strip()
            if action not in actions:
                actions.append(action)
            if value not in cues:
                cues.append(value)

    return actions, cues


def _relation_from_actions(actions: list[str]) -> tuple[str, str]:
    kinds = set(actions)
    has_affirmative = bool(kinds & {"APPLY", "KEEP"})
    has_limit = "LIMIT" in kinds
    has_negative = bool(kinds & {"OVERRULE", "ABROGATE", "DISAPPROVE", "WEAKEN"})

    active = sum([has_affirmative, has_limit, has_negative])

    if active > 1:
        return "MIXED_OR_CONFLICTING", "high"
    if has_negative:
        return "NEGATIVE_TREATMENT", "high"
    if has_limit:
        return "DISTINGUISHES_OR_LIMITS", "high"
    if has_affirmative:
        return "AFFIRMATIVE_USE", "high"
    return "MENTION_ONLY", "medium"


def extract_structured_relation(
    context: str,
    *,
    target_citation: str,
    target_term: str | None = None,
) -> dict[str, Any]:
    text = normalize_source_text(context)
    if not text:
        return RelationFrame(
            target_present=False,
            attribution_owner="UNKNOWN",
            attributed_proposition="",
            current_court_actions=[],
            current_court_cues=[],
            relation="UNKNOWN",
            confidence="low",
            abstention_reason="empty_context",
        ).to_dict()

    target_pattern = re.compile(
        _target_source(target_citation, target_term),
        re.IGNORECASE,
    )

    if not _target_present(
        text,
        target_citation=target_citation,
        target_term=target_term,
    ):
        return RelationFrame(
            target_present=False,
            attribution_owner="UNKNOWN",
            attributed_proposition="",
            current_court_actions=[],
            current_court_cues=[],
            relation="UNKNOWN",
            confidence="low",
            abstention_reason="target_absent",
        ).to_dict()

    chunks = _target_chunks(
        text,
        target_citation=target_citation,
        target_term=target_term,
        neighbor_count=1,
    )
    if not chunks:
        chunks = [text]

    all_actions: list[str] = []
    all_cues: list[str] = []
    attributed_props: list[str] = []
    owner = "CURRENT_COURT"

    for chunk in chunks:
        treatment_text, proposition = _strip_attributed_holding_content(
            chunk,
            target_pattern=target_pattern,
        )
        if proposition:
            owner = "TARGET_AUTHORITY"
            if proposition not in attributed_props:
                attributed_props.append(proposition)

        actions, cues = _collect_actions(
            treatment_text,
            target_pattern=target_pattern,
        )
        for action in actions:
            if action not in all_actions:
                all_actions.append(action)
        for cue in cues:
            if cue not in all_cues:
                all_cues.append(cue)

    relation, confidence = _relation_from_actions(all_actions)

    if relation == "MENTION_ONLY" and owner == "TARGET_AUTHORITY":
        abstention = "attributed_target_holding_not_current_treatment"
    elif relation == "MENTION_ONLY":
        abstention = "no_current_court_treatment_cue"
    else:
        abstention = None

    return RelationFrame(
        target_present=True,
        attribution_owner=owner,
        attributed_proposition=" ".join(attributed_props)[:1600],
        current_court_actions=all_actions,
        current_court_cues=all_cues,
        relation=relation,
        confidence=confidence,
        abstention_reason=abstention,
    ).to_dict()
