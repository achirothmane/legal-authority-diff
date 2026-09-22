"""OpenAI Structured Outputs adapter for the V0.11 relation experiment.

This is intentionally optional and manual. Ordinary CI never requires an API
key or a live model call.

The model extracts a bounded evidence object. Deterministic code validates the
schema, target identity, stance/treatment consistency, and evidence grounding.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .schema_relation_v011 import (
    RELATION_EXTRACTION_JSON_SCHEMA,
    safe_treatment,
    validate_relation_extraction,
)


DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_REASONING_EFFORT = "medium"


SYSTEM_PROMPT = """You extract precedent relationships from U.S. judicial text.

Return only the schema-constrained object requested by the API.

Your task is narrow: determine how the CURRENT COURT treats the TARGET AUTHORITY
inside the supplied passage.

Rules:
- Separate the target authority's historical proposition from what the current
  court is doing with that proposition.
- A sentence saying "X held that ..." describes X's proposition. It does not by
  itself mean the current court applies, limits, or rejects X.
- A question or argument about whether X applies is not itself APPLIES.
- If the current court refuses to extend X, choose DECLINES_TO_EXTEND.
- If it distinguishes materially different facts or legal settings, choose
  DISTINGUISHES or LIMITS.
- If it keeps the precedent after being asked to overrule it, choose
  DECLINES_TO_OVERRULE or REAFFIRMS.
- If it expressly overrules, weakens, or disapproves the target, choose the
  corresponding negative stance.
- DESCRIBES/CITES/QUOTES are mention-only stances.
- If the target or stance cannot be resolved from this passage, abstain.
- Do not infer current validity from outside knowledge.
- Evidence spans must be short verbatim substrings copied from the supplied
  passage. Do not fabricate or normalize evidence text.
- Do not output chain-of-thought or free-form reasoning.
"""


class RelationExtractionError(RuntimeError):
    pass


def _user_payload(
    *,
    context: str,
    target_name: str,
    target_citation: str,
    claim: str | None,
) -> str:
    payload = {
        "target_authority": {
            "name": target_name,
            "citation": target_citation,
        },
        "tested_claim": claim or "",
        "passage": context,
    }
    return json.dumps(payload, ensure_ascii=False)


def _extract_refusal(response: Any) -> str | None:
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            refusal = getattr(content, "refusal", None)
            if isinstance(refusal, str) and refusal.strip():
                return refusal.strip()
    return None


def extract_relation_openai(
    *,
    context: str,
    target_name: str,
    target_citation: str,
    claim: str | None = None,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    client: Any | None = None,
) -> dict[str, Any]:
    """Call a structured-output model and validate its evidence envelope."""
    if client is None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RelationExtractionError(
                'OpenAI SDK missing; install with: pip install -e ".[llm]"'
            ) from exc
        client = OpenAI()

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": _user_payload(
                    context=context,
                    target_name=target_name,
                    target_citation=target_citation,
                    claim=claim,
                ),
            },
        ],
        reasoning={"effort": reasoning_effort},
        text={
            "format": {
                "type": "json_schema",
                "name": "legal_relation_extraction_v011",
                "strict": True,
                "schema": RELATION_EXTRACTION_JSON_SCHEMA,
            }
        },
        max_output_tokens=2200,
        store=False,
    )

    refusal = _extract_refusal(response)
    if refusal:
        raise RelationExtractionError(f"model_refusal:{refusal}")

    status = getattr(response, "status", None)
    if status not in {None, "completed"}:
        raise RelationExtractionError(f"incomplete_response:{status}")

    output_text = getattr(response, "output_text", "")
    if not isinstance(output_text, str) or not output_text.strip():
        raise RelationExtractionError("empty_structured_output")

    try:
        extraction = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise RelationExtractionError("structured_output_not_json") from exc

    validation = validate_relation_extraction(
        extraction,
        context=context,
        expected_target_name=target_name,
        expected_target_citation=target_citation,
    )
    envelope = safe_treatment(
        extraction,
        context=context,
        expected_target_name=target_name,
        expected_target_citation=target_citation,
    )

    return {
        "model": model,
        "reasoning_effort": reasoning_effort,
        "extraction": extraction,
        "validation": validation,
        "policy_input": envelope,
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RelationExtractionError(
                f"{path}:{line_number}: invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise RelationExtractionError(
                f"{path}:{line_number}: row must be an object"
            )
        rows.append(value)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run V0.11 schema-constrained legal relation extraction."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--model",
        default=os.getenv("LEGAL_RELATION_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=["low", "medium", "high", "xhigh", "max"],
        default=DEFAULT_REASONING_EFFORT,
    )
    args = parser.parse_args(argv)

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is required for the live V0.11 extractor.")
        return 2

    rows = _load_jsonl(args.input)
    output_rows: list[dict[str, Any]] = []

    for row in rows:
        case_id = row.get("case_id") or row.get("challenge_id")
        context = row.get("context")
        target_name = row.get("target_case") or row.get("target_name")
        target_citation = row.get("target_citation")
        claim = row.get("claim")

        if not all(
            isinstance(value, str) and value.strip()
            for value in [str(case_id or ""), context, target_name, target_citation]
        ):
            raise RelationExtractionError(
                f"row {case_id!r} is missing context/target identity"
            )

        result = extract_relation_openai(
            context=context,
            target_name=target_name,
            target_citation=target_citation,
            claim=claim if isinstance(claim, str) else None,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
        )
        output_rows.append(
            {
                "case_id": case_id,
                **result,
            }
        )

    args.output.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n"
            for row in output_rows
        ),
        encoding="utf-8",
    )

    usable = sum(1 for row in output_rows if row["policy_input"]["usable"])
    print(
        f"V0.11 extracted={len(output_rows)} "
        f"validated={usable} invalid_or_abstained={len(output_rows) - usable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
