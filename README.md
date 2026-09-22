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


## Source-text support regression (V0.4)

V0.4 adds a deliberately narrow support-evidence layer. A golden-set record can define a deterministic support contract:

```json
{
  "context": {
    "support_contract": {
      "required_phrases": ["same-sex couples", "marry"]
    }
  }
}
```

For a resolved CourtListener citation, the adapter retrieves the linked opinion text and prefers `html_with_citations` when available. It then evaluates whether the configured textual anchors are present. The raw opinion text is not persisted in the enriched record; the evidence bundle stores the match result, missing/matched anchors, source hash, and source metadata.

The support states are conservative:

- all required anchors present → `supported`
- some present → `partial`
- none present → `unsupported`
- source/contract cannot be resolved → `unknown`

This is **not** general legal entailment and must not be interpreted as proof that a case legally supports a proposition. It is a deterministic regression primitive for benchmark/golden-set assertions.

The live V0.4 check isolates support from citation existence and authority strength:

- baseline: `576 U.S. 644`
- candidate: `347 U.S. 483`
- target: `ca2`
- both citations resolve through CourtListener
- both source courts resolve to `scotus`
- both derive as `controlling`
- baseline source satisfies the support contract
- candidate source misses the support contract

The resulting differential is:

```text
proposition_support:
  supported -> unsupported

RESULT: BLOCK
```

The authenticated live run passed end-to-end:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35716809115

The manual GitHub Actions workflow is `live-proposition-support`.


## Real claim-citation benchmark (V0.5)

V0.5 adds a 20-pair benchmark designed to measure proposition-support errors before adding a semantic model.

The benchmark contains 10 supported pairs and 10 hard negatives built from the same claims and real Supreme Court citations. Several negatives deliberately share topic vocabulary with the positive source—for example Miranda/Gideon, Tinker/T.L.O., Brandenburg/Sullivan, and Obergefell/Loving.

The first baseline is intentionally simple: it retrieves the best one- or two-sentence window from the principal opinion text and scores token overlap, claim-token recall, and bigram overlap. It is called `lexical_retrieval_v0.5`.

The benchmark reports TP, TN, FP, FN, accuracy, precision, recall, false-positive rate, false-negative rate, and every misclassified pair. There is no quality gate yet: V0.5 is a measurement step used to decide what evidence layer is needed next.

The reproducible V0.5 run uses official GovInfo U.S. Reports PDFs. CourtListener
remains an optional source backend, but benchmark measurement is deliberately
decoupled from third-party API quotas.

Run:

```bash
python -m pip install -e ".[benchmark]"
legal-benchmark-support \
  benchmarks/real-claim-citation-v0.5/pairs.jsonl \
  --source govinfo \
  --output /tmp/v0.5-report.json
```

First measured result at threshold `0.34`:

```text
TP=10 TN=9 FP=1 FN=0
accuracy=0.950
precision=0.909
recall=1.000
false-positive-rate=0.100
false-negative-rate=0.000
```

The only error was the Gideon appointed-counsel claim paired with Miranda
(`384 U.S. 436`), a useful hard negative because related criminal-procedure
and counsel language fooled the lexical baseline. We do not tune the threshold
on this same 20-pair set.

Full result notes:
`benchmarks/real-claim-citation-v0.5/RESULTS.md`

The benchmark evaluates whether the **source text supports the test proposition**.
It does not decide whether the proposition remains current law today.


## Generic NLI falsification (V0.6)

V0.6 tested whether a local Natural Language Inference layer could solve the failure
exposed by V0.5: confusing related legal language with proposition support.

The experiment froze its configuration before evaluating a new 20-pair held-out set:

- local model: `cross-encoder/nli-MiniLM2-L6-H768`
- entailment threshold: `0.50`
- top 8 lexical candidate windows
- 10 new supported pairs and 10 new topic-overlapping negatives
- official GovInfo U.S. Reports PDFs

It failed the intended falsification test.

The known V0.5 false positive remained a false positive:

```text
Gideon appointed-counsel claim
vs. Miranda, 384 U.S. 436

expected: unsupported
semantic: supported
entailment: 0.865
```

On the untouched V0.6 held-out set:

```text
Frozen lexical V0.5: TP=10 TN=10 FP=0 FN=0  accuracy=1.000
Semantic V0.6:       TP=10 TN=9  FP=1 FN=0  accuracy=0.950
```

The semantic layer fixed no lexical mistakes and introduced one new false positive.
Accordingly, generic NLI is **not promoted into the core regression gate**.

The engineering lesson is more specific than “semantic models do not work”: proposition
support in legal sources needs evidence about the source's **authority role**—for example
whether the language is the holding/rule being established, merely quoted, discussed,
distinguished, or applied from another authority.

Full frozen result:
`benchmarks/semantic-v0.6/RESULTS.md`


## Authority-role provenance (V0.7)

V0.7 follows the V0.6 falsification result: generic semantic entailment could not
reliably distinguish topical legal language from proposition support.

Instead of asking only whether a passage is similar to or entails a claim, V0.7
adds a conservative provenance question:

> Is the retrieved support window the source case's own rule/holding language,
> an attributed prior authority, secondary material, or unresolved?

The current observable roles are:

- `COURT_SELF_HOLDING`
- `REPORTER_SYLLABUS_HOLDING`
- `ATTRIBUTED_PRIOR_AUTHORITY`
- `SECONDARY_SOURCE`
- `UNKNOWN`

The U.S. Reports syllabus is explicitly kept separate from a Court-authored
holding.

Authority role is additive. It can only create a regression when both baseline
and candidate already clear the frozen lexical threshold and a primary-like
baseline degrades to attributed/secondary evidence. Primary -> `UNKNOWN` is
not forced into a regression.

This recovers the one V0.5 lexical false positive:

```text
Gideon, 372 U.S. 335
score=0.478
REPORTER_SYLLABUS_HOLDING

        ->

Miranda, 384 U.S. 436
score=0.365
SECONDARY_SOURCE

authority_role -> REGRESSION
```

On the paired V0.5 development benchmark:

```text
lexical-only: 9/10 regressions detected
role-aware:  10/10 regressions detected
identity controls: 0 false regressions
```

On the V0.6 replay set, both methods detect 10/10 and the identity controls again
produce zero regressions. This replay is not a new untouched held-out result.

The heuristic is **not promoted into the mandatory core gate yet**. Mapp and
Tinker probes demonstrate that a single retrieved window cannot reliably recover
every holding's provenance, so uncertain cases remain `UNKNOWN` or unchanged.

Live V0.7 run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35721271909

Full result:
`benchmarks/authority-role-v0.7/RESULTS.md`


## Precedent relationship guardrail (V0.8)

V0.8 addresses a false-block risk introduced by V0.7.

A later case can legitimately apply or reaffirm an earlier precedent even when
its local evidence looks like attributed prior authority. Blocking every
`COURT_SELF_HOLDING -> ATTRIBUTED_PRIOR_AUTHORITY` transition would therefore
be too aggressive.

V0.8 adds a separate target-aware relationship axis:

```text
AFFIRMATIVE_USE
DISTINGUISHES_OR_LIMITS
NEGATIVE_TREATMENT
MENTION_ONLY
UNKNOWN
```

The frozen 12-challenge benchmark uses official GovInfo U.S. Reports PDFs.
Its first execution scored 11/12 because one fixed anchor failed to resolve an
OCR-split `Ba tson`. After adding a generic OCR-tolerant anchor resolver without
changing the labels or relation rules, the replay scored:

```text
12/12

AFFIRMATIVE_USE          5/5
DISTINGUISHES_OR_LIMITS  2/2
NEGATIVE_TREATMENT       1/1
MENTION_ONLY             3/3
UNKNOWN                  1/1
```

The corrected 12/12 is explicitly a replay, not an untouched held-out score.

The experimental relation-aware policy then produced:

```text
affirmative-use role-only false blocks prevented = 5/5
negative-treatment -> WORLD_CHANGE                = 1/1
distinguish/limit -> UNKNOWN                      = 2/2
```

An affirmative-use signal never overrides a failed lexical support check. It only
prevents the role layer from blocking a later case solely because that case cites
the originating precedent.

The policy remains experimental and is not yet part of the mandatory core gate.

Measured run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35722812150

Full result:
`benchmarks/authority-relation-v0.8/RESULTS.md`
