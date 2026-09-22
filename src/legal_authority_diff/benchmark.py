"""V0.5 real claim-citation support benchmark.

This benchmark is intentionally source-support focused. It measures whether a
simple deterministic lexical retrieval baseline can distinguish a claim that is
supported by a cited opinion from hard negative citations on nearby legal topics.

It does not determine current-law validity and is not a legal advice system.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from .courtlistener import (
    CourtListenerError,
    fetch_opinion_document,
    lookup_citation,
    resolve_authority_metadata,
)


STOPWORDS = {
    "a","an","and","are","as","at","be","been","being","by","can","could",
    "did","do","does","for","from","had","has","have","if","in","into","is",
    "it","its","may","must","no","not","of","on","or","shall","should","that",
    "the","their","them","there","these","they","this","those","to","under",
    "was","were","when","where","which","who","will","with","would",
}

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in TOKEN_RE.findall(text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def _bigrams(tokens: list[str]) -> set[tuple[str, str]]:
    return set(zip(tokens, tokens[1:]))


def _f1_overlap(claim_tokens: set[str], text_tokens: set[str]) -> float:
    if not claim_tokens or not text_tokens:
        return 0.0
    overlap = len(claim_tokens & text_tokens)
    if overlap == 0:
        return 0.0
    precision = overlap / len(text_tokens)
    recall = overlap / len(claim_tokens)
    return 2 * precision * recall / (precision + recall)


def _claim_recall(claim_tokens: set[str], text_tokens: set[str]) -> float:
    if not claim_tokens:
        return 0.0
    return len(claim_tokens & text_tokens) / len(claim_tokens)


def score_claim_against_source(claim: str, source_text: str) -> dict[str, Any]:
    """Return the best lexical support score over short opinion-text windows."""
    claim_list = _tokens(claim)
    claim_tokens = set(claim_list)
    claim_bigrams = _bigrams(claim_list)

    raw_sentences = [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_RE.split(source_text)
        if sentence.strip()
    ]
    if not raw_sentences:
        raw_sentences = [source_text.strip()] if source_text.strip() else []

    windows: list[str] = []
    for index in range(len(raw_sentences)):
        windows.append(raw_sentences[index])
        if index + 1 < len(raw_sentences):
            windows.append(raw_sentences[index] + " " + raw_sentences[index + 1])

    best = {
        "score": 0.0,
        "token_f1": 0.0,
        "claim_recall": 0.0,
        "bigram_recall": 0.0,
        "window": "",
    }

    for window in windows:
        window_list = _tokens(window)
        window_tokens = set(window_list)
        token_f1 = _f1_overlap(claim_tokens, window_tokens)
        claim_recall = _claim_recall(claim_tokens, window_tokens)

        window_bigrams = _bigrams(window_list)
        if claim_bigrams:
            bigram_recall = len(claim_bigrams & window_bigrams) / len(claim_bigrams)
        else:
            bigram_recall = 0.0

        score = 0.55 * token_f1 + 0.35 * claim_recall + 0.10 * bigram_recall

        if score > best["score"]:
            best = {
                "score": round(score, 6),
                "token_f1": round(token_f1, 6),
                "claim_recall": round(claim_recall, 6),
                "bigram_recall": round(bigram_recall, 6),
                "window": window[:500],
            }

    return best


def evaluate_binary(
    rows: list[dict[str, Any]],
    *,
    threshold: float,
) -> dict[str, Any]:
    tp = tn = fp = fn = 0
    scored: list[dict[str, Any]] = []

    for row in rows:
        score = float(row["score"])
        expected = row["expected_support"]
        predicted = "supported" if score >= threshold else "unsupported"

        item = dict(row)
        item["predicted_support"] = predicted
        item["correct"] = predicted == expected
        scored.append(item)

        if expected == "supported" and predicted == "supported":
            tp += 1
        elif expected == "supported" and predicted == "unsupported":
            fn += 1
        elif expected == "unsupported" and predicted == "supported":
            fp += 1
        else:
            tn += 1

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    fnr = fn / (fn + tp) if fn + tp else 0.0

    positives = [float(x["score"]) for x in scored if x["expected_support"] == "supported"]
    negatives = [float(x["score"]) for x in scored if x["expected_support"] == "unsupported"]

    return {
        "model": "lexical_retrieval_v0.5",
        "threshold": threshold,
        "counts": {
            "tp": tp,
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "total": total,
        },
        "metrics": {
            "accuracy": round(accuracy, 6),
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "false_positive_rate": round(fpr, 6),
            "false_negative_rate": round(fnr, 6),
        },
        "score_distribution": {
            "supported_mean": round(statistics.mean(positives), 6) if positives else None,
            "supported_min": round(min(positives), 6) if positives else None,
            "supported_max": round(max(positives), 6) if positives else None,
            "unsupported_mean": round(statistics.mean(negatives), 6) if negatives else None,
            "unsupported_min": round(min(negatives), 6) if negatives else None,
            "unsupported_max": round(max(negatives), 6) if negatives else None,
        },
        "rows": scored,
    }


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            if value.get("expected_support") not in {"supported", "unsupported"}:
                raise ValueError(
                    f"{path}:{line_number}: expected_support must be supported or unsupported"
                )
            rows.append(value)
    return rows


PRIMARY_OPINION_TYPES = {
    "010combined",
    "015unamimous",
    "015unanimous",
    "020lead",
    "025plurality",
    "combined-opinion",
    "unanimous-opinion",
    "lead-opinion",
    "plurality-opinion",
    "080onthemerits",
    "on-the-merits",
}


def _case_name_tokens(value: str) -> set[str]:
    ignored = {"v", "vs", "versus", "co", "company", "inc", "corp", "corporation"}
    return {
        token
        for token in TOKEN_RE.findall(value.lower())
        if token not in ignored and len(token) > 1
    }


def _disambiguate_lookup(
    lookup: dict[str, Any],
    *,
    expected_case_name: str | None,
) -> dict[str, Any]:
    if lookup.get("status") != 300:
        return lookup

    clusters = [
        cluster
        for cluster in (lookup.get("clusters") or [])
        if isinstance(cluster, dict)
    ]
    if not expected_case_name or not clusters:
        return lookup

    expected_tokens = _case_name_tokens(expected_case_name)
    if not expected_tokens:
        return lookup

    scored: list[tuple[float, dict[str, Any]]] = []
    for cluster in clusters:
        actual = str(cluster.get("case_name") or "")
        actual_tokens = _case_name_tokens(actual)
        if not actual_tokens:
            score = 0.0
        else:
            overlap = len(expected_tokens & actual_tokens)
            score = overlap / len(expected_tokens | actual_tokens)
        scored.append((score, cluster))

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_cluster = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0

    if best_score < 0.5 or (best_score - runner_up) < 0.15:
        return lookup

    resolved = dict(lookup)
    resolved["status"] = 200
    resolved["adapter_state"] = "FOUND_DISAMBIGUATED"
    resolved["clusters"] = [best_cluster]
    resolved["disambiguation"] = {
        "expected_case_name": expected_case_name,
        "selected_case_name": best_cluster.get("case_name"),
        "score": round(best_score, 6),
    }
    return resolved


def _resolve_source_text(
    citation: str,
    *,
    token: str,
    expected_case_name: str | None = None,
) -> tuple[str, dict[str, Any]]:
    lookup = lookup_citation(citation, token=token)
    lookup = _disambiguate_lookup(
        lookup,
        expected_case_name=expected_case_name,
    )
    lookup = resolve_authority_metadata(lookup, token=token)

    if lookup.get("status") != 200:
        raise CourtListenerError(
            f"citation {citation!r} did not resolve: "
            f"status={lookup.get('status')} state={lookup.get('adapter_state')}"
        )

    opinion_refs = lookup.get("sub_opinions") or []
    fallback: dict[str, Any] | None = None
    selected: dict[str, Any] | None = None
    fetched_count = 0

    for item in opinion_refs:
        if isinstance(item, str):
            url = item
        elif isinstance(item, dict):
            url = item.get("resource_uri") or item.get("url")
        else:
            url = None

        if not isinstance(url, str) or not url.startswith("http"):
            continue

        doc = fetch_opinion_document(url, token=token)
        fetched_count += 1
        doc["requested_url"] = url

        if fallback is None:
            fallback = doc

        opinion_type = str(doc.get("type") or "").strip().lower()
        if opinion_type in PRIMARY_OPINION_TYPES:
            selected = doc
            break

    if selected is None:
        selected = fallback

    if selected is None:
        raise CourtListenerError(f"citation {citation!r} has no usable opinion text")

    metadata = {
        "citation": citation,
        "source_court_id": lookup.get("source_court_id"),
        "precedential_status": lookup.get("precedential_status"),
        "opinion_count_fetched": fetched_count,
        "selected_opinion_count": 1,
        "selected_opinion_types": [selected.get("type")],
        "selected_opinion_urls": [selected.get("requested_url")],
        "lookup_state": lookup.get("adapter_state"),
        "disambiguation": lookup.get("disambiguation"),
    }
    return str(selected["text"]), metadata


def _resolve_source_text_with_retry(
    citation: str,
    *,
    token: str,
    expected_case_name: str | None = None,
    max_attempts: int = 5,
    backoff_seconds: float = 20.0,
) -> tuple[str, dict[str, Any]]:
    last_error: CourtListenerError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return _resolve_source_text(
                citation,
                token=token,
                expected_case_name=expected_case_name,
            )
        except CourtListenerError as exc:
            last_error = exc
            message = str(exc)
            throttled = "429" in message or "throttl" in message.lower()
            if not throttled or attempt == max_attempts:
                raise
            time.sleep(backoff_seconds * attempt)

    assert last_error is not None
    raise last_error


def run_live_benchmark(
    rows: list[dict[str, Any]],
    *,
    token: str,
    threshold: float,
    delay_seconds: float,
) -> dict[str, Any]:
    cache: dict[str, tuple[str, dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []

    unique_citations: list[str] = []
    citation_case_names: dict[str, str | None] = {}
    for row in rows:
        citation = str(row["citation"]).strip()
        case_name = row.get("case_name")
        case_name = str(case_name).strip() if case_name else None

        if citation not in unique_citations:
            unique_citations.append(citation)
            citation_case_names[citation] = case_name
        elif citation_case_names[citation] != case_name:
            raise ValueError(
                f"citation {citation!r} maps to inconsistent case names in benchmark"
            )

    for index, citation in enumerate(unique_citations):
        cache[citation] = _resolve_source_text_with_retry(
            citation,
            token=token,
            expected_case_name=citation_case_names[citation],
        )
        if delay_seconds > 0 and index < len(unique_citations) - 1:
            time.sleep(delay_seconds)

    for row in rows:
        citation = str(row["citation"]).strip()
        source_text, metadata = cache[citation]
        score = score_claim_against_source(str(row["claim"]), source_text)

        results.append(
            {
                "pair_id": row["pair_id"],
                "claim_id": row["claim_id"],
                "claim": row["claim"],
                "citation": citation,
                "expected_support": row["expected_support"],
                "score": score["score"],
                "score_components": {
                    "token_f1": score["token_f1"],
                    "claim_recall": score["claim_recall"],
                    "bigram_recall": score["bigram_recall"],
                },
                "best_window": score["window"],
                "source": metadata,
            }
        )

    report = evaluate_binary(results, threshold=threshold)
    report["benchmark"] = {
        "name": "real-claim-citation-v0.5",
        "pairs": len(rows),
        "unique_citations": len(unique_citations),
        "labels": {
            "supported": sum(1 for x in rows if x["expected_support"] == "supported"),
            "unsupported": sum(1 for x in rows if x["expected_support"] == "unsupported"),
        },
        "scope": "source proposition support only; not current-law validity",
    }
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legal-benchmark-support",
        description="Run the V0.5 real claim-citation support benchmark.",
    )
    parser.add_argument("dataset", help="Benchmark JSONL path")
    parser.add_argument("--threshold", type=float, default=0.34)
    parser.add_argument("--delay", type=float, default=7.0)
    parser.add_argument("--output", help="Optional JSON report path")
    parser.add_argument("--token-env", default="COURTLISTENER_TOKEN")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.token_env)
    if not token:
        print(f"error: set {args.token_env}", file=sys.stderr)
        return 2

    try:
        rows = _read_jsonl(args.dataset)
        report = run_live_benchmark(
            rows,
            token=token,
            threshold=args.threshold,
            delay_seconds=max(0.0, args.delay),
        )
    except (OSError, ValueError, CourtListenerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    metrics = report["metrics"]
    counts = report["counts"]
    print(
        (
            f"accuracy={metrics['accuracy']:.3f} "
            f"precision={metrics['precision']:.3f} "
            f"recall={metrics['recall']:.3f} "
            f"fp={counts['fp']} fn={counts['fn']}"
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
