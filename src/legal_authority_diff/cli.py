"""Command-line interface for Legal Authority Diff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .engine import diff_runs


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


def _render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "Legal Authority Diff",
        "",
        f"Cases evaluated: {summary['cases_evaluated']}",
        "",
        f"REGRESSIONS      {summary['regressions']}",
        f"IMPROVEMENTS     {summary['improvements']}",
        f"UNCHANGED        {summary['unchanged']}",
        f"UNKNOWN          {summary['unknown']}",
        f"WORLD_CHANGE     {summary['world_change']}",
        "",
        f"RESULT: {summary['decision']}",
    ]

    for item in report["cases"]:
        if item["classification"] == "UNCHANGED":
            continue
        lines.extend(["", f"{item['classification']} {item['case_id']}"])
        for change in item["changes"]:
            lines.append(
                f"- {change['kind']}: {change['before']} -> {change['after']} | {change['reason']}"
            )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legal-diff",
        description="Compare legal-AI baseline and candidate runs for authority regressions.",
    )
    parser.add_argument("baseline", help="Path to baseline JSONL")
    parser.add_argument("candidate", help="Path to candidate JSONL")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the full machine-readable report as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = diff_runs(_read_jsonl(args.baseline), _read_jsonl(args.candidate))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_render_text(report))

    return 1 if report["summary"]["decision"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
