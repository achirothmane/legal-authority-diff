# V0.6 semantic support experiment — result

Run: https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35719654634

## Frozen configuration

- source: official GovInfo U.S. Reports PDFs
- semantic model: `cross-encoder/nli-MiniLM2-L6-H768`
- entailment threshold: `0.50`
- lexical retrieval: top 8 one/two-sentence windows
- frozen V0.5 lexical threshold: `0.34`
- held-out pairs: 20 (10 supported / 10 unsupported)
- no post-result parameter tuning

## Development failure probe

V0.5's only lexical false positive was tested before the held-out set:

```text
claim:
An indigent criminal defendant charged with a felony has a right
to appointed counsel in state court.

citation:
384 U.S. 436 — Miranda v. Arizona

expected: unsupported
semantic predicted: supported

entailment:    0.865
neutral:       0.133
contradiction: 0.001
```

So generic NLI did **not** fix the known topical-overlap failure.

## Held-out result

| Metric | Frozen lexical V0.5 | Semantic V0.6 |
|---|---:|---:|
| True positives | 10 | 10 |
| True negatives | 10 | 9 |
| False positives | 0 | 1 |
| False negatives | 0 | 0 |
| Accuracy | 1.000 | 0.950 |

Semantic V0.6 fixed no lexical errors and introduced one new false positive:

```text
H-NEG-010
expected: unsupported
citation: 573 U.S. 373 — Riley v. California
semantic predicted: supported
entailment score: 0.565
```

## Falsification result

The hypothesis

> adding a generic NLI entailment layer will reliably distinguish topical
> legal similarity from proposition support

is **not supported by this experiment**.

The semantic layer is therefore not promoted into the core `legal-diff` gate.

This result does not establish that all semantic models are unsuitable. It establishes
that this off-the-shelf generic NLI approach, under a frozen configuration and on this
small held-out set, failed to improve the existing lexical baseline and reproduced the
known V0.5 failure mode.

## What the failure teaches us

A sentence can linguistically entail a proposition while still being the wrong kind of
legal evidence for the proposition. A cited opinion may discuss, quote, distinguish, or
apply a related rule without itself being the authority that establishes the tested claim.

The next experiment should therefore target **authority-role / holding provenance**, not
merely stronger semantic similarity or a lower/higher entailment threshold.
