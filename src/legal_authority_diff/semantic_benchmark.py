"""V0.6 held-out semantic proposition-support benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .benchmark import _read_jsonl, evaluate_binary, score_claim_against_source
from .govinfo import GovInfoError, fetch_us_reports_text
from .semantic import NliVerifier


def _load_govinfo_cache(
    rows: list[dict[str, Any]],
) -> dict[str, tuple[str, dict[str, Any]]]:
    cache: dict[str, tuple[str, dict[str, Any]]] = {}
    for row in rows:
        citation = str(row["citation"]).strip()
        if citation not in cache:
            cache[citation] = fetch_us_reports_text(citation)
    return cache


def _lexical_report(
    rows: list[dict[str, Any]],
    cache: dict[str, tuple[str, dict[str, Any]]],
    *,
    threshold: float,
) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    for row in rows:
        citation = str(row["citation"]).strip()
        source_text, metadata = cache[citation]
        score = score_claim_against_source(str(row["claim"]), source_text)
        scored.append(
            {
                "pair_id": row["pair_id"],
                "claim_id": row["claim_id"],
                "claim": row["claim"],
                "citation": citation,
                "expected_support": row["expected_support"],
                "score": score["score"],
                "best_window": score["window"],
                "source": metadata,
            }
        )

    report = evaluate_binary(scored, threshold=threshold)
    report["model"] = "lexical_retrieval_v0.5"
    return report


def _semantic_report(
    rows: list[dict[str, Any]],
    cache: dict[str, tuple[str, dict[str, Any]]],
    *,
    verifier: NliVerifier,
) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []

    for row in rows:
        citation = str(row["citation"]).strip()
        source_text, metadata = cache[citation]
        decision = verifier.verify(str(row["claim"]), source_text)

        scored.append(
            {
                "pair_id": row["pair_id"],
                "claim_id": row["claim_id"],
                "claim": row["claim"],
                "citation": citation,
                "expected_support": row["expected_support"],
                "score": decision["score"],
                "predicted_support": decision["predicted_support"],
                "best_window": decision["best_window"],
                "retrieval_score": decision["retrieval_score"],
                "nli": decision["nli"],
                "source": metadata,
            }
        )

    report = evaluate_binary(scored, threshold=verifier.threshold)
    report["model"] = verifier.model_name
    report["retrieval"] = {
        "top_k": verifier.top_k,
        "max_sentences": verifier.max_sentences,
    }
    return report


def compare_reports(
    lexical: dict[str, Any],
    semantic: dict[str, Any],
) -> dict[str, Any]:
    lex_by_id = {row["pair_id"]: row for row in lexical["rows"]}
    sem_by_id = {row["pair_id"]: row for row in semantic["rows"]}

    fixed: list[str] = []
    broken: list[str] = []
    same_correct: list[str] = []
    same_wrong: list[str] = []

    for pair_id in sorted(lex_by_id):
        lex_ok = bool(lex_by_id[pair_id]["correct"])
        sem_ok = bool(sem_by_id[pair_id]["correct"])
        if not lex_ok and sem_ok:
            fixed.append(pair_id)
        elif lex_ok and not sem_ok:
            broken.append(pair_id)
        elif lex_ok and sem_ok:
            same_correct.append(pair_id)
        else:
            same_wrong.append(pair_id)

    return {
        "fixed_by_semantic": fixed,
        "broken_by_semantic": broken,
        "same_correct": same_correct,
        "same_wrong": same_wrong,
    }


def run_benchmark(
    rows: list[dict[str, Any]],
    *,
    model_name: str,
    semantic_threshold: float,
    lexical_threshold: float,
    top_k: int,
    max_sentences: int,
) -> dict[str, Any]:
    cache = _load_govinfo_cache(rows)

    lexical = _lexical_report(
        rows,
        cache,
        threshold=lexical_threshold,
    )
    verifier = NliVerifier(
        model_name=model_name,
        threshold=semantic_threshold,
        top_k=top_k,
        max_sentences=max_sentences,
    )
    semantic = _semantic_report(rows, cache, verifier=verifier)

    return {
        "benchmark": {
            "name": "semantic-v0.6-heldout",
            "pairs": len(rows),
            "unique_citations": len(cache),
            "split_values": sorted(
                {
                    str(row.get("split") or "")
                    for row in rows
                }
            ),
            "labels": {
                "supported": sum(
                    1 for row in rows
                    if row["expected_support"] == "supported"
                ),
                "unsupported": sum(
                    1 for row in rows
                    if row["expected_support"] == "unsupported"
                ),
            },
            "source": "govinfo",
            "scope": "source proposition support only; not current-law validity",
            "no_tuning_protocol": True,
        },
        "lexical": lexical,
        "semantic": semantic,
        "comparison": compare_reports(lexical, semantic),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legal-benchmark-semantic",
        description="Run the V0.6 held-out semantic support benchmark.",
    )
    parser.add_argument("dataset")
    parser.add_argument(
        "--model",
        default="cross-encoder/nli-MiniLM2-L6-H768",
    )
    parser.add_argument("--semantic-threshold", type=float, default=0.50)
    parser.add_argument("--lexical-threshold", type=float, default=0.34)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--max-sentences", type=int, default=2)
    parser.add_argument("--output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        rows = _read_jsonl(args.dataset)
        report = run_benchmark(
            rows,
            model_name=args.model,
            semantic_threshold=args.semantic_threshold,
            lexical_threshold=args.lexical_threshold,
            top_k=args.top_k,
            max_sentences=args.max_sentences,
        )
    except (OSError, ValueError, GovInfoError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    lex = report["lexical"]
    sem = report["semantic"]
    print(
        (
            "lexical "
            f"acc={lex['metrics']['accuracy']:.3f} "
            f"fp={lex['counts']['fp']} fn={lex['counts']['fn']} | "
            "semantic "
            f"acc={sem['metrics']['accuracy']:.3f} "
            f"fp={sem['counts']['fp']} fn={sem['counts']['fn']}"
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
