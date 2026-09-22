# V0.5 benchmark result

Run: https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35718677497

Source backend: official GovInfo U.S. Reports PDFs.

Model: `lexical_retrieval_v0.5`

Threshold: `0.34`

## Result

| Metric | Value |
|---|---:|
| Pairs | 20 |
| Supported labels | 10 |
| Unsupported labels | 10 |
| True positives | 10 |
| True negatives | 9 |
| False positives | 1 |
| False negatives | 0 |
| Accuracy | 0.950 |
| Precision | 0.909 |
| Recall | 1.000 |
| False-positive rate | 0.100 |
| False-negative rate | 0.000 |
| Mean supported score | 0.495607 |
| Mean unsupported score | 0.233510 |

The only misclassification was:

```text
NEG-003
claim: An indigent criminal defendant charged with a felony has a right to appointed counsel in state court.
expected: unsupported
citation: 384 U.S. 436 (Miranda v. Arizona)
predicted: supported
score: 0.365
```

This is a useful hard negative rather than a random failure: Miranda contains related
criminal-procedure and counsel language, so a lexical matcher can confuse topical overlap
with proposition support.

## Interpretation

V0.5 establishes that source retrieval and a simple lexical baseline can separate most
pairs in this tiny benchmark, but it also exposes the precise failure mode we need to test
next: **related legal language is not the same thing as authority supporting the claim**.

We do not tune the threshold against this same 20-pair set. The next verifier should be
evaluated on a held-out expansion so that improvements are not benchmark overfitting.

This benchmark measures source proposition support only. It does not determine current-law
validity and is not legal advice.
