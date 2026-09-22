"""Deterministic claim-support contracts over source text.

V0.4 deliberately does not pretend to solve general legal entailment. A support
contract is a benchmark/golden-set assertion that names textual anchors expected
to appear in source material supporting a tested proposition.
"""

from __future__ import annotations

import hashlib
import html
import re
from html.parser import HTMLParser
from typing import Any


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    return html.unescape(parser.text())


def normalize_text(value: str) -> str:
    text = html.unescape(str(value))
    text = (
        text.replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def evaluate_phrase_contract(
    source_text: str,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate required phrases against source text.

    All phrases matched -> supported.
    Some matched -> partial.
    None matched -> unsupported.
    No valid phrases -> unknown.
    """
    phrases = contract.get("required_phrases")
    if not isinstance(phrases, list):
        phrases = []

    required = [
        str(item).strip()
        for item in phrases
        if isinstance(item, str) and item.strip()
    ]

    normalized_source = normalize_text(source_text)
    matched: list[str] = []
    missing: list[str] = []

    for phrase in required:
        if normalize_text(phrase) in normalized_source:
            matched.append(phrase)
        else:
            missing.append(phrase)

    if not required:
        support = "unknown"
    elif not missing:
        support = "supported"
    elif matched:
        support = "partial"
    else:
        support = "unsupported"

    return {
        "contract_type": "required_phrases_v0.4",
        "support": support,
        "required_phrases": required,
        "matched_phrases": matched,
        "missing_phrases": missing,
        "source_sha256": hashlib.sha256(
            normalized_source.encode("utf-8")
        ).hexdigest(),
        "source_characters": len(normalized_source),
    }
