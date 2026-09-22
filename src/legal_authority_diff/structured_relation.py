"""Structured precedent-relation extraction experiment for V0.10.

V0.9 failed because phrase-level patterns could not reliably answer a more basic
question: whose proposition is being stated?

V0.10 extracts an evidence frame before assigning a relation:

    target authority
        -> target resolution
        -> proposition owner / attribution
        -> current-court treatment actions
        -> relation

The extractor is conservative. It can abstain and it keeps attributed holding
content separate from treatment by the current court.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .authority_relation_v09 import (
    _approximate_anchor_span,
    _citation_pattern,
    _ocr_tolerant_anchor_pattern,
    normalize_source_text,
)


@dataclass
class RelationContext:
    text: str
    anchor_found: bool
    target_found_near_anchor: bool
    target_distance_chars: int | None
    target_resolution: str
    gold_suspect_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelationFrame:
    target_present: bool
    target_resolution: str
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


def _target_pattern(
    target_citation: str,
    target_term: str | None,
) -> re.Pattern[str]:
    return re.compile(
        _target_source(target_citation, target_term),
        re.IGNORECASE,
    )


def _target_present(
    text: str,
    *,
    target_citation: str,
    target_term: str | None,
) -> bool:
    return _target_pattern(target_citation, target_term).search(text) is not None


def _anchor_span(
    source: str,
    anchor: str,
) -> tuple[int, int] | None:
    needle = normalize_source_text(anchor)
    if not source or not needle:
        return None

    index = source.lower().find(needle.lower())
    if index >= 0:
        return index, index + len(needle)

    fuzzy = _ocr_tolerant_anchor_pattern(needle).search(source)
    if fuzzy is not None:
        return fuzzy.start(), fuzzy.end()

    return _approximate_anchor_span(source, needle)


def build_relation_context(
    source_text: str,
    *,
    anchor: str,
    target_citation: str,
    target_term: str | None,
    radius: int = 320,
    max_target_gap: int = 2400,
) -> dict[str, Any]:
    """Build a context that contains both the benchmark anchor and target.

    V0.9 showed that an anchor can describe a precedent through short-form
    citations after the full target name/citation has fallen just outside the
    fixed radius. V0.10 expands only when the full target can be resolved near
    the anchor. If it cannot, the example is flagged as potentially suspect
    rather than silently forcing a relationship.
    """
    source = normalize_source_text(source_text)
    span = _anchor_span(source, anchor)
    if span is None:
        return RelationContext(
            text="",
            anchor_found=False,
            target_found_near_anchor=False,
            target_distance_chars=None,
            target_resolution="ANCHOR_NOT_FOUND",
            gold_suspect_reason="anchor_not_found",
        ).to_dict()

    anchor_start, anchor_end = span
    base_radius = max(0, int(radius))
    start = max(0, anchor_start - base_radius)
    end = min(len(source), anchor_end + base_radius)

    target = _target_pattern(target_citation, target_term)
    nearby_start = max(0, anchor_start - max_target_gap)
    nearby_end = min(len(source), anchor_end + max_target_gap)
    nearby = source[nearby_start:nearby_end]

    candidates = list(target.finditer(nearby))
    if not candidates:
        return RelationContext(
            text=source[start:end],
            anchor_found=True,
            target_found_near_anchor=False,
            target_distance_chars=None,
            target_resolution="TARGET_NOT_FOUND_NEAR_ANCHOR",
            gold_suspect_reason=(
                "expected relation requires target treatment but the full target "
                "name/citation is not resolved near the benchmark anchor"
            ),
        ).to_dict()

    absolute = [
        (
            nearby_start + match.start(),
            nearby_start + match.end(),
        )
        for match in candidates
    ]

    def distance(item: tuple[int, int]) -> int:
        target_start, target_end = item
        if target_end < anchor_start:
            return anchor_start - target_end
        if target_start > anchor_end:
            return target_start - anchor_end
        return 0

    target_start, target_end = min(absolute, key=distance)
    target_distance = distance((target_start, target_end))

    start = max(0, min(start, target_start - 220))
    end = min(len(source), max(end, target_end + 220))

    resolution = (
        "TARGET_OVERLAPS_ANCHOR"
        if target_distance == 0
        else "TARGET_EXPANDED_INTO_CONTEXT"
    )

    return RelationContext(
        text=source[start:end],
        anchor_found=True,
        target_found_near_anchor=True,
        target_distance_chars=target_distance,
        target_resolution=resolution,
        gold_suspect_reason=None,
    ).to_dict()


def _sentenceish_chunks(text: str) -> list[str]:
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
    target = _target_pattern(target_citation, target_term)

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


def _strip_attributed_holding_content(
    chunk: str,
    *,
    target_pattern: re.Pattern[str],
) -> tuple[str, str]:
    """Separate a target's historical holding from current-court treatment."""
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
    remaining = normalized[:absolute_start].strip()
    return remaining, proposition


def _action_patterns(
    target_source: str,
) -> list[tuple[str, re.Pattern[str]]]:
    target = target_source
    flags = re.IGNORECASE

    return [
        # Explicit negative treatment. Keep these target-linked.
        (
            "OVERRULE",
            re.compile(
                rf"{target}.{{0,180}}\bshould\s+be\s+and\s+now\s+is\s+overruled\b",
                flags,
            ),
        ),
        (
            "OVERRULE",
            re.compile(
                rf"\bwe\s+(?:therefore\s+)?overrule\b.{{0,90}}{target}",
                flags,
            ),
        ),
        (
            "OVERRULE",
            re.compile(
                rf"{target}.{{0,180}}\b(?:is|are|was|were|has\s+been)\s+"
                rf"(?:expressly\s+)?overruled\b",
                flags,
            ),
        ),
        (
            "WEAKEN",
            re.compile(
                rf"{target}.{{0,260}}\b(?:is|are|was|were)\s+no\s+longer\s+"
                rf"(?:controlling|binding|good\s+law)\b",
                flags,
            ),
        ),
        (
            "WEAKEN",
            re.compile(
                rf"{target}.{{0,320}}\bshould\s+no\s+longer\s+be\s+regarded\s+"
                rf"as\s+mandatory\b",
                flags,
            ),
        ),
        (
            "WEAKEN",
            re.compile(
                rf"{target}.{{0,360}}\b(?:was|were|is|are)\s+wrongly\s+decided\b",
                flags,
            ),
        ),
        # Limit/distinguish the target.
        (
            "LIMIT",
            re.compile(
                rf"\bdeclines?\s+to\s+extend\s+{target}",
                flags,
            ),
        ),
        (
            "LIMIT",
            re.compile(
                rf"\b(?:find|finds|found)\b.{{0,120}}\birrelevant\b.{{0,180}}{target}",
                flags,
            ),
        ),
        (
            "LIMIT",
            re.compile(
                rf"{target}.{{0,220}}\b(?:provides?|provided)\s+no\s+support\b",
                flags,
            ),
        ),
        (
            "LIMIT",
            re.compile(
                rf"{target}.{{0,220}}\b(?:departs?|departed)\s+from\b",
                flags,
            ),
        ),
        (
            "LIMIT",
            re.compile(
                rf"{target}.{{0,180}}\b(?:does|did)\s+not\s+"
                rf"(?:apply|mandate|control|govern|require)\b",
                flags,
            ),
        ),
        (
            "LIMIT",
            re.compile(rf"\bin\s+contrast\s+to\s+{target}", flags),
        ),
        (
            "LIMIT",
            re.compile(rf"\bunlike\s+(?:in\s+)?{target}", flags),
        ),
        # Affirmative use / preservation.
        (
            "KEEP",
            re.compile(
                rf"\bdeclines?\s+to\s+overrule\s+{target}",
                flags,
            ),
        ),
        (
            "KEEP",
            re.compile(
                rf"\breaffirm(?:s|ed|ing)?\b.{{0,90}}{target}",
                flags,
            ),
        ),
        (
            "APPLY",
            re.compile(rf"\bunder\s+{target}", flags),
        ),
        (
            "APPLY",
            re.compile(rf"\bin\s+light\s+of\s+{target}", flags),
        ),
        (
            "APPLY",
            re.compile(
                rf"\bas\s+we\s+(?:stated|explained|held)\s+in\s+{target}",
                flags,
            ),
        ),
        (
            "APPLY",
            re.compile(
                rf"{target}.{{0,180}}\b(?:guide|guides|guided)\s+our\s+analysis\b",
                flags,
            ),
        ),
        (
            "APPLY",
            re.compile(
                rf"{target}.{{0,180}}\bset\s+forth\s+(?:a|the)\s+framework\b",
                flags,
            ),
        ),
        (
            "APPLY",
            re.compile(
                rf"{target}.{{0,160}}\b(?:applies?|governs?|controls?)\b",
                flags,
            ),
        ),
        (
            "APPLY",
            re.compile(
                rf"\bwe\s+hold\b.{{0,180}}{target}",
                flags,
            ),
        ),
    ]


def _collect_actions(
    text: str,
    *,
    target_citation: str,
    target_term: str | None,
) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    cues: list[str] = []

    if not text:
        return actions, cues

    for action, pattern in _action_patterns(
        _target_source(target_citation, target_term)
    ):
        for match in pattern.finditer(text):
            value = match.group(0).strip()
            if action not in actions:
                actions.append(action)
            if value not in cues:
                cues.append(value)

    return actions, cues


def _relation_from_actions(actions: list[str]) -> tuple[str, str]:
    kinds = set(actions)
    has_negative = bool(kinds & {"OVERRULE", "WEAKEN"})
    has_affirmative = bool(kinds & {"APPLY", "KEEP"})
    has_limit = "LIMIT" in kinds

    # Explicit negative treatment is a legal-world change signal even if the
    # later opinion also describes parts of the old rule as useful.
    if has_negative:
        return "NEGATIVE_TREATMENT", "high"

    if has_affirmative and has_limit:
        return "MIXED_OR_CONFLICTING", "high"
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
    target_resolution: str = "DIRECT_CONTEXT",
) -> dict[str, Any]:
    text = normalize_source_text(context)
    if not text:
        return RelationFrame(
            target_present=False,
            target_resolution=target_resolution,
            attribution_owner="UNKNOWN",
            attributed_proposition="",
            current_court_actions=[],
            current_court_cues=[],
            relation="UNKNOWN",
            confidence="low",
            abstention_reason="empty_context",
        ).to_dict()

    target_pattern = _target_pattern(target_citation, target_term)

    if not _target_present(
        text,
        target_citation=target_citation,
        target_term=target_term,
    ):
        return RelationFrame(
            target_present=False,
            target_resolution=target_resolution,
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
            target_citation=target_citation,
            target_term=target_term,
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
        target_resolution=target_resolution,
        attribution_owner=owner,
        attributed_proposition=" ".join(attributed_props)[:1600],
        current_court_actions=all_actions,
        current_court_cues=all_cues,
        relation=relation,
        confidence=confidence,
        abstention_reason=abstention,
    ).to_dict()
