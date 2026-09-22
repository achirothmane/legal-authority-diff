"""CourtListener citation-existence adapter.

This module intentionally verifies only what CourtListener's citation-lookup
endpoint can establish deterministically: whether a U.S. case-law citation
can be resolved in CourtListener, plus normalization/ambiguity metadata.

It does not infer proposition support, treatment, binding force, or legal advice.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINT = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
DEFAULT_TOKEN_ENV = "COURTLISTENER_TOKEN"


class CourtListenerError(RuntimeError):
    """Raised when the CourtListener adapter cannot complete a lookup."""


def lookup_citation(
    citation: str,
    *,
    token: str | None = None,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Look up one case-law citation using CourtListener's v4 API."""
    if not citation or not str(citation).strip():
        raise ValueError("citation must be non-empty")

    body = urlencode({"text": str(citation).strip()}).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "legal-authority-diff/0.2",
    }
    if token:
        headers["Authorization"] = f"Token {token}"

    request = Request(ENDPOINT, data=body, headers=headers, method="POST")

    try:
        with opener(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CourtListenerError(
            f"CourtListener HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except URLError as exc:
        raise CourtListenerError(f"CourtListener request failed: {exc.reason}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CourtListenerError("CourtListener returned invalid JSON") from exc

    if not isinstance(data, list):
        raise CourtListenerError("CourtListener returned an unexpected response shape")

    if not data:
        return {
            "citation": str(citation).strip(),
            "status": None,
            "normalized_citations": [],
            "clusters": [],
            "error_message": "",
            "adapter_state": "UNPARSED",
        }

    item = data[0]
    if not isinstance(item, dict):
        raise CourtListenerError("CourtListener citation result was not an object")

    status = item.get("status")
    state = {
        200: "FOUND",
        404: "NOT_FOUND",
        300: "AMBIGUOUS",
        400: "INVALID_OR_UNSUPPORTED",
        429: "THROTTLED",
    }.get(status, "UNKNOWN")

    return {
        "citation": item.get("citation", str(citation).strip()),
        "status": status,
        "normalized_citations": item.get("normalized_citations") or [],
        "clusters": item.get("clusters") or [],
        "error_message": item.get("error_message") or "",
        "adapter_state": state,
    }


def apply_lookup(
    record: dict[str, Any],
    lookup: dict[str, Any],
) -> dict[str, Any]:
    """Attach CourtListener evidence to a Legal Authority Diff record."""
    enriched = copy.deepcopy(record)
    authority = enriched.get("authority")
    if not isinstance(authority, dict):
        authority = {}
        enriched["authority"] = authority

    status = lookup.get("status")
    if status == 200:
        authority["exists"] = True
    elif status == 404:
        authority["exists"] = False
    # 300/400/429/unparsed stay unresolved. Do not convert uncertainty to False.

    clusters = lookup.get("clusters") or []
    cluster_summaries = []
    for cluster in clusters[:5]:
        if not isinstance(cluster, dict):
            continue
        cluster_summaries.append(
            {
                "id": cluster.get("id"),
                "case_name": cluster.get("case_name"),
                "date_filed": cluster.get("date_filed"),
                "precedential_status": cluster.get("precedential_status"),
                "absolute_url": cluster.get("absolute_url"),
            }
        )

    authority["verification"] = {
        "provider": "courtlistener",
        "endpoint": "citation-lookup-v4",
        "lookup_status": lookup.get("adapter_state"),
        "http_semantic_status": status,
        "normalized_citations": lookup.get("normalized_citations") or [],
        "matches": cluster_summaries,
        "error_message": lookup.get("error_message") or "",
    }

    return enriched


def enrich_records(
    records: list[dict[str, Any]],
    *,
    token: str | None = None,
    opener: Callable[..., Any] = urlopen,
    delay_seconds: float = 1.05,
) -> list[dict[str, Any]]:
    """Enrich records sequentially to stay conservative with API throttles."""
    enriched: list[dict[str, Any]] = []

    for index, record in enumerate(records):
        authority = record.get("authority")
        citation = authority.get("citation") if isinstance(authority, dict) else None

        if not citation:
            copy_record = copy.deepcopy(record)
            copy_record.setdefault("authority", {})["verification"] = {
                "provider": "courtlistener",
                "endpoint": "citation-lookup-v4",
                "lookup_status": "NO_CITATION",
                "http_semantic_status": None,
                "normalized_citations": [],
                "matches": [],
                "error_message": "Record has no authority.citation value.",
            }
            enriched.append(copy_record)
            continue

        lookup = lookup_citation(str(citation), token=token, opener=opener)
        enriched.append(apply_lookup(record, lookup))

        if delay_seconds > 0 and index < len(records) - 1:
            time.sleep(delay_seconds)

    return enriched


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
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            rows.append(value)
    return rows


def _write_jsonl(path: str, records: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legal-enrich-citations",
        description="Enrich Legal Authority Diff JSONL with CourtListener citation lookup evidence.",
    )
    parser.add_argument("input", help="Input JSONL path")
    parser.add_argument("output", help="Output JSONL path")
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Environment variable containing the CourtListener API token (default: {DEFAULT_TOKEN_ENV}).",
    )
    parser.add_argument(
        "--allow-unauthenticated",
        action="store_true",
        help="Allow a request without an API token. Intended only for experimentation.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.05,
        help="Delay in seconds between citation requests (default: 1.05).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.token_env)

    if not token and not args.allow_unauthenticated:
        print(
            f"error: set {args.token_env} or pass --allow-unauthenticated for experimentation",
            file=sys.stderr,
        )
        return 2

    try:
        records = _read_jsonl(args.input)
        enriched = enrich_records(
            records,
            token=token,
            delay_seconds=max(0.0, args.delay),
        )
        _write_jsonl(args.output, enriched)
    except (OSError, ValueError, CourtListenerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    states: dict[str, int] = {}
    for record in enriched:
        authority = record.get("authority") or {}
        verification = authority.get("verification") or {}
        state = str(verification.get("lookup_status", "UNKNOWN"))
        states[state] = states.get(state, 0) + 1

    print(f"Enriched {len(enriched)} records with CourtListener evidence.")
    for state in sorted(states):
        print(f"{state}: {states[state]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
