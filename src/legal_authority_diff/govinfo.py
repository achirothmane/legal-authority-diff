"""Official GovInfo U.S. Reports source backend for benchmarks.

This module is intentionally limited to canonical U.S. Reports citations such as
"347 U.S. 483". It downloads the corresponding official GovInfo PDF and extracts
its embedded text for benchmark use.
"""

from __future__ import annotations

import hashlib
import io
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


US_REPORTS_RE = re.compile(
    r"^\s*(?P<volume>\d+)\s+U\.?\s*S\.?\s+(?P<page>\d+)\s*$",
    re.IGNORECASE,
)


class GovInfoError(RuntimeError):
    """Raised when the GovInfo benchmark source cannot be resolved."""


def parse_us_reports_citation(citation: str) -> tuple[int, int]:
    match = US_REPORTS_RE.match(str(citation))
    if not match:
        raise ValueError(
            f"unsupported GovInfo citation {citation!r}; expected e.g. '347 U.S. 483'"
        )
    return int(match.group("volume")), int(match.group("page"))


def govinfo_pdf_url(citation: str) -> str:
    volume, page = parse_us_reports_citation(citation)
    return (
        f"https://www.govinfo.gov/content/pkg/USREPORTS-{volume}/pdf/"
        f"USREPORTS-{volume}-{page}.pdf"
    )


def download_pdf(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 30.0,
) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/pdf",
            "User-Agent": "legal-authority-diff/0.6",
        },
        method="GET",
    )
    try:
        with opener(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        raise GovInfoError(f"GovInfo HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise GovInfoError(f"GovInfo request failed for {url}: {exc.reason}") from exc

    if not payload.startswith(b"%PDF"):
        raise GovInfoError(f"GovInfo did not return a PDF for {url}")
    return payload


def extract_pdf_text(pdf_bytes: bytes) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise GovInfoError(
            'PDF extraction requires the benchmark extra: pip install -e ".[benchmark]"'
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise GovInfoError(f"could not parse GovInfo PDF: {exc}") from exc

    pages: list[str] = []
    for page in reader.pages:
        try:
            value = page.extract_text() or ""
        except Exception as exc:
            raise GovInfoError(f"could not extract GovInfo PDF text: {exc}") from exc
        if value.strip():
            pages.append(value)

    text = "\n".join(pages).strip()
    if not text:
        raise GovInfoError("GovInfo PDF contained no extractable text")

    return {
        "text": text,
        "pages": len(reader.pages),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "characters": len(text),
    }


def fetch_us_reports_text(
    citation: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 30.0,
) -> tuple[str, dict[str, Any]]:
    url = govinfo_pdf_url(citation)
    payload = download_pdf(url, opener=opener, timeout=timeout)
    extracted = extract_pdf_text(payload)

    return extracted["text"], {
        "provider": "govinfo",
        "citation": citation,
        "url": url,
        "pages": extracted["pages"],
        "characters": extracted["characters"],
        "text_sha256": extracted["text_sha256"],
    }
