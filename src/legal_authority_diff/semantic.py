"""Semantic proposition-support verifier for V0.6.

The verifier separates two jobs:

1. lexical retrieval finds a small set of candidate source windows;
2. a local Natural Language Inference (NLI) model estimates whether each
   candidate window entails the tested proposition.

This is still an experimental signal, not a legal conclusion.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Iterable


TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","by","can","could",
    "did","do","does","for","from","had","has","have","if","in","into","is",
    "it","its","may","must","no","not","of","on","or","shall","should","that",
    "the","their","them","there","these","they","this","those","to","under",
    "was","were","when","where","which","who","will","with","would",
}


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_RE.findall(text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def source_windows(source_text: str, *, max_sentences: int = 2) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_RE.split(source_text)
        if sentence.strip()
    ]
    if not sentences:
        return [source_text.strip()] if source_text.strip() else []

    windows: list[str] = []
    for index in range(len(sentences)):
        for width in range(1, max_sentences + 1):
            stop = index + width
            if stop <= len(sentences):
                windows.append(" ".join(sentences[index:stop]))
    return windows


def lexical_retrieval_score(claim: str, window: str) -> float:
    claim_tokens = set(_tokens(claim))
    window_tokens = set(_tokens(window))
    if not claim_tokens or not window_tokens:
        return 0.0

    overlap = len(claim_tokens & window_tokens)
    recall = overlap / len(claim_tokens)
    precision = overlap / len(window_tokens)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return 0.65 * recall + 0.35 * f1


def rank_candidate_windows(
    claim: str,
    source_text: str,
    *,
    top_k: int = 8,
    max_sentences: int = 2,
) -> list[dict[str, Any]]:
    ranked = [
        {
            "window": window,
            "retrieval_score": round(
                lexical_retrieval_score(claim, window),
                6,
            ),
        }
        for window in source_windows(source_text, max_sentences=max_sentences)
    ]
    ranked.sort(key=lambda item: item["retrieval_score"], reverse=True)
    return ranked[: max(1, top_k)]


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps)
    return [value / total for value in exps]


def normalize_nli_output(
    logits: Iterable[float],
    id2label: dict[int | str, str],
) -> dict[str, float]:
    values = [float(value) for value in logits]
    probabilities = _softmax(values)

    result = {
        "contradiction": 0.0,
        "entailment": 0.0,
        "neutral": 0.0,
    }
    for index, probability in enumerate(probabilities):
        label = id2label.get(index, id2label.get(str(index), str(index)))
        normalized = str(label).strip().lower()
        if normalized in result:
            result[normalized] = probability

    return {key: round(value, 6) for key, value in result.items()}


@dataclass
class SemanticDecision:
    support_score: float
    predicted_support: str
    best_window: str
    retrieval_score: float
    entailment: float
    neutral: float
    contradiction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.support_score, 6),
            "predicted_support": self.predicted_support,
            "best_window": self.best_window,
            "retrieval_score": round(self.retrieval_score, 6),
            "nli": {
                "entailment": round(self.entailment, 6),
                "neutral": round(self.neutral, 6),
                "contradiction": round(self.contradiction, 6),
            },
        }


class NliVerifier:
    """Local NLI verifier loaded lazily from Hugging Face."""

    def __init__(
        self,
        *,
        model_name: str = "cross-encoder/nli-MiniLM2-L6-H768",
        threshold: float = 0.50,
        top_k: int = 8,
        max_sentences: int = 2,
    ) -> None:
        self.model_name = model_name
        self.threshold = float(threshold)
        self.top_k = int(top_k)
        self.max_sentences = int(max_sentences)
        self._model = None
        self._tokenizer = None
        self._torch = None

    def _load(self) -> None:
        if self._model is not None:
            return

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                'semantic verification requires: pip install -e ".[semantic]"'
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name
        )
        self._model.eval()

    def _score_pairs(
        self,
        premises: list[str],
        hypotheses: list[str],
    ) -> list[dict[str, float]]:
        self._load()
        assert self._torch is not None
        assert self._tokenizer is not None
        assert self._model is not None

        encoded = self._tokenizer(
            premises,
            hypotheses,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        with self._torch.no_grad():
            logits = self._model(**encoded).logits.cpu().tolist()

        id2label = dict(self._model.config.id2label)
        return [
            normalize_nli_output(row, id2label)
            for row in logits
        ]

    def verify(self, claim: str, source_text: str) -> dict[str, Any]:
        candidates = rank_candidate_windows(
            claim,
            source_text,
            top_k=self.top_k,
            max_sentences=self.max_sentences,
        )
        if not candidates:
            return SemanticDecision(
                support_score=0.0,
                predicted_support="unsupported",
                best_window="",
                retrieval_score=0.0,
                entailment=0.0,
                neutral=1.0,
                contradiction=0.0,
            ).to_dict()

        premises = [item["window"] for item in candidates]
        hypotheses = [claim] * len(candidates)
        scores = self._score_pairs(premises, hypotheses)

        best_index = max(
            range(len(scores)),
            key=lambda index: scores[index]["entailment"],
        )
        best_score = scores[best_index]
        best_candidate = candidates[best_index]

        entailment = best_score["entailment"]
        is_entailment_label = (
            entailment >= best_score["neutral"]
            and entailment >= best_score["contradiction"]
        )
        supported = (
            entailment >= self.threshold
            and is_entailment_label
        )

        return SemanticDecision(
            support_score=entailment,
            predicted_support="supported" if supported else "unsupported",
            best_window=best_candidate["window"][:1000],
            retrieval_score=best_candidate["retrieval_score"],
            entailment=entailment,
            neutral=best_score["neutral"],
            contradiction=best_score["contradiction"],
        ).to_dict()
