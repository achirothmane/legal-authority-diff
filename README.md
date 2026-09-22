# Legal Authority Diff

**Differential regression testing for legal AI authority, citations, and claim support.**

Legal Authority Diff is an experimental developer tool for one narrow question:

> Did a new version of a legal-AI system weaken the legal authority supporting the same tested claim?

It is not a legal chatbot, a legal research database, or a replacement for lawyer review.

## Why differential testing?

A model, prompt, retriever, agent, or source index can change without an obvious application failure. The answer may still look plausible while the legal support becomes weaker:

- a real citation becomes fabricated or unresolved;
- good law becomes negatively treated authority;
- controlling authority becomes merely persuasive;
- a supported proposition becomes only partially supported or unsupported;
- the law itself changes, which should not be blamed on the model.

V0.1 compares a **baseline** run with a **candidate** run and reports:

`REGRESSION | IMPROVEMENT | UNCHANGED | UNKNOWN | WORLD_CHANGE`

A deterministic regression makes the CLI exit with code `1`, so it can act as a CI gate.

## Quickstart

Requires Python 3.10+.

```bash
python -m pip install -e .
legal-diff examples/baseline.jsonl examples/candidate.jsonl
```

Expected summary:

```text
Legal Authority Diff

Cases evaluated: 3

REGRESSIONS      1
IMPROVEMENTS     0
UNCHANGED        1
UNKNOWN          0
WORLD_CHANGE     1

RESULT: BLOCK
```

For machine-readable output:

```bash
legal-diff examples/baseline.jsonl examples/candidate.jsonl --json
```

## Input

One JSON object per line. Baseline and candidate records are paired by `case_id`.

```json
{
  "case_id": "LAD-001",
  "claim": "California law requires ...",
  "authority": {
    "citation": "123 Cal. 4th 456",
    "jurisdiction": "CA",
    "court": "California Supreme Court",
    "status": "controlling",
    "treatment": "good_law",
    "exists": true
  },
  "support": "supported"
}
```

V0.1 deliberately trusts supplied metadata. It does **not** yet retrieve or independently verify legal sources. That boundary is intentional: the prototype is testing whether differential legal semantics are useful before we build or buy verification infrastructure.

## V0.1 blocking rules

The candidate is blocked when supplied evidence shows a deterministic downgrade such as:

1. existing citation → missing/fabricated citation;
2. non-negative treatment → overruled/superseded/reversed/vacated/invalid;
3. stronger authority class → weaker authority class;
4. proposition support → weaker proposition support.

A jurisdiction change that cannot be ranked safely is `UNKNOWN`, not a guessed failure. An explicitly marked change in the underlying law is `WORLD_CHANGE`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Status

Prototype / falsification stage. The next decision is not “add more features.” It is whether differential legal-authority output catches meaningful regressions that generic LLM evaluation does not.

## Disclaimer

This software is experimental and does not provide legal advice. Legal conclusions require qualified human review.
