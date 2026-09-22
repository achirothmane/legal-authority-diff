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


## CourtListener citation adapter (V0.2)

V0.2 adds a first real legal-data adapter using CourtListener's citation lookup API.

The adapter is deliberately narrow: it verifies **U.S. case-law citation existence and normalization**. It does not claim to verify proposition support, treatment, binding force, statutes, law-journal citations, `id.`, or `supra`.

Set a CourtListener API token in the environment:

```bash
export COURTLISTENER_TOKEN="..."
legal-enrich-citations examples/courtlistener-input.jsonl /tmp/enriched.jsonl
```

CourtListener's citation-lookup endpoint requires authentication in the live smoke environment. The adapter therefore fails closed when `COURTLISTENER_TOKEN` is missing.

The adapter maps CourtListener results conservatively:

- `200` → `exists: true`
- `404` → `exists: false`
- `300` ambiguous → unresolved, not false
- `400` invalid/unsupported citation form → unresolved, not false
- `429` throttled → unresolved, not false
- no parsed citation → `UNPARSED`

CourtListener evidence is stored under `authority.verification` so the original record remains inspectable.

The point of this adapter is not to turn Legal Authority Diff into a legal database. It is to test whether real-source evidence makes differential regression output more useful than a generic LLM score.


### Live end-to-end smoke test

The repository includes a manual GitHub Actions workflow named `live-courtlistener-smoke`. It checks a real citation that CourtListener documents as found (`576 U.S. 644`) against its documented not-found example (`1 U.S. 200`), enriches both records from the live API, and requires Legal Authority Diff to return `BLOCK`.

Add a repository Actions secret named `COURTLISTENER_TOKEN`, then run **Actions → live-courtlistener-smoke → Run workflow**.

The live check is kept separate from ordinary CI because external API availability and credentials should not make deterministic unit tests flaky.


## Real authority regression (V0.3)

V0.3 moves beyond citation existence and resolves an unambiguous CourtListener case result through its linked docket to obtain the source court.

When a record supplies a narrow federal appellate target context:

```json
{
  "context": {
    "target_court_id": "ca2"
  }
}
```

the adapter can derive a conservative authority class using the `us-federal-appellate-v0.3` rule:

- SCOTUS → `controlling` for a federal circuit target;
- a published decision from the target circuit → `controlling`;
- a published decision from a different federal circuit → `persuasive`;
- anything outside that narrow scope → unresolved rather than guessed.

The live regression fixture uses two citations that CourtListener resolves successfully:

- baseline: `576 U.S. 644` → source court `scotus`;
- candidate: `771 F.3d 456` → source court `ca9`;
- target context: `ca2`.

The resulting differential is:

```text
controlling -> persuasive
RESULT: BLOCK
```

Both citations are real and found. The block is therefore caused by an authority-strength downgrade, not by a missing-citation check.

This V0.3 test still does **not** independently verify proposition support, treatment/current validity, or every U.S. hierarchy rule. Those remain separate evidence layers.

The authenticated end-to-end check is available as the manual GitHub Actions workflow `live-authority-regression`.
