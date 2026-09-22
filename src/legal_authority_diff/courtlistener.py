"""CourtListener adapter for citation existence and narrow court-authority metadata.

The adapter verifies U.S. case-law citations against CourtListener, can resolve
an unambiguous result to its source court through the linked docket, and can
derive a deliberately narrow federal authority class for a supplied target
federal appellate court.

It does not verify proposition support, treatment, current validity, or provide
legal advice.
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

from .support import evaluate_phrase_contract, html_to_text


ENDPOINT = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
DEFAULT_TOKEN_ENV = "COURTLISTENER_TOKEN"

FEDERAL_CIRCUIT_COURTS = {
    "ca1",
    "ca2",
    "ca3",
    "ca4",
    "ca5",
    "ca6",
    "ca7",
    "ca8",
    "ca9",
    "ca10",
    "ca11",
    "cadc",
    "cafc",
}


class CourtListenerError(RuntimeError):
    """Raised when the CourtListener adapter cannot complete a lookup."""


def _request_json(
    request: Request,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> Any:
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
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CourtListenerError("CourtListener returned invalid JSON") from exc


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
        "User-Agent": "legal-authority-diff/0.4",
    }
    if token:
        headers["Authorization"] = f"Token {token}"

    request = Request(ENDPOINT, data=body, headers=headers, method="POST")
    data = _request_json(request, opener=opener, timeout=timeout)

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


def fetch_docket_metadata(
    docket_url: str,
    *,
    token: str,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Fetch the minimal docket metadata needed to identify the source court."""
    request = Request(
        docket_url,
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": "legal-authority-diff/0.4",
        },
        method="GET",
    )
    data = _request_json(request, opener=opener, timeout=timeout)
    if not isinstance(data, dict):
        raise CourtListenerError("CourtListener docket response was not an object")
    return {
        "docket_id": data.get("id"),
        "docket_number": data.get("docket_number"),
        "court": data.get("court"),
        "court_id": data.get("court_id"),
    }


def resolve_authority_metadata(
    lookup: dict[str, Any],
    *,
    token: str | None,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Resolve an unambiguous found citation to a source court."""
    enriched = copy.deepcopy(lookup)
    clusters = enriched.get("clusters") or []

    if enriched.get("status") != 200 or len(clusters) != 1:
        enriched["authority_metadata_state"] = "UNRESOLVED"
        return enriched

    cluster = clusters[0]
    if not isinstance(cluster, dict):
        enriched["authority_metadata_state"] = "UNRESOLVED"
        return enriched

    docket_url = cluster.get("docket")
    if not token or not isinstance(docket_url, str) or not docket_url.startswith("http"):
        enriched["authority_metadata_state"] = "UNRESOLVED"
        return enriched

    docket = fetch_docket_metadata(
        docket_url,
        token=token,
        opener=opener,
        timeout=timeout,
    )

    enriched["authority_metadata_state"] = "RESOLVED"
    enriched["source_court_id"] = docket.get("court_id")
    enriched["source_court_url"] = docket.get("court")
    enriched["docket_id"] = docket.get("docket_id")
    enriched["docket_number"] = docket.get("docket_number")
    enriched["precedential_status"] = cluster.get("precedential_status")
    enriched["sub_opinions"] = cluster.get("sub_opinions") or []
    return enriched


def fetch_opinion_text(
    opinion_url: str,
    *,
    token: str,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> str:
    """Fetch CourtListener opinion text, preferring html_with_citations."""
    request = Request(
        opinion_url,
        headers={
            "Authorization": f"Token {token}",
            "Accept": "application/json",
            "User-Agent": "legal-authority-diff/0.4",
        },
        method="GET",
    )
    data = _request_json(request, opener=opener, timeout=timeout)
    if not isinstance(data, dict):
        raise CourtListenerError("CourtListener opinion response was not an object")

    html_value = data.get("html_with_citations")
    if isinstance(html_value, str) and html_value.strip():
        return html_to_text(html_value)

    for field in ("html", "html_lawbox", "html_columbia", "html_anon_2020"):
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            return html_to_text(value)

    plain = data.get("plain_text")
    if isinstance(plain, str) and plain.strip():
        return plain

    raise CourtListenerError("CourtListener opinion has no usable text field")


def resolve_support_evidence(
    lookup: dict[str, Any],
    *,
    contract: dict[str, Any] | None,
    token: str | None,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Evaluate an optional support contract against live opinion text."""
    enriched = copy.deepcopy(lookup)
    if not isinstance(contract, dict):
        return enriched

    opinion_refs = enriched.get("sub_opinions") or []
    if (
        enriched.get("status") != 200
        or enriched.get("authority_metadata_state") != "RESOLVED"
        or not token
        or not opinion_refs
    ):
        enriched["support_verification"] = {
            "state": "UNRESOLVED",
            "support": "unknown",
            "reason": "Opinion text could not be resolved for the support contract.",
        }
        return enriched

    texts: list[str] = []
    opinion_urls: list[str] = []
    for item in opinion_refs:
        if isinstance(item, str):
            url = item
        elif isinstance(item, dict):
            url = item.get("resource_uri") or item.get("url")
        else:
            url = None

        if not isinstance(url, str) or not url.startswith("http"):
            continue

        opinion_urls.append(url)
        texts.append(
            fetch_opinion_text(
                url,
                token=token,
                opener=opener,
                timeout=timeout,
            )
        )

    if not texts:
        enriched["support_verification"] = {
            "state": "UNRESOLVED",
            "support": "unknown",
            "reason": "No usable CourtListener opinion text URL was available.",
        }
        return enriched

    result = evaluate_phrase_contract("\n".join(texts), contract)
    result["state"] = "RESOLVED"
    result["provider"] = "courtlistener"
    result["opinion_count"] = len(texts)
    result["opinion_urls"] = opinion_urls
    enriched["support_verification"] = result
    return enriched


def infer_federal_authority_status(
    source_court_id: str | None,
    target_court_id: str | None,
    precedential_status: str | None,
) -> str | None:
    """Infer a narrow federal appellate authority class.

    Scope:
    - SCOTUS is controlling for federal circuit targets.
    - A published decision from the target circuit is controlling there.
    - A published decision from a different federal circuit is persuasive.
    - Everything else is unresolved rather than guessed.
    """
    source = (source_court_id or "").strip().lower()
    target = (target_court_id or "").strip().lower()
    precedent = (precedential_status or "").strip().lower()

    if target not in FEDERAL_CIRCUIT_COURTS:
        return None

    if source == "scotus":
        return "controlling"

    if source not in FEDERAL_CIRCUIT_COURTS:
        return None

    if precedent != "published":
        return None

    if source == target:
        return "controlling"

    return "persuasive"


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
                "docket_id": cluster.get("docket_id"),
            }
        )

    context = enriched.get("context")
    target_court_id = context.get("target_court_id") if isinstance(context, dict) else None
    derived_status = infer_federal_authority_status(
        lookup.get("source_court_id"),
        target_court_id,
        lookup.get("precedential_status"),
    )
    if derived_status is not None:
        authority["status"] = derived_status

    support_verification = lookup.get("support_verification")
    if isinstance(support_verification, dict):
        derived_support = support_verification.get("support")
        if derived_support in {"supported", "partial", "unsupported", "contradicted"}:
            enriched["support"] = derived_support

    authority["verification"] = {
        "provider": "courtlistener",
        "endpoint": "citation-lookup-v4",
        "lookup_status": lookup.get("adapter_state"),
        "http_semantic_status": status,
        "normalized_citations": lookup.get("normalized_citations") or [],
        "matches": cluster_summaries,
        "error_message": lookup.get("error_message") or "",
        "authority_metadata_state": lookup.get("authority_metadata_state", "UNRESOLVED"),
        "source_court_id": lookup.get("source_court_id"),
        "source_court_url": lookup.get("source_court_url"),
        "docket_id": lookup.get("docket_id"),
        "docket_number": lookup.get("docket_number"),
        "precedential_status": lookup.get("precedential_status"),
        "target_court_id": target_court_id,
        "derived_authority_status": derived_status,
        "authority_rule": (
            "us-federal-appellate-v0.3" if derived_status is not None else None
        ),
        "support_verification": support_verification,
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
                "authority_metadata_state": "UNRESOLVED",
            }
            enriched.append(copy_record)
            continue

        lookup = lookup_citation(str(citation), token=token, opener=opener)
        lookup = resolve_authority_metadata(
            lookup,
            token=token,
            opener=opener,
        )

        context = record.get("context")
        support_contract = (
            context.get("support_contract")
            if isinstance(context, dict)
            else None
        )
        lookup = resolve_support_evidence(
            lookup,
            contract=support_contract,
            token=token,
            opener=opener,
        )
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
        description="Enrich Legal Authority Diff JSONL with CourtListener evidence.",
    )
    parser.add_argument("input", help="Input JSONL path")
    parser.add_argument("output", help="Output JSONL path")
    parser.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Environment variable containing the CourtListener API token (default: {DEFAULT_TOKEN_ENV}).",
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

    if not token:
        print(
            f"error: set {args.token_env}; CourtListener citation lookup requires authentication",
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
